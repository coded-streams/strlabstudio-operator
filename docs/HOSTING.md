# Hosting the FlinkSQL Studio Operator — Helm Chart Repository Guide

This guide walks through every option for hosting and distributing the
FlinkSQL StudioKube Operator, from a simple GitHub Pages chart repo to
ArtifactHub and OCI registries.

---

## Option 1: GitHub Pages (simplest, free)

This is the standard way most open-source operators are distributed.
Helm treats any static HTTP server serving an `index.yaml` as a valid chart repo.

### Step 1 — Package the chart

```bash
# From the repo root
helm package helm/flinksql-operator --destination ./charts
# Creates: charts/flinksql-operator-1.0.0.tgz
```

### Step 2 — Generate the chart index

```bash
helm repo index charts/ --url https://coded-streams.github.io/flinksql-kube-operator/charts
# Creates: charts/index.yaml
```

### Step 3 — Enable GitHub Pages

1. Go to your GitHub repo → **Settings → Pages**
2. Set source to **Branch: main**, folder: **/ (root)** or **/docs**
3. Commit and push the `charts/` folder

### Step 4 — Users install it

```bash
helm repo add flinksql https://coded-streams.github.io/flinksql-kube-operator/charts
helm repo update
helm install flinksql-operator flinksql/flinksql-operator \
  --namespace flinksql-system \
  --create-namespace
```

### Automate packaging with GitHub Actions

```yaml
# .github/workflows/release-chart.yml
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
        run: helm package helm/flinksql-operator --destination charts/

      - name: Update index
        run: |
          helm repo index charts/ \
            --url https://coded-streams.github.io/flinksql-kube-operator/charts

      - name: Push to gh-pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./charts
          destination_dir: charts
```

---

## Option 2: OCI Registry (Docker Hub or GHCR) — modern approach

Helm 3.8+ supports storing charts as OCI artifacts alongside Docker images.
This is the direction the Helm ecosystem is moving.

### Push to GitHub Container Registry (GHCR)

```bash
# Login
echo $GITHUB_TOKEN | helm registry login ghcr.io -u YOUR_GITHUB_USER --password-stdin

# Package
helm package helm/flinksql-operator

# Push
helm push flinksql-operator-1.0.0.tgz oci://ghcr.io/coded-streams/helm-charts

# Users install with:
helm install flinksql-operator \
  oci://ghcr.io/coded-streams/helm-charts/flinksql-operator \
  --version 1.0.0 \
  --namespace flinksql-system \
  --create-namespace
```

### Push to Docker Hub

```bash
helm registry login registry-1.docker.io -u codedstreams
helm push flinksql-operator-1.0.0.tgz oci://registry-1.docker.io/codedstreams/helm-charts
```

---

## Option 3: ArtifactHub — discoverability

[ArtifactHub](https://artifacthub.io) is the official Helm chart search engine
(like Docker Hub but for charts). It indexes your chart automatically.

### Register your repo on ArtifactHub

1. Go to https://artifacthub.io → **Sign up** → **Add repository**
2. Choose **Helm charts** as the type
3. Enter your GitHub Pages URL:
   ```
   https://coded-streams.github.io/flinksql-kube-operator/charts
   ```
4. ArtifactHub will index it within minutes

### Add ArtifactHub metadata (optional but recommended)

Create `helm/flinksql-operator/artifacthub-repo.yml` at your repo root:

```yaml
repositoryID: <your-artifacthub-repo-id>
owners:
  - name: Coded Streams
    email: nestorabiawuh@gmail.com
```

### Add chart annotations for better listing

In `helm/flinksql-operator/Chart.yaml`:

```yaml
annotations:
  artifacthub.io/license: MIT
  artifacthub.io/maintainers: |
    - name: Coded Streams
      email: nestorabiawuh@gmail.com
  artifacthub.io/category: streaming-messaging
  artifacthub.io/keywords: |
    - flink
    - sql
    - streaming
    - kafka
    - kubernetes
    - operator
```

---

## Option 4: OperatorHub.io — for Kubernetes operators specifically

[OperatorHub.io](https://operatorhub.io) is to Kubernetes operators what
ArtifactHub is to Helm charts. It's bundled into OpenShift and also indexed
by the Operator Lifecycle Manager (OLM).

### What you need

To list on OperatorHub you need to package using the **Operator Bundle** format:

```
bundle/
├── manifests/
│   ├── flinksqlstudio-operator.clusterserviceversion.yaml  # OLM CSV
│   ├── flinksqlstudios.crd.yaml
│   └── flinksqlstudio-operator.deployment.yaml
├── metadata/
│   └── annotations.yaml
└── Dockerfile.bundle
```

This is more involved than a Helm chart and usually worthwhile once you have
a mature operator. For now, ArtifactHub + GitHub Pages covers 95% of users.

---

## Recommended hosting strategy for FlinkSQL Studio Operator

| Phase | Action |
|---|---|
| **Now** | GitHub Pages chart repo + ArtifactHub listing |
| **v1.1** | OCI push to GHCR alongside existing GitHub Pages |
| **v2.0** | OperatorHub listing with OLM bundle |

### Full release checklist

```bash
# 1. Bump version in Chart.yaml and values.yaml
# 2. Build and push operator image
docker build -t codedstreams/flinksql-kube-operator:1.1.0 .
docker push codedstreams/flinksql-kube-operator:1.1.0
docker tag codedstreams/flinksql-kube-operator:1.1.0 codedstreams/flinksql-kube-operator:latest
docker push codedstreams/flinksql-kube-operator:latest

# 3. Package and push Helm chart
helm package helm/flinksql-operator --destination charts/
helm repo index charts/ --url https://coded-streams.github.io/flinksql-kube-operator/charts
git add charts/ && git commit -m "chore: release chart v1.1.0" && git push

# 4. Also push as OCI artifact
helm push charts/flinksql-operator-1.1.0.tgz oci://ghcr.io/coded-streams/helm-charts

# 5. Create GitHub release tag
git tag v1.1.0 && git push origin v1.1.0
```

---

## Installing the operator — quick reference

### From GitHub Pages (HTTP repo)
```bash
helm repo add flinksql https://coded-streams.github.io/flinksql-kube-operator/charts
helm repo update
helm install flinksql-operator flinksql/flinksql-operator \
  --namespace flinksql-system --create-namespace
```

### From OCI (GHCR)
```bash
helm install flinksql-operator \
  oci://ghcr.io/coded-streams/helm-charts/flinksql-operator \
  --version 1.0.0 --namespace flinksql-system --create-namespace
```

### From source (development)
```bash
helm install flinksql-operator ./helm/flinksql-operator \
  --namespace flinksql-system --create-namespace
```

### Verify installation
```bash
kubectl get pods -n flinksql-system
# NAME                                    READY   STATUS    RESTARTS
# flinksqlstudio-operator-xxx-yyy         1/1     Running   0

kubectl get crd flinksqlstudios.codedstreams.io
# NAME                                  CREATED AT
# flinksqlstudios.codedstreams.io       2026-03-10T...
```

### Deploy your first studio instance
```bash
kubectl apply -f - <<EOF
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
EOF

kubectl port-forward svc/my-studio 3030:3030 -n flink
# Open http://localhost:3030
```
