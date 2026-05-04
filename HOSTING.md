# Hosting the Str:::lab Studio Operator — Helm Chart Repository Guide

This guide covers every option for hosting and distributing the
Str:::lab Studio Kube Operator.

---

## Option 1: GitHub Pages (simplest, free)

### Step 1 — Package the chart
```bash
helm package helm/strlab-operator --destination ./public/charts
# Creates: public/charts/strlab-operator-1.0.0.tgz
```

### Step 2 — Generate the chart index
```bash
helm repo index public/charts/ --url https://coded-streams.github.io/strlabstudio-operator/charts
```

### Step 3 — Enable GitHub Pages
1. Go to your GitHub repo → **Settings → Pages**
2. Set source to **Branch: gh-pages**, folder: **/ (root)**
3. The CI pipeline handles packaging and publishing automatically on every tag push

### Step 4 — Users install it
```bash
helm repo add strlabstudio https://coded-streams.github.io/strlabstudio-operator/charts
helm repo update
helm install strlab-operator strlabstudio/strlab-operator \
  --namespace strlab-system --create-namespace
```

### Automated via GitHub Actions
The `.github/workflows/publish.yml` pipeline handles this automatically on every `v*.*.*` tag push — no manual steps needed after initial setup.

---

## Option 2: OCI Registry (GHCR or Docker Hub)

```bash
# Login
echo $GITHUB_TOKEN | helm registry login ghcr.io -u YOUR_GITHUB_USER --password-stdin

# Package and push
helm package helm/strlab-operator
helm push strlab-operator-1.0.0.tgz oci://ghcr.io/coded-streams/helm-charts

# Users install with:
helm install strlab-operator \
  oci://ghcr.io/coded-streams/helm-charts/strlab-operator \
  --version 1.0.0 --namespace strlab-system --create-namespace
```

---

## Option 3: ArtifactHub

1. Go to https://artifacthub.io → **Add repository**
2. Choose **Helm charts**
3. Enter: `https://coded-streams.github.io/strlabstudio-operator/charts`

Add to `helm/strlab-operator/Chart.yaml`:
```yaml
annotations:
  artifacthub.io/license: Apache-2.0
  artifacthub.io/maintainers: |
    - name: Coded Streams
      email: nestorabiawuh@gmail.com
  artifacthub.io/category: streaming-messaging
  artifacthub.io/keywords: |
    - flink
    - sql
    - streaming
    - kubernetes
    - operator
```

---

## Full release checklist

```bash
# 1. Bump version in helm/strlab-operator/Chart.yaml

# 2. Commit and tag — CI handles image build + helm publish automatically
git add .
git commit -m "chore: release v1.2.0"
git tag v1.2.0
git push origin main --tags
```

---

## Quick reference — install options

```bash
# GitHub Pages
helm repo add strlabstudio https://coded-streams.github.io/strlabstudio-operator/charts
helm install strlab-operator strlabstudio/strlab-operator \
  --namespace strlab-system --create-namespace

# OCI
helm install strlab-operator \
  oci://ghcr.io/coded-streams/helm-charts/strlab-operator \
  --version 1.0.0 --namespace strlab-system --create-namespace

# From source
helm install strlab-operator ./helm/strlab-operator \
  --namespace strlab-system --create-namespace

# Verify
kubectl get pods -n strlab-system
kubectl get crd strlabstudios.codedstreams.io

# Deploy first instance
kubectl apply -f - <<EOF
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
    port: 80
EOF

kubectl port-forward svc/strlab-studio-my-studio 3030:80 -n flink
# Open http://localhost:3030
```