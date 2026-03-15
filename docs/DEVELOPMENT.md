# Development Guide — Str:::lab Studio Operator

## Prerequisites

- Python 3.11+
- kubectl configured against a cluster (or minikube/kind locally)
- Docker
- kopf: `pip install kopf kubernetes pydantic`

## Local development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Apply CRD to your cluster first
kubectl apply -f config/crd/strlabstudios.yaml

# 3. Apply RBAC
kubectl apply -f config/rbac/rbac.yaml

# 4. Run the operator locally (uses your current kubeconfig)
kopf run controllers/strlabstudio_controller.py --verbose --all-namespaces

# 5. In another terminal, apply a sample CR
kubectl apply -f config/samples/basic.yaml

# 6. Watch the operator react
kubectl get strlabstudio -A -w
kubectl describe strlabstudio dev -n default
```

## Testing

```bash
# Apply the basic sample
kubectl apply -f config/samples/basic.yaml

# Check status
kubectl get strlabstudio dev -n default -o yaml | grep -A10 status

# Port-forward to access the studio
kubectl port-forward svc/strlab-studio-dev 3030:80 -n default
# Open http://localhost:3030

# Delete and verify cleanup
kubectl delete strlabstudio dev -n default
kubectl get pods -n default  # should show no strlab-studio pods
```

## Project structure

```
strlab-kube-operator/
├── api/v1alpha1/types.py                    # CRD type definitions
├── controllers/strlabstudio_controller.py   # Reconciliation logic
├── config/
│   ├── crd/strlabstudios.yaml              # CRD manifest
│   ├── manager/manager.yaml                # Operator deployment
│   ├── rbac/rbac.yaml                      # ClusterRole + binding
│   └── samples/                            # Example CRs
├── helm/strlab-operator/                   # Helm chart
└── docs/
    ├── DEVELOPMENT.md
    ├── CRD_REFERENCE.md
    ├── STORAGE.md
    └── HOSTING.md
```