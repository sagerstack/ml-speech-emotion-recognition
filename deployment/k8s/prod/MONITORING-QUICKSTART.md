# Monitoring Stack - Quick Reference Card

## 🚀 TL;DR - Enable Monitoring in 3 Commands

```bash
# 1. Configure kubectl
aws eks update-kubeconfig --name ml-speech-emotion-prod-eks --region us-east-1 --profile ml-ser-deploy

# 2. Deploy monitoring
kubectl apply -f deployment/k8s/prod/monitoring-stack.yaml

# 3. Access Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000
# Open: http://localhost:3000 (admin/admin)
```

## ❌ Disable Monitoring

```bash
# Complete removal
kubectl delete -f deployment/k8s/prod/monitoring-stack.yaml

# OR scale to zero (keeps data)
cd deployment/terraform && ./monitoring-cleanup.sh --keep
```

## 🔍 Quick Health Checks

```bash
# Check all monitoring pods
kubectl get pods -n monitoring

# Check if Prometheus is scraping backend
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Open: http://localhost:9090/targets

# Test backend metrics endpoint
kubectl port-forward -n ml-speech-emotion svc/backend 8000:8000
curl http://localhost:8000/metrics
```

## 📊 Access URLs (Port-Forward Required)

```bash
# Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000
# → http://localhost:3000 (admin/admin)

# Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# → http://localhost:9090

# Backend Metrics
kubectl port-forward -n ml-speech-emotion svc/backend 8000:8000
# → http://localhost:8000/metrics
```

## 🎯 Useful PromQL Queries

```promql
# Request rate
rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error percentage
sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100

# Predictions by emotion
sum(prediction_requests_total) by (emotion)
```

## 🔧 Common Issues & Fixes

### Prometheus Not Scraping

```bash
# Check backend annotations
kubectl get pods -n ml-speech-emotion -o yaml | grep -A 3 "prometheus.io"

# View Prometheus logs
kubectl logs -n monitoring -l app=prometheus --tail=50
```

### Grafana Shows No Data

```bash
# Generate traffic
kubectl port-forward -n ml-speech-emotion svc/streamlit 8501:8501
# Use the app

# Check time range in Grafana
# Set to "Last 15 minutes"
```

### PVC Stuck Pending

```bash
# Check storage class
kubectl get storageclass

# Describe PVC
kubectl describe pvc prometheus-pvc -n monitoring
```

## 📁 Files Created

```
deployment/k8s/prod/
├── monitoring-stack.yaml        # Main monitoring manifest
├── MONITORING.md                # Full deployment guide
└── MONITORING-QUICKSTART.md     # This file

deployment/terraform/
└── monitoring-cleanup.sh        # Cleanup script

MONITORING_AWS_DEPLOYMENT_SUMMARY.md  # Complete overview
```

## 💡 Key Points

✅ Monitoring is **optional** and separate from main app
✅ **No changes** to existing terraform, CD, or kustomization
✅ Can be **enabled/disabled** without affecting app
✅ Uses **same stack** as local development
✅ **Easy rollback** - just delete the namespace

## 📚 Full Documentation

- **Detailed Guide**: `deployment/k8s/prod/MONITORING.md`
- **Overview**: `MONITORING_AWS_DEPLOYMENT_SUMMARY.md`
- **Local Setup**: `deployment/monitoring/README.md`

---

**Need Help?** Check logs:
```bash
kubectl logs -n monitoring -l app=prometheus --tail=100
kubectl logs -n monitoring -l app=grafana --tail=100
kubectl logs -n monitoring -l app=loki --tail=100
```
