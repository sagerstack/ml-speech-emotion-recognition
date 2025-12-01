# Monitoring Stack - Deployment Summary

## 📋 Overview

This document summarizes the monitoring infrastructure setup for both **local** (docker-compose) and **AWS EKS** environments.

---

## 🏠 Local Development (Docker Compose)

### What's Already Working ✅

Your local monitoring stack is **fully functional** via docker-compose:

```bash
# Start monitoring stack
docker-compose --profile monitoring up -d

# Access dashboards
# Grafana:    http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9090
# Backend:    http://localhost:8000/metrics
```

**Services Included:**
- ✅ Prometheus (port 9090)
- ✅ Grafana (port 3001)
- ✅ Loki (port 3100)
- ✅ Promtail (log collection)

**Backend Integration:**
- ✅ Metrics endpoint: `http://localhost:8000/metrics`
- ✅ Prometheus annotations on pods
- ✅ Automatic scraping configured

---

## ☁️ AWS EKS Deployment (NEW)

### Files Added (Non-Intrusive)

All monitoring configs are **separate and optional** - they don't modify your existing deployment:

```
deployment/
├── k8s/prod/
│   ├── monitoring-stack.yaml       # NEW - Complete monitoring stack
│   ├── MONITORING.md               # NEW - Deployment guide
│   └── kustomization.yaml          # UNCHANGED - No modifications
└── terraform/
    ├── monitoring-cleanup.sh       # NEW - Optional cleanup script
    ├── tf-apply.sh                 # UNCHANGED - No modifications
    └── destroy.sh                  # UNCHANGED - No modifications
```

### Why This Approach?

✅ **Non-invasive**: Existing deployment unchanged
✅ **Easy rollback**: Just delete the monitoring namespace
✅ **Toggle on/off**: Enable/disable without affecting main app
✅ **Independent**: Monitoring fails = app keeps running

---

## 🚀 Quick Start Guide

### Enable Monitoring on EKS

```bash
# 1. Ensure kubectl is configured
aws eks update-kubeconfig \
  --name ml-speech-emotion-prod-eks \
  --region us-east-1 \
  --profile ml-ser-deploy

# 2. Deploy monitoring stack
kubectl apply -f deployment/k8s/prod/monitoring-stack.yaml

# 3. Wait for pods to be ready
kubectl get pods -n monitoring -w

# 4. Port-forward to access Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# 5. Open Grafana: http://localhost:3000
# Login: admin / admin
```

### Disable Monitoring

```bash
# Option 1: Complete removal
kubectl delete -f deployment/k8s/prod/monitoring-stack.yaml

# Option 2: Scale to zero (keeps data)
cd deployment/terraform
./monitoring-cleanup.sh --keep
```

---

## 🔍 What Gets Monitored?

### Backend Metrics (Already Instrumented)

Your FastAPI backend already exposes these metrics at `/metrics`:

```promql
# HTTP Metrics
http_requests_total              # Total requests by method, endpoint, status
http_request_duration_seconds    # Request latency histogram

# Application Metrics
prediction_requests_total         # Emotion predictions by type & confidence
audio_processing_duration_seconds # Audio processing time
```

### How Prometheus Finds Your Backend

The backend pods already have the correct annotations:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "9090"
  prometheus.io/path: "/metrics"
```

Prometheus automatically discovers and scrapes these pods.

---

## 📊 Access Patterns

### Local Development
```bash
# Direct access (no port-forwarding needed)
Grafana:    http://localhost:3001
Prometheus: http://localhost:9090
Backend:    http://localhost:8000/metrics
```

### AWS EKS
```bash
# Port-forward required
kubectl port-forward -n monitoring svc/grafana 3000:3000
kubectl port-forward -n monitoring svc/prometheus 9090:9090
kubectl port-forward -n ml-speech-emotion svc/backend 8000:8000

# Then access
Grafana:    http://localhost:3000
Prometheus: http://localhost:9090
Backend:    http://localhost:8000/metrics
```

---

## 🛠️ Terraform & CD Integration

### No Changes Required

Your existing workflows remain unchanged:

```bash
# Terraform apply (as before)
cd deployment/terraform
./tf-apply.sh

# CD deployment (as before)
gh workflow run cd.yml
```

**Monitoring is deployed separately AFTER your app is running.**

### Cleanup Process

```bash
# Main app cleanup (as before)
cd deployment/terraform
./destroy.sh

# Optional: Clean up monitoring first
./monitoring-cleanup.sh
```

---

## 📁 Storage

### Local (Docker Volumes)
```
prometheus_data  # 15-day retention
grafana_data     # Dashboard configs
loki_data        # Log storage
```

### AWS EKS (EBS Volumes)
```
prometheus-pvc   # 20Gi (30-day retention, gp3)
grafana-pvc      # 10Gi (configs, gp3)
loki-pvc         # 20Gi (logs, gp3)
```

**Total EKS Cost**: ~$5-10/month for storage

---

## 🔄 Migration Path

### From Local to EKS

Your local monitoring setup **translates 1:1 to EKS**:

| Local (Docker Compose) | EKS (Kubernetes) |
|---|---|
| `docker-compose --profile monitoring up` | `kubectl apply -f monitoring-stack.yaml` |
| `docker-compose logs prometheus` | `kubectl logs -n monitoring -l app=prometheus` |
| `http://localhost:3001` | `kubectl port-forward svc/grafana 3000:3000` |
| Docker volumes | EBS PersistentVolumes |

---

## 🎯 Sample Queries

### PromQL (Prometheus)

```promql
# Request rate
rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
sum(rate(http_requests_total{status_code=~"5.."}[5m]))
  / sum(rate(http_requests_total[5m])) * 100

# Predictions by emotion
sum(prediction_requests_total) by (emotion)
```

### LogQL (Loki)

```logql
# All logs from backend
{namespace="ml-speech-emotion", app="backend"}

# Error logs only
{namespace="ml-speech-emotion"} |= "error"

# Prediction requests
{namespace="ml-speech-emotion"} |= "prediction"
```

---

## 🔐 Security Notes

### Change Default Passwords

```bash
# Local (docker-compose)
# Edit docker-compose.yml:
# environment:
#   - GF_SECURITY_ADMIN_PASSWORD=YourSecurePassword

# EKS
kubectl create secret generic grafana-secret \
  -n monitoring \
  --from-literal=admin-password='YourSecurePassword' \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl rollout restart deployment/grafana -n monitoring
```

### Don't Expose Publicly

Monitoring dashboards contain sensitive app metrics. Use:
- Port-forwarding for development
- VPN for production access
- Or enable ALB ingress with authentication

---

## 🆘 Troubleshooting

### Prometheus Not Scraping Backend

```bash
# 1. Check Prometheus targets
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Open: http://localhost:9090/targets
# Look for "backend" job - should be UP

# 2. Verify backend metrics endpoint
kubectl port-forward -n ml-speech-emotion svc/backend 8000:8000
curl http://localhost:8000/metrics
# Should return Prometheus-formatted metrics

# 3. Check backend pod annotations
kubectl get pods -n ml-speech-emotion -o yaml | grep -A 3 "annotations:"
```

### Grafana Dashboard Empty

```bash
# 1. Verify Prometheus datasource
# Grafana → Configuration → Data Sources → Prometheus → Test

# 2. Generate traffic to populate metrics
kubectl port-forward -n ml-speech-emotion svc/streamlit 8501:8501
# Use the app to create requests

# 3. Check time range (top-right in Grafana)
# Set to "Last 15 minutes"
```

---

## 📚 Full Documentation

- **EKS Deployment**: `deployment/k8s/prod/MONITORING.md`
- **Local Setup**: `deployment/monitoring/README.md`
- **Backend Metrics**: Already configured in `backend/app/main.py`

---

## ✅ Summary

**What Changed:**
- ✅ 3 new files added (monitoring-stack.yaml, MONITORING.md, monitoring-cleanup.sh)
- ✅ 0 existing files modified
- ✅ Terraform unchanged
- ✅ CD workflow unchanged
- ✅ Main app deployment unchanged

**What You Can Do:**
- ✅ Deploy monitoring anytime with `kubectl apply`
- ✅ Remove monitoring anytime with `kubectl delete`
- ✅ Toggle monitoring on/off without affecting app
- ✅ Keep or discard data when cleaning up

**Cost:**
- Local: Free (uses Docker volumes)
- EKS: ~$5-10/month (EBS storage only)

---

**Last Updated**: 2025-12-01
**Maintained by**: ML Speech Emotion Recognition Team
