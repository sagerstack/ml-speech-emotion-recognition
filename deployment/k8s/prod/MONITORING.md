# Monitoring Stack Deployment Guide

This guide explains how to enable/disable monitoring (Prometheus + Grafana + Loki) for your EKS deployment.

## 📊 What's Included

The monitoring stack includes:
- **Prometheus** - Metrics collection from backend `/metrics` endpoint
- **Grafana** - Visualization dashboards
- **Loki** - Log aggregation

## ✅ Prerequisites

1. EKS cluster deployed (`./deployment/terraform/tf-apply.sh`)
2. Main application deployed via CD workflow
3. `kubectl` configured to access your cluster

```bash
aws eks update-kubeconfig --name ml-speech-emotion-prod-eks --region us-east-1 --profile ml-ser-deploy
```

## 🚀 Enable Monitoring

### Option 1: Using kubectl (Recommended)

```bash
# Deploy monitoring stack
kubectl apply -f deployment/k8s/prod/monitoring-stack.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=prometheus -n monitoring --timeout=120s
kubectl wait --for=condition=ready pod -l app=grafana -n monitoring --timeout=120s
kubectl wait --for=condition=ready pod -l app=loki -n monitoring --timeout=120s

# Verify deployment
kubectl get pods -n monitoring
```

### Option 2: Port-forward to Access Grafana

```bash
# Forward Grafana to localhost
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Access Grafana at: http://localhost:3000
# Login: admin / admin
```

### Option 3: Enable External Access via Ingress

Edit `monitoring-stack.yaml` and uncomment the `Ingress` section at the bottom, then:

```bash
kubectl apply -f deployment/k8s/prod/monitoring-stack.yaml

# Get ALB DNS name
kubectl get ingress -n monitoring monitoring-ingress
```

## 📈 Access Dashboards

### Grafana (Primary UI)
- **Port-forward**: `http://localhost:3000`
- **Credentials**: `admin` / `admin` (change on first login!)

**Pre-configured datasources:**
- Prometheus (default)
- Loki

### Prometheus (Direct Access)
```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Access at: http://localhost:9090
```

## 🔍 Verify Metrics Collection

### Check if Backend Metrics are Being Scraped

```bash
# Port-forward to Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Open http://localhost:9090/targets
# Look for "backend" job - should show State: UP
```

### Sample PromQL Queries

```promql
# Request rate over last 5 minutes
rate(http_requests_total[5m])

# P95 request latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate percentage
sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100

# Prediction requests by emotion
sum(prediction_requests_total) by (emotion)
```

## ❌ Disable Monitoring

### Complete Removal

```bash
# Delete monitoring stack
kubectl delete -f deployment/k8s/prod/monitoring-stack.yaml

# Verify namespace is gone
kubectl get namespace monitoring
```

### Keep Data, Stop Pods (Scale to Zero)

```bash
kubectl scale deployment prometheus --replicas=0 -n monitoring
kubectl scale deployment grafana --replicas=0 -n monitoring
kubectl scale deployment loki --replicas=0 -n monitoring
```

### Resume from Scale-to-Zero

```bash
kubectl scale deployment prometheus --replicas=1 -n monitoring
kubectl scale deployment grafana --replicas=1 -n monitoring
kubectl scale deployment loki --replicas=1 -n monitoring
```

## 🛠️ Troubleshooting

### Prometheus Not Scraping Backend

1. Check Prometheus targets:
   ```bash
   kubectl port-forward -n monitoring svc/prometheus 9090:9090
   # Open http://localhost:9090/targets
   ```

2. Verify backend pod annotations:
   ```bash
   kubectl get pods -n ml-speech-emotion -o yaml | grep -A 3 "annotations:"
   # Should see:
   #   prometheus.io/scrape: "true"
   #   prometheus.io/port: "9090"
   #   prometheus.io/path: "/metrics"
   ```

3. Test backend metrics endpoint:
   ```bash
   kubectl port-forward -n ml-speech-emotion svc/backend 8000:8000
   curl http://localhost:8000/metrics
   ```

### Grafana Dashboards Not Showing Data

1. Verify Prometheus datasource:
   - Grafana → Configuration → Data Sources → Prometheus
   - Click "Test" button - should show "Data source is working"

2. Check time range in dashboard (top-right corner)

3. Generate traffic to populate metrics:
   ```bash
   # Forward streamlit
   kubectl port-forward -n ml-speech-emotion svc/streamlit 8501:8501
   # Use the app to generate requests
   ```

### No Logs in Loki

1. Check Loki is running:
   ```bash
   kubectl get pods -n monitoring -l app=loki
   ```

2. Verify Loki datasource in Grafana

3. Check Loki logs:
   ```bash
   kubectl logs -n monitoring -l app=loki
   ```

### Persistent Volume Issues

If PVCs are stuck in "Pending":

```bash
# Check PVC status
kubectl get pvc -n monitoring

# Describe PVC for details
kubectl describe pvc prometheus-pvc -n monitoring

# Common issue: StorageClass not available
kubectl get storageclass
# Should see "gp3" storage class
```

## 📊 Storage Information

**Persistent Volumes Created:**
- `prometheus-pvc`: 20Gi (metrics storage, 30 days retention)
- `grafana-pvc`: 10Gi (dashboard configs, users, settings)
- `loki-pvc`: 20Gi (logs storage)

**Total**: ~50Gi EBS storage

**Storage Class**: gp3 (AWS EBS)

## 🔄 Updating Monitoring Configuration

### Update Prometheus Configuration

```bash
# Edit ConfigMap
kubectl edit configmap prometheus-config -n monitoring

# Restart Prometheus to reload config
kubectl rollout restart deployment/prometheus -n monitoring
```

### Update Grafana Admin Password

```bash
# Edit secret
kubectl edit secret grafana-secret -n monitoring

# Restart Grafana
kubectl rollout restart deployment/grafana -n monitoring
```

## 💰 Cost Considerations

**EBS Volumes**: ~$5-10/month for 50Gi gp3 storage
**EC2 Resources**: Monitoring pods use ~2.5Gi RAM, 1.0 CPU total

To reduce costs:
- Scale monitoring to zero when not needed
- Reduce Prometheus retention from 30d to 7d
- Use smaller PVC sizes

## 🔐 Security Best Practices

1. **Change Grafana admin password** immediately:
   ```bash
   kubectl create secret generic grafana-secret \
     -n monitoring \
     --from-literal=admin-password='YourSecurePassword' \
     --dry-run=client -o yaml | kubectl apply -f -

   kubectl rollout restart deployment/grafana -n monitoring
   ```

2. **Don't expose Grafana publicly** without authentication

3. **Use RBAC** to control access to monitoring namespace

## 📚 Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)

## 🆘 Need Help?

Check logs for each component:

```bash
# Prometheus logs
kubectl logs -n monitoring -l app=prometheus --tail=100

# Grafana logs
kubectl logs -n monitoring -l app=grafana --tail=100

# Loki logs
kubectl logs -n monitoring -l app=loki --tail=100
```

---

**Last Updated**: 2025-12-01
**Maintained by**: ML Speech Emotion Recognition Team
