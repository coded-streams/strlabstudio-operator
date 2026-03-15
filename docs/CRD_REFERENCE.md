# StrlabStudio CRD Reference

## Group / Version / Kind
`codedstreams.io/v1alpha1/StrlabStudio`

## Spec Fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `spec.image` | string | No | `codedstreams/strlabstudio:latest` | IDE Docker image |
| `spec.replicas` | integer | No | `1` | Number of pods (1–10) |
| `spec.gateway.host` | string | **Yes** | — | Flink SQL Gateway hostname |
| `spec.gateway.port` | integer | No | `8083` | Flink SQL Gateway port |
| `spec.jobmanager.host` | string | No | `localhost` | JobManager REST hostname |
| `spec.jobmanager.port` | integer | No | `8081` | JobManager REST port |
| `spec.service.type` | string | No | `ClusterIP` | `ClusterIP`, `NodePort`, or `LoadBalancer` |
| `spec.service.port` | integer | No | `80` | Service port |
| `spec.service.nodePort` | integer | No | — | NodePort (30000–32767, NodePort type only) |
| `spec.resources.requests` | object | No | `{cpu:50m, memory:64Mi}` | Pod resource requests |
| `spec.resources.limits` | object | No | `{cpu:200m, memory:128Mi}` | Pod resource limits |
| `spec.extraEnv` | array | No | `[]` | Extra env vars injected into the IDE container |

## Status Fields

| Field | Description |
|---|---|
| `status.conditions[].type` | `Ready` |
| `status.conditions[].status` | `True` / `False` |
| `status.message` | Human-readable reconciliation message |

## Managed Resources

The operator creates and maintains:
- `Deployment/strlab-studio-<name>` — the IDE pods
- `Service/strlab-studio-<name>` — exposes the IDE

Both have `ownerReferences` pointing to the CR so they are garbage-collected when the CR is deleted.

## Short name
`kubectl get sls` is equivalent to `kubectl get strlabstudios`