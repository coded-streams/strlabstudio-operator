"""
controllers/flinksqlstudio_controller.py
========================================
Kopf-based reconciler for FlinkSQLStudio custom resources.

Run locally:
    kopf run controllers/flinksqlstudio_controller.py --verbose

Deploy to cluster:
    kubectl apply -f config/crd/flinksqlstudios.yaml
    kubectl apply -f config/rbac/rbac.yaml
    kubectl apply -f config/manager/manager.yaml
"""
from __future__ import annotations

import kopf
import kubernetes
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.v1alpha1.types import parse_spec, FlinkSQLStudioSpec

# ── Kubernetes API clients (initialized at startup) ──────────────────────────
apps_v1: kubernetes.client.AppsV1Api  | None = None
core_v1: kubernetes.client.CoreV1Api  | None = None
log = logging.getLogger(__name__)

MANAGED_BY_LABEL = "codedstreams.io/managed-by"
OPERATOR_NAME    = "flinksqlstudio-operator"
API_GROUP        = "codedstreams.io"
API_VERSION      = "v1alpha1"
KIND             = "FlinkSQLStudio"


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.persistence.finalizer = f"{API_GROUP}/finalizer"
    settings.posting.level = logging.WARNING
    try:
        kubernetes.config.load_incluster_config()
        log.info("Using in-cluster kubeconfig")
    except kubernetes.config.ConfigException:
        kubernetes.config.load_kube_config()
        log.info("Using local kubeconfig")

    global apps_v1, core_v1
    apps_v1 = kubernetes.client.AppsV1Api()
    core_v1 = kubernetes.client.CoreV1Api()
    log.info("FlinkSQL Studio Operator started")


# ── Create / Update handler ───────────────────────────────────────────────────
@kopf.on.create(API_GROUP, API_VERSION, "flinksqlstudios")
@kopf.on.update(API_GROUP, API_VERSION, "flinksqlstudios")
def reconcile(name: str, namespace: str, spec: dict, uid: str,
              logger: kopf.Logger, **kwargs):
    logger.info(f"Reconciling FlinkSQLStudio/{name} in {namespace}")
    parsed = parse_spec(spec)
    owner_ref = _owner_ref(name, namespace, uid)

    _reconcile_deployment(name, namespace, parsed, owner_ref, logger)
    _reconcile_service(name, namespace, parsed, owner_ref, logger)

    return {"message": "Reconciled successfully", "ready": True}


# ── Delete handler ────────────────────────────────────────────────────────────
@kopf.on.delete(API_GROUP, API_VERSION, "flinksqlstudios")
def on_delete(name: str, namespace: str, logger: kopf.Logger, **kwargs):
    """
    Kubernetes garbage-collects owned resources automatically when the CR is
    deleted (via ownerReferences).  This handler just logs the event.
    """
    logger.info(f"FlinkSQLStudio/{name} deleted — owned resources will be GC'd")


# ── Deployment reconciler ─────────────────────────────────────────────────────
def _reconcile_deployment(name: str, namespace: str, spec: FlinkSQLStudioSpec,
                          owner_ref: dict, logger: kopf.Logger):
    deploy_name = f"flinksql-studio-{name}"
    labels = _labels(name)

    env_vars = [
        {"name": "FLINK_GATEWAY_HOST", "value": spec.gateway.host},
        {"name": "FLINK_GATEWAY_PORT", "value": str(spec.gateway.port)},
        {"name": "JOBMANAGER_HOST",    "value": spec.jobmanager.host},
        {"name": "JOBMANAGER_PORT",    "value": str(spec.jobmanager.port)},
    ] + spec.extraEnv

    desired = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": deploy_name,
            "namespace": namespace,
            "labels": labels,
            "ownerReferences": [owner_ref],
        },
        "spec": {
            "replicas": spec.replicas,
            "selector": {"matchLabels": labels},
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "containers": [{
                        "name": "studio",
                        "image": spec.image,
                        "imagePullPolicy": "Always",
                        "ports": [{"containerPort": 80, "name": "http"}],
                        "env": env_vars,
                        "resources": {
                            "requests": spec.resources.requests,
                            "limits":   spec.resources.limits,
                        },
                        "readinessProbe": {
                            "httpGet": {"path": "/healthz", "port": 80},
                            "initialDelaySeconds": 5, "periodSeconds": 10,
                        },
                        "livenessProbe": {
                            "httpGet": {"path": "/healthz", "port": 80},
                            "initialDelaySeconds": 10, "periodSeconds": 30,
                        },
                    }]
                }
            }
        }
    }

    try:
        apps_v1.read_namespaced_deployment(deploy_name, namespace)
        # Update existing
        apps_v1.replace_namespaced_deployment(
            deploy_name, namespace,
            kubernetes.client.V1Deployment(**_flatten(desired))
        )
        logger.info(f"Updated Deployment/{deploy_name}")
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 404:
            apps_v1.create_namespaced_deployment(
                namespace,
                kubernetes.client.V1Deployment(**_flatten(desired))
            )
            logger.info(f"Created Deployment/{deploy_name}")
        else:
            raise kopf.PermanentError(f"Failed to reconcile Deployment: {e}")


# ── Service reconciler ────────────────────────────────────────────────────────
def _reconcile_service(name: str, namespace: str, spec: FlinkSQLStudioSpec,
                       owner_ref: dict, logger: kopf.Logger):
    svc_name = f"flinksql-studio-{name}"
    labels = _labels(name)

    ports = [{"port": spec.service.port, "targetPort": 80, "name": "http"}]
    if spec.service.type == "NodePort" and spec.service.nodePort:
        ports[0]["nodePort"] = spec.service.nodePort

    desired = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": svc_name,
            "namespace": namespace,
            "labels": labels,
            "ownerReferences": [owner_ref],
        },
        "spec": {
            "selector": labels,
            "type": spec.service.type,
            "ports": ports,
        }
    }

    try:
        core_v1.read_namespaced_service(svc_name, namespace)
        # patch is safer for Services (preserves clusterIP)
        core_v1.patch_namespaced_service(
            svc_name, namespace,
            kubernetes.client.V1Service(**_flatten(desired))
        )
        logger.info(f"Patched Service/{svc_name}")
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 404:
            core_v1.create_namespaced_service(
                namespace,
                kubernetes.client.V1Service(**_flatten(desired))
            )
            logger.info(f"Created Service/{svc_name}")
        else:
            raise kopf.PermanentError(f"Failed to reconcile Service: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────
def _labels(instance_name: str) -> dict:
    return {
        "app":                        f"flinksql-studio-{instance_name}",
        MANAGED_BY_LABEL:             OPERATOR_NAME,
        "codedstreams.io/instance":   instance_name,
    }


def _owner_ref(name: str, namespace: str, uid: str) -> dict:
    return {
        "apiVersion":         f"{API_GROUP}/{API_VERSION}",
        "kind":               KIND,
        "name":               name,
        "uid":                uid,
        "controller":         True,
        "blockOwnerDeletion": True,
    }


def _flatten(obj):
    """Pass dicts straight to kubernetes client (it accepts raw dicts via **kwargs)."""
    return obj
