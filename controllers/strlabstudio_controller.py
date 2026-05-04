"""
controllers/strlabstudio_controller.py
=======================================
Kopf-based reconciler for StrlabStudio custom resources.

Run locally:
    kopf run controllers/strlabstudio_controller.py --verbose

Deploy to cluster:
    kubectl apply -f config/crd/strlabstudios.yaml
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
from api.v1alpha1.types import parse_spec, StrlabStudioSpec

# ── Kubernetes API clients (initialized at startup) ───────────────────────────
apps_v1: kubernetes.client.AppsV1Api | None = None
core_v1: kubernetes.client.CoreV1Api | None = None
log = logging.getLogger(__name__)

MANAGED_BY_LABEL = "codedstreams.io/managed-by"
OPERATOR_NAME    = "strlabstudio-operator"
API_GROUP        = "codedstreams.io"
API_VERSION      = "v1alpha1"
KIND             = "StrlabStudio"


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
    log.info("Str:::lab Studio Operator started")


# ── Create / Update handler ───────────────────────────────────────────────────
@kopf.on.create(API_GROUP, API_VERSION, "strlabstudios")
@kopf.on.update(API_GROUP, API_VERSION, "strlabstudios")
def reconcile(name: str, namespace: str, spec: dict, uid: str,
              logger: kopf.Logger, **kwargs):
    logger.info(f"Reconciling StrlabStudio/{name} in {namespace}")
    parsed    = parse_spec(spec)
    owner_ref = _owner_ref(name, namespace, uid)

    _reconcile_deployment(name, namespace, parsed, owner_ref, logger)
    _reconcile_service(name, namespace, parsed, owner_ref, logger)

    return {"message": "Reconciled successfully", "ready": True}


# ── Delete handler ────────────────────────────────────────────────────────────
@kopf.on.delete(API_GROUP, API_VERSION, "strlabstudios")
def on_delete(name: str, namespace: str, logger: kopf.Logger, **kwargs):
    """
    Kubernetes garbage-collects owned resources automatically when the CR is
    deleted (via ownerReferences). This handler just logs the event.
    """
    logger.info(f"StrlabStudio/{name} deleted — owned resources will be GC'd")


# ── Deployment reconciler ─────────────────────────────────────────────────────
def _reconcile_deployment(name: str, namespace: str, spec: StrlabStudioSpec,
                          owner_ref: dict, logger: kopf.Logger):
    deploy_name = f"strlab-studio-{name}"
    labels = _labels(name)

    env_vars = [
        {"name": "FLINK_GATEWAY_HOST", "value": spec.gateway.host},
        {"name": "FLINK_GATEWAY_PORT", "value": str(spec.gateway.port)},
        {"name": "JOBMANAGER_HOST",    "value": spec.jobmanager.host},
        {"name": "JOBMANAGER_PORT",    "value": str(spec.jobmanager.port)},
    ] + spec.extraEnv

    desired = _build_deployment(deploy_name, namespace, labels, owner_ref, spec, env_vars)

    try:
        apps_v1.read_namespaced_deployment(deploy_name, namespace)
        apps_v1.replace_namespaced_deployment(
            deploy_name, namespace,
            _dict_to_deployment(desired)
        )
        logger.info(f"Updated Deployment/{deploy_name}")
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 404:
            apps_v1.create_namespaced_deployment(
                namespace,
                _dict_to_deployment(desired)
            )
            logger.info(f"Created Deployment/{deploy_name}")
        else:
            raise kopf.PermanentError(f"Failed to reconcile Deployment: {e}")


# ── Service reconciler ────────────────────────────────────────────────────────
def _reconcile_service(name: str, namespace: str, spec: StrlabStudioSpec,
                       owner_ref: dict, logger: kopf.Logger):
    svc_name = f"strlab-studio-{name}"
    labels   = _labels(name)

    ports = [{"port": spec.service.port, "targetPort": 80, "name": "http"}]
    if spec.service.type == "NodePort" and spec.service.nodePort:
        ports[0]["nodePort"] = spec.service.nodePort

    desired = _build_service(svc_name, namespace, labels, owner_ref, spec, ports)

    try:
        core_v1.read_namespaced_service(svc_name, namespace)
        core_v1.patch_namespaced_service(
            svc_name, namespace,
            _dict_to_service(desired)
        )
        logger.info(f"Patched Service/{svc_name}")
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 404:
            core_v1.create_namespaced_service(
                namespace,
                _dict_to_service(desired)
            )
            logger.info(f"Created Service/{svc_name}")
        else:
            raise kopf.PermanentError(f"Failed to reconcile Service: {e}")


# ── Object builders ───────────────────────────────────────────────────────────
def _build_deployment(deploy_name, namespace, labels, owner_ref, spec, env_vars):
    return {
        "metadata": {
            "name":            deploy_name,
            "namespace":       namespace,
            "labels":          labels,
            "ownerReferences": [owner_ref],
        },
        "spec": {
            "replicas": spec.replicas,
            "selector": {"matchLabels": labels},
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "containers": [{
                        "name":            "studio",
                        "image":           spec.image,
                        "imagePullPolicy": "Always",
                        "ports": [{"containerPort": 80, "name": "http"}],
                        "env":   env_vars,
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


def _build_service(svc_name, namespace, labels, owner_ref, spec, ports):
    return {
        "metadata": {
            "name":            svc_name,
            "namespace":       namespace,
            "labels":          labels,
            "ownerReferences": [owner_ref],
        },
        "spec": {
            "selector": labels,
            "type":     spec.service.type,
            "ports":    ports,
        }
    }


# ── Dict → kubernetes client object converters ────────────────────────────────
def _dict_to_deployment(d: dict) -> kubernetes.client.V1Deployment:
    """Convert a raw dict (without apiVersion/kind) to a V1Deployment object."""
    api_client = kubernetes.client.ApiClient()
    meta = d.get("metadata", {})
    spec = d.get("spec", {})
    return kubernetes.client.V1Deployment(
        metadata=api_client.deserialize(
            _MockResponse(meta), kubernetes.client.V1ObjectMeta
        ),
        spec=api_client.deserialize(
            _MockResponse(spec), kubernetes.client.V1DeploymentSpec
        ),
    )


def _dict_to_service(d: dict) -> kubernetes.client.V1Service:
    """Convert a raw dict (without apiVersion/kind) to a V1Service object."""
    api_client = kubernetes.client.ApiClient()
    meta = d.get("metadata", {})
    spec = d.get("spec", {})
    return kubernetes.client.V1Service(
        metadata=api_client.deserialize(
            _MockResponse(meta), kubernetes.client.V1ObjectMeta
        ),
        spec=api_client.deserialize(
            _MockResponse(spec), kubernetes.client.V1ServiceSpec
        ),
    )


class _MockResponse:
    """Wraps a dict so ApiClient.deserialize() can process it."""
    def __init__(self, data):
        import json
        self.data = json.dumps(data)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _labels(instance_name: str) -> dict:
    return {
        "app":                      f"strlab-studio-{instance_name}",
        MANAGED_BY_LABEL:           OPERATOR_NAME,
        "codedstreams.io/instance": instance_name,
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