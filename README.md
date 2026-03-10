# FlinkSQL Kube Operator

> A Kubernetes operator that manages FlinkSQL Studio deployments as first-class CRDs — deploy, configure, and lifecycle-manage FlinkSQL Studio instances on any Kubernetes cluster.

![License](https://img.shields.io/badge/license-MIT-green)
![Kubernetes](https://img.shields.io/badge/kubernetes-1.24%2B-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-yellow)

---

## What is it?

The FlinkSQL Kube Operator watches for `FlinkSQLStudio` custom resources and automatically:

- Deploys and configures FlinkSQL Studio instances
- Manages nginx reverse proxy configuration to route to your Flink SQL Gateway and JobManager
- Handles upgrades, scaling, and deletion of studio instances
- Exposes status conditions on the CRD for GitOps workflows

---

## Quickstart

### Install via Helm

```bash
helm install flinksql-operator ./helm/flinksql-operator \
  --namespace flinksql-system \
  --create-namespace
```

### Deploy a Studio instance

```yaml
# examples/basic-instance.yaml
apiVersion: codedstreams.io/v1alpha1
kind: FlinkSQLStudio
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
kubectl get flinksqlstudio -n flink
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
| `spec.image` | string | `codedstreams/flinksql-studio:latest` | Studio image to deploy |
| `spec.resources` | ResourceRequirements | — | CPU/memory requests and limits |

---

## Project Structure

```
flinksql-kube-operator/
├── api/
│   └── v1alpha1/
│       └── types.py                    # CRD type definitions (Python dataclasses)
├── controllers/
│   └── flinksqlstudio_controller.py    # Reconciliation loop — kopf operator
├── config/
│   ├── crd/
│   │   └── flinksqlstudios.yaml        # CRD manifest (applied to cluster)
│   ├── manager/
│   │   └── manager.yaml                # Operator deployment manifest
│   ├── rbac/
│   │   └── rbac.yaml                   # ClusterRole + ClusterRoleBinding
│   └── samples/
│       ├── basic.yaml                  # Minimal FlinkSQLStudio CR
│       └── production.yaml             # Production CR with resources/ingress
├── examples/
│   ├── basic-instance.yaml             # Quick-start example
│   └── production-instance.yaml        # Full production example
├── helm/
│   └── flinksql-operator/
│       ├── Chart.yaml                  # Helm chart metadata
│       ├── values.yaml                 # Default values
│       └── templates/
│           └── all.yaml                # All operator resources templated
├── docs/
│   ├── CRD_REFERENCE.md                # Full CRD field reference
│   └── DEVELOPMENT.md                  # Local dev + testing guide
├── .github/
│   └── workflows/
│       └── publish.yml                 # Build and push operator image to Docker Hub
├── Dockerfile                          # Operator container image
├── requirements.txt                    # kopf, kubernetes-client, pydantic
├── LICENSE
└── README.md                           # This file
```

---

## How it works

The operator uses [kopf](https://kopf.readthedocs.io/) (Kubernetes Operator Pythonic Framework):

```python
# controllers/flinksqlstudio_controller.py

@kopf.on.create('codedstreams.io', 'v1alpha1', 'flinksqlstudios')
def create_fn(spec, name, namespace, **kwargs):
    # 1. Create nginx ConfigMap from spec.gateway / spec.jobmanager
    # 2. Create Deployment with studio image + nginx sidecar
    # 3. Create Service (ClusterIP / NodePort / LoadBalancer)
    # 4. Patch status.conditions = [{ type: Ready, status: True }]
```

---

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for local dev instructions.

```bash
# Install dependencies
pip install -r requirements.txt

# Run operator locally (uses your current kubeconfig)
kopf run controllers/flinksqlstudio_controller.py --verbose

# Apply CRD first
kubectl apply -f config/crd/flinksqlstudios.yaml
```

---

## Changelog

### v1.1 (current)
- Updated studio image reference to v8 (session isolation, cancel job, streaming results, named export)
- Added `spec.jobmanager` field to CRD for JobManager API proxy
- Updated Helm chart values for new nginx config structure
- Improved status condition reporting

### v1.0
- Initial release
- CREATE / UPDATE / DELETE reconciliation
- Helm chart
- Basic and production sample CRs

---

## License

MIT — see [LICENSE](LICENSE)

---

## Storage & PVC requirements

**The operator itself needs no PVC.** It is a stateless controller that stores all state in the Kubernetes API.

The FlinkSQL Studio pods the operator creates are also stateless by default — the nginx container serves a static HTML file and the user's workspace lives in browser `localStorage`.

A PVC is only needed if you want to:
- Serve a custom `index.html` without rebuilding the image
- Enable server-side workspace backups

See [docs/STORAGE.md](docs/STORAGE.md) for full details and YAML examples.

---

## Hosting & distribution

The operator is distributed as a Helm chart. Three hosting options:

### Option A — GitHub Pages (quickest)
```bash
helm repo add flinksql https://coded-streams.github.io/flinksql-kube-operator/charts
helm repo update
helm install flinksql-operator flinksql/flinksql-operator \
  --namespace flinksql-system --create-namespace
```

### Option B — OCI / GHCR
```bash
helm install flinksql-operator \
  oci://ghcr.io/coded-streams/helm-charts/flinksql-operator \
  --version 1.0.0 --namespace flinksql-system --create-namespace
```

### Option C — From source
```bash
helm install flinksql-operator ./helm/flinksql-operator \
  --namespace flinksql-system --create-namespace
```

For the complete hosting guide including ArtifactHub listing, OLM/OperatorHub packaging, GitHub Actions release automation, and the full release checklist, see **[docs/HOSTING.md](docs/HOSTING.md)**.

---

## Verify installation

```bash
kubectl get pods -n flinksql-system
kubectl get crd flinksqlstudios.codedstreams.io
```

## Deploy your first studio

```bash
kubectl apply -f examples/basic-instance.yaml
kubectl port-forward svc/my-studio 3030:3030 -n flink
# Open http://localhost:3030
```
