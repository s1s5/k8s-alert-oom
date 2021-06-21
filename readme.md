# alert OOM in k8s
- 

# example-manifests

``` yaml:secrets.yml
apiVersion: v1
kind: Secret
metadata:
  name: alertoom-secret
type: Opaque
stringData:
  WEBHOOK_URL: https://hooks.slack.com/services/xxxxxx/yyyyy/zzzzzzz
  ICON_URL: some-icon-url
```

```yaml:deploy.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alert-oom
spec:
  selector:
    matchLabels:
      app: alert-oom
  replicas: 1
  template:
    metadata:
      labels:
        app: alert-oom
      name: alert-oom
    spec:
      serviceAccount: admin
      containers:
      - name: alert-oom
        image: s1s5/k8s-alert-oom
        imagePullPolicy: Always
        env:
          - name: DEBUG
            value: "True"
          - name: IN_CLUSTER
            value: "True"
          - name: TZ
            value: "Asia/Tokyo"
        envFrom:
          - secretRef:
              name: alertoom-secret
        resources:
          limits:
            memory: "100Mi"
            cpu: "0.1"
          requests:
            memory: "100Mi"
            cpu: "0.01"
        livenessProbe:
          exec:
            command:
              - cat
              - /tmp/healthchecks-sendalerts-alive
          initialDelaySeconds: 60
          periodSeconds: 30
```

```yaml:admin-sa.yml
---
apiVersion: v1
kind: ServiceAccount
metadata:
metadata:
  name: admin
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-clusterrolebinding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin
  namespace: default
```
