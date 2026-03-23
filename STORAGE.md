# Storage Guide — PVC and Persistence

## Does the operator need a PVC?

**No — the operator itself does not need a PVC.** The operator is a stateless controller that uses the Kubernetes API for all state.

```
Operator pod (strlabstudio-operator)
    └── No PVC needed
    └── Reads/writes only to Kubernetes API (ConfigMaps, Deployments, Services)
```

## What about the Str:::lab Studio instances it creates?

The studio instances the operator creates are also **stateless by default** — the nginx container serving the HTML file has no state. The user's workspace is saved in browser `localStorage`.

```
Str:::lab Studio pod
    └── nginx serving index.html  ← stateless, no PVC needed
    └── User workspace            ← stored in browser localStorage
```

## When would you use a PVC?

### 1. Persist the studio HTML file outside the image

```yaml
# In your StrlabStudio CR:
spec:
  studioVolume:
    persistentVolumeClaim:
      claimName: strlab-studio-html
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: strlab-studio-html
  namespace: flink
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 50Mi
  storageClassName: standard
```

### 2. Server-side workspace backups

```yaml
spec:
  workspaceStorage:
    enabled: true
    storageClassName: standard
    size: 1Gi
```

## Summary

| Component | PVC needed? | Why |
|---|---|---|
| Operator controller pod | No | Stateless — uses Kubernetes API |
| Studio pod (default) | No | Stateless — workspace in browser |
| Studio pod (server-side backup) | Optional | Mount at `/workspace-exports/` |
| Studio pod (custom HTML) | Optional | Mount `index.html` from PVC |
| Flink JM/TM checkpoints | Yes (separate) | Managed by your Flink cluster, not this operator |