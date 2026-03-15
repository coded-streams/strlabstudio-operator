"""
api/v1alpha1/types.py — StrlabStudio CRD schema definitions.

These Python dataclasses mirror the YAML spec and are used by the
controller for validation and default-filling.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GatewaySpec:
    host: str
    port: int = 8083


@dataclass
class JobManagerSpec:
    host: str = "localhost"
    port: int = 8081


@dataclass
class ServiceSpec:
    type: str = "ClusterIP"   # ClusterIP | NodePort | LoadBalancer
    port: int = 80
    nodePort: int | None = None


@dataclass
class ResourceSpec:
    requests: dict[str, str] = field(default_factory=lambda: {"cpu": "50m", "memory": "64Mi"})
    limits:   dict[str, str] = field(default_factory=lambda: {"cpu": "200m", "memory": "128Mi"})


@dataclass
class StrlabStudioSpec:
    gateway:    GatewaySpec
    image:      str         = "codedstreams/strlabstudio:latest"
    replicas:   int         = 1
    jobmanager: JobManagerSpec = field(default_factory=JobManagerSpec)
    service:    ServiceSpec    = field(default_factory=ServiceSpec)
    resources:  ResourceSpec   = field(default_factory=ResourceSpec)
    extraEnv:   list[dict[str, Any]] = field(default_factory=list)


def parse_spec(raw: dict) -> StrlabStudioSpec:
    """Parse the raw spec dict from a CR into a typed StrlabStudioSpec."""
    gw_raw  = raw.get("gateway", {})
    jm_raw  = raw.get("jobmanager", {})
    svc_raw = raw.get("service", {})
    res_raw = raw.get("resources", {})

    gateway = GatewaySpec(
        host=gw_raw["host"],
        port=int(gw_raw.get("port", 8083)),
    )
    jobmanager = JobManagerSpec(
        host=jm_raw.get("host", "localhost"),
        port=int(jm_raw.get("port", 8081)),
    )
    service = ServiceSpec(
        type=svc_raw.get("type", "ClusterIP"),
        port=int(svc_raw.get("port", 80)),
        nodePort=svc_raw.get("nodePort"),
    )
    resources = ResourceSpec(
        requests=res_raw.get("requests", {"cpu": "50m", "memory": "64Mi"}),
        limits=res_raw.get("limits",   {"cpu": "200m", "memory": "128Mi"}),
    )

    return StrlabStudioSpec(
        image=raw.get("image", "codedstreams/strlabstudio:latest"),
        replicas=int(raw.get("replicas", 1)),
        gateway=gateway,
        jobmanager=jobmanager,
        service=service,
        resources=resources,
        extraEnv=raw.get("extraEnv", []),
    )