# Storage Guide — PVC and Persistence

## Does the operator need a PVC?

**No — the operator itself does not need a PVC.** The operator is a stateless controller that runs as a single pod and uses the Kubernetes API for all state. It needs no disk storage of its own.

```
Operator pod (flinksqlstudio-operator)
    └── No PVC needed
    └── Reads/writes only to Kubernetes API (ConfigMaps, Deployments, Services)
```

## What about the FlinkSQL Studio instances it creates?

The studio instances the operator creates are also **stateless by default** — the nginx container serving the HTML file has no state. The user's workspace (tabs, SQL, history) is saved in the browser's `localStorage`, not on the server.

```
FlinkSQL Studio pod
    └── nginx serving index.html  ← stateless, no PVC needed
    └── User workspace            ← stored in browser localStorage
```

## When would you use a PVC?

You only need a PVC if you want to:

### 1. Persist the studio HTML file outside the image

If you want to update `index.html` without rebuilding the Docker image:

```yaml
# In your FlinkSQLStudio CR:
spec:
  studioVolume:
    persistentVolumeClaim:
      claimName: flinksql-studio-html

# The operator creates a Deployment that mounts:
# /usr/share/nginx/html/index.html from the PVC
```

```yaml
# PVC to create manually before applying the CR:
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: flinksql-studio-html
  namespace: flink
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 50Mi
  storageClassName: standard
```

### 2. Back up user workspaces server-side

By default workspaces live in browser localStorage only. To persist them server-side, you can configure an nginx proxy that saves workspace exports to a mounted volume:

```yaml
spec:
  workspaceStorage:
    enabled: true
    storageClassName: standard
    size: 1Gi
```

The operator will create the PVC and mount it at `/workspace-exports/` in the studio pod.

### 3. Flink cluster checkpoints and savepoints

This is outside the studio operator's scope — configure this in your Flink cluster's `docker-compose.yml` or Flink operator. The studio is a UI layer only.

## Summary

| Component | PVC needed? | Why |
|---|---|---|
| Operator controller pod | No | Stateless — uses Kubernetes API |
| Studio pod (default) | No | Stateless — workspace in browser |
| Studio pod (server-side workspace backup) | Optional | Mount at `/workspace-exports/` |
| Studio pod (custom HTML without image rebuild) | Optional | Mount `index.html` from PVC |
| Flink JM/TM checkpoints | Yes (separate) | Managed by your Flink cluster, not this operator |
