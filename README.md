# Str:::lab Studio Kube Operator

> A Kubernetes operator that manages Str:::lab Studio deployments as first-class CRDs — deploy, configure, and lifecycle-manage Str:::lab Studio instances on any Kubernetes cluster.

![License](https://img.shields.io/badge/license-Apache%202.0-green)
![Kubernetes](https://img.shields.io/badge/kubernetes-1.24%2B-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-yellow)

> **Apache Flink** is a trademark of the Apache Software Foundation.
> Str:::lab Studio is an independent project not affiliated with the Apache Software Foundation.

---

## What is it?

The Str:::lab Studio Kube Operator watches for `StrlabStudio` custom resources and automatically:

- Deploys and configures Str:::lab Studio instances
- Manages nginx reverse proxy configuration to route to your Flink SQL Gateway and JobManager
- Handles upgrades, scaling, and deletion of studio instances
- Exposes status conditions on the CRD for GitOps workflows

---

## Quickstart

### Install via Helm

```bash
helm repo add strlabstudio https://coded-streams.github.io/strlab-kube-operator/charts
helm repo update
helm install strlab-operator strlabstudio/strlab-operator \
  --namespace strlab-system \
  --create-namespace
```

### Deploy a Studio instance

```yaml
# examples/basic-instance.yaml
apiVersion: codedstreams.io/v1alpha1
kind: StrlabStudio
metadata:
  name: my-studio
  namespace: flink
spec:
  replicas: 1
  gateway:
    host: flink-sql-gateway
    port: 8083
  jobmanager:
    host: flink-jobmanager
    port: 8081
  service:
    type: ClusterIP
    port: 3030
```

```bash
kubectl apply -f examples/basic-instance.yaml
kubectl get strlabstudio -n flink
```

---

## CRD Reference

See [docs/CRD_REFERENCE.md](docs/CRD_REFERENCE.md) for full spec documentation.

### Core fields

| Field | Type | Default | Description |
|---|---|---|---|
| `spec.replicas` | int | `1` | Number of studio pods |
| `spec.gateway.host` | string | required | Flink SQL Gateway hostname |
| `spec.gateway.port` | int | `8083` | Gateway port |
| `spec.jobmanager.host` | string | required | JobManager hostname |
| `spec.jobmanager.port` | int | `8081` | JobManager REST port |
| `spec.service.type` | string | `ClusterIP` | `ClusterIP`, `NodePort`, or `LoadBalancer` |
| `spec.image` | string | `codedstreams/strlabstudio:latest` | Studio image to deploy |
| `spec.resources` | ResourceRequirements | — | CPU/memory requests and limits |

---

## Project Structure

```
strlab-kube-operator/
├── api/
│   └── v1alpha1/
│       └── types.py                     # CRD type definitions (Python dataclasses)
├── controllers/
│   └── strlabstudio_controller.py       # Reconciliation loop — kopf operator
├── config/
│   ├── crd/
│   │   └── strlabstudios.yaml           # CRD manifest (applied to cluster)
│   ├── manager/
│   │   └── manager.yaml                 # Operator deployment manifest
│   ├── rbac/
│   │   └── rbac.yaml                    # ClusterRole + ClusterRoleBinding
│   └── samples/
│       ├── basic.yaml                   # Minimal StrlabStudio CR
│       └── production.yaml              # Production CR with resources
├── examples/
│   ├── basic-instance.yaml              # Quick-start example
│   └── production-instance.yaml         # Full production example
├── helm/
│   └── strlab-operator/
│       ├── Chart.yaml                   # Helm chart metadata
│       ├── values.yaml                  # Default values
│       └── templates/
│           └── all.yaml                 # All operator resources templated
├── docs/
│   ├── CRD_REFERENCE.md                 # Full CRD field reference
│   ├── DEVELOPMENT.md                   # Local dev + testing guide
│   ├── HOSTING.md                       # Helm chart hosting guide
│   └── STORAGE.md                       # PVC / storage guide
├── .github/
│   └── workflows/
│       └── publish.yml                  # Build and push operator image to Docker Hub
├── Dockerfile                           # Operator container image
├── requirements.txt                     # kopf, kubernetes-client, pydantic
├── LICENSE
└── README.md
```

---

## How it works

The operator uses [kopf](https://kopf.readthedocs.io/) (Kubernetes Operator Pythonic Framework):

```python
# controllers/strlabstudio_controller.py

@kopf.on.create('codedstreams.io', 'v1alpha1', 'strlabstudios')
def reconcile(spec, name, namespace, **kwargs):
    # 1. Parse spec into typed StrlabStudioSpec dataclass
    # 2. Create/update Deployment (strlab-studio-<name>) with studio image
    # 3. Create/update Service (strlab-studio-<name>)
    # 4. ownerReferences ensure GC on CR deletion
```

---

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for local dev instructions.

```bash
# Install dependencies
pip install -r requirements.txt

# Apply CRD first
kubectl apply -f config/crd/strlabstudios.yaml

# Run operator locally (uses your current kubeconfig)
kopf run controllers/strlabstudio_controller.py --verbose

# Apply a sample CR
kubectl apply -f config/samples/basic.yaml

# Watch it
kubectl get strlabstudio -A -w
```

---

## Hosting & distribution

### Option A — GitHub Pages (recommended)
```bash
helm repo add strlabstudio https://coded-streams.github.io/strlab-kube-operator/charts
helm repo update
helm install strlab-operator strlabstudio/strlab-operator \
  --namespace strlab-system --create-namespace
```

### Option B — OCI / GHCR
```bash
helm install strlab-operator \
  oci://ghcr.io/coded-streams/helm-charts/strlab-operator \
  --version 1.0.0 --namespace strlab-system --create-namespace
```

### Option C — From source
```bash
helm install strlab-operator ./helm/strlab-operator \
  --namespace strlab-system --create-namespace
```

See [docs/HOSTING.md](docs/HOSTING.md) for the full guide including ArtifactHub, OLM/OperatorHub, and the release checklist.

---

## Verify installation

```bash
kubectl get pods -n strlab-system
# NAME                                 READY   STATUS    RESTARTS
# strlabstudio-operator-xxx-yyy        1/1     Running   0

kubectl get crd strlabstudios.codedstreams.io
```

## Deploy your first studio

```bash
kubectl apply -f examples/basic-instance.yaml
kubectl port-forward svc/strlab-studio-dev 3030:80 -n default
# Open http://localhost:3030
```

---

## Changelog

### v1.2 (current)
- Renamed from FlinkSQL Studio Kube Operator to **Str:::lab Studio Kube Operator**
- CRD kind renamed `FlinkSQLStudio` → `StrlabStudio`, plural `flinksqlstudios` → `strlabstudios`
- Short name changed from `fss` → `sls`
- All resource names, namespaces, and image references updated
- Studio image updated to `codedstreams/strlabstudio:v1.0.22`

### v1.0
- Initial release — CREATE/UPDATE/DELETE reconciliation, Helm chart, basic and production sample CRs

---

## Storage & PVC

**The operator itself needs no PVC.** It is a stateless controller using the Kubernetes API for all state.

The Str:::lab Studio pods it creates are also stateless by default — nginx serves a static file and the user workspace lives in browser `localStorage`.

See [docs/STORAGE.md](docs/STORAGE.md) for optional PVC usage (custom HTML, server-side workspace backups).

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).
Created by **Nestor A. A** · [coded-streams](https://github.com/coded-streams)