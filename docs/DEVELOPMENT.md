# Development Guide — FlinkSQL Studio Operator

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
kubectl apply -f config/crd/flinksqlstudios.yaml

# 3. Apply RBAC
kubectl apply -f config/rbac/rbac.yaml

# 4. Run the operator locally (uses your current kubeconfig)
kopf run controllers/flinksqlstudio_controller.py --verbose --all-namespaces

# 5. In another terminal, apply a sample CR
kubectl apply -f config/samples/basic.yaml

# 6. Watch the operator react
kubectl get flinksqlstudio -A -w
kubectl describe flinksqlstudio my-studio -n flink
```

## Testing

```bash
# Apply the basic sample
kubectl apply -f config/samples/basic.yaml

# Check status
kubectl get flinksqlstudio my-studio -n flink -o yaml | grep -A10 status

# Port-forward to access the studio
kubectl port-forward svc/my-studio 3030:3030 -n flink
# Open http://localhost:3030

# Delete and verify cleanup
kubectl delete flinksqlstudio my-studio -n flink
kubectl get pods -n flink  # should show no studio pods
```

## Project structure

```
flinksql-kube-operator/
├── api/v1alpha1/types.py                    # CRD type definitions
├── controllers/flinksqlstudio_controller.py  # Reconciliation logic
├── config/
│   ├── crd/flinksqlstudios.yaml             # CRD manifest
│   ├── manager/manager.yaml                 # Operator deployment
│   ├── rbac/rbac.yaml                       # ClusterRole + binding
│   └── samples/                             # Example CRs
├── helm/flinksql-operator/                  # Helm chart
└── docs/
    ├── DEVELOPMENT.md                       
    ├── CRD_REFERENCE.md                     
    ├── STORAGE.md                           # PVC / storage guide
    └── HOSTING.md                           # Helm chart hosting guide
```
