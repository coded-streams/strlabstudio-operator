# Hosting the Str:::lab Studio Operator — Helm Chart Repository Guide

This guide covers every option for hosting and distributing the
Str:::lab Studio Kube Operator.

---

## Option 1: GitHub Pages (simplest, free)

### Step 1 — Package the chart
```bash
helm package helm/strlab-operator --destination ./charts
# Creates: charts/strlab-operator-1.0.0.tgz
```

### Step 2 — Generate the chart index
```bash
helm repo index charts/ --url https://coded-streams.github.io/strlab-kube-operator/charts
```

### Step 3 — Enable GitHub Pages
1. Go to your GitHub repo → **Settings → Pages**
2. Set source to **Branch: main**, folder: **/ (root)**
3. Commit and push the `charts/` folder

### Step 4 — Users install it
```bash
helm repo add strlabstudio https://coded-streams.github.io/strlab-kube-operator/charts
helm repo update
helm install strlab-operator strlabstudio/strlab-operator \
  --namespace strlab-system --create-namespace
```

### Automate with GitHub Actions
```yaml
name: Release Helm Chart
on:
  push:
    tags: ['v*']
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Install Helm
        uses: azure/setup-helm@v3
      - name: Package chart
        run: helm package helm/strlab-operator --destination charts/
      - name: Update index
        run: |
          helm repo index charts/ \
            --url https://coded-streams.github.io/strlab-kube-operator/charts
      - name: Push to gh-pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./charts
          destination_dir: charts
```

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
3. Enter: `https://coded-streams.github.io/strlab-kube-operator/charts`

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
# 1. Bump version in Chart.yaml and values.yaml

# 2. Build and push operator image
docker build -t codedstreams/strlab-kube-operator:1.1.0 .
docker push codedstreams/strlab-kube-operator:1.1.0
docker tag  codedstreams/strlab-kube-operator:1.1.0 \
            codedstreams/strlab-kube-operator:latest
docker push codedstreams/strlab-kube-operator:latest

# 3. Package and push Helm chart
helm package helm/strlab-operator --destination charts/
helm repo index charts/ --url https://coded-streams.github.io/strlab-kube-operator/charts
git add charts/ && git commit -m "chore: release chart v1.1.0" && git push

# 4. Also push as OCI artifact
helm push charts/strlab-operator-1.1.0.tgz oci://ghcr.io/coded-streams/helm-charts

# 5. Create GitHub release tag
git tag v1.1.0 && git push origin v1.1.0
```

---

## Quick reference — install options

```bash
# GitHub Pages
helm repo add strlabstudio https://coded-streams.github.io/strlab-kube-operator/charts
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