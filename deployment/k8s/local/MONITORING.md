# Monitoring Stack for ML Speech Emotion Recognition

This directory contains a complete monitoring solution for the ML Speech Emotion Recognition application running on Kubernetes (Minikube).

## 📊 Overview

The monitoring stack includes:
- **Prometheus** - Metrics collection and storage
- **Grafana** - Visualization and dashboards
- **Loki** - Log aggregation
- **Promtail** - Log collection agent

## 🎯 Pre-configured Dashboards

Three production-ready Grafana dashboards are automatically provisioned:

### 1. Infra Monitor (Dashboard ID: 15661)
**Purpose**: Kubernetes cluster health and resource monitoring
- **Metrics Tracked**:
  - Node CPU, memory, disk usage
  - Pod resource consumption
  - Kubernetes API server metrics
  - Network bandwidth and I/O
  - Container resource limits and requests
  - Cluster-wide resource allocation
- **Use Cases**: Infrastructure capacity planning, cluster health monitoring

### 2. App Monitor (Dashboard ID: 16110)
**Purpose**: FastAPI backend observability
- **Metrics Tracked**:
  - HTTP request rate and latency (p50, p95, p99)
  - Request duration histograms
  - Error rates and status codes
  - Endpoint-specific performance
  - Active connections
  - Application-level metrics
- **Use Cases**: API performance monitoring, troubleshooting slow endpoints, capacity planning

### 3. Logs Monitor (Dashboard ID: 14055)
**Purpose**: Log aggregation and analysis via Loki and Promtail
- **Metrics Tracked**:
  - Log ingestion rates
  - Loki and Promtail resource usage
  - Stream counts and log volumes
  - Error message detection
  - Log parsing performance
- **Log Sources**:
  - Backend (FastAPI) application logs
  - Streamlit frontend logs
  - Kubernetes system logs
  - Loki and Promtail component logs
- **Use Cases**: Log analysis, error tracking, debugging production issues

## 🚀 Quick Start

### Deploy Monitoring Stack

```bash
# Deploy with monitoring enabled
cd deployment/k8s/local
./deploy-local.sh --with-monitoring

# Or deploy monitoring separately
kubectl apply -f monitoring-stack.yaml
```

### Access Grafana Dashboard

**Option 1: Port Forward (Recommended)**
```bash
kubectl port-forward -n monitoring svc/grafana 3000:3000
```
Then access: http://localhost:3000

**Option 2: NodePort**
```bash
minikube service grafana -n monitoring
```
This will automatically open the browser with the correct URL.

**Default Credentials:**
- Username: `admin`
- Password: `admin`

### Access Prometheus

```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```
Then access: http://localhost:9090

### Access Loki

```bash
kubectl port-forward -n monitoring svc/loki 3100:3100
```
Then access: http://localhost:3100/metrics

## 📁 File Structure

```
deployment/k8s/local/
├── monitoring-stack.yaml          # Complete monitoring stack deployment
├── grafana-dashboards-configmap.yaml  # Dashboard configurations (included in monitoring-stack.yaml)
└── MONITORING.md                  # This file

deployment/monitoring/
├── grafana/
│   ├── dashboards/
│   │   ├── infra-monitor.json     # K8s infrastructure dashboard
│   │   ├── app-monitor.json       # FastAPI backend dashboard
│   │   └── logs-monitor.json      # Loki logs dashboard
│   └── provisioning/
│       ├── dashboards/
│       │   └── dashboard.yml      # Dashboard provisioning config
│       └── datasources/
│           └── loki.yml           # Data source config (Prometheus + Loki)
└── prometheus/
    └── prometheus.yml             # Prometheus scrape configuration
```

## 🔧 Configuration Details

### Prometheus Configuration

**Scrape Intervals:**
- Global: 15s
- Backend: Auto-discovered via Kubernetes service discovery

**Scrape Jobs:**
1. `prometheus` - Self-monitoring
2. `kubernetes-apiservers` - K8s API server metrics
3. `kubernetes-nodes` - Node metrics
4. `kubernetes-cadvisor` - Container metrics
5. `kubernetes-service-endpoints` - Service endpoint metrics
6. `kubernetes-pods` - Pod metrics (auto-discovery)
7. `backend-ml-app` - FastAPI backend (explicit config)

**Storage:**
- Retention: 7 days
- Storage: emptyDir (ephemeral)

### Loki Configuration

**Features:**
- Log retention: 7 days (168 hours)
- Ingestion rate limit: 16MB/s
- Max streams per user: 10,000
- Query range: 30 days
- Compression enabled

**Storage:**
- Type: Filesystem (local)
- Storage: emptyDir (ephemeral)

### Promtail Configuration

**Deployment:**
- Type: DaemonSet (runs on every node)
- Scrape jobs: kubernetes-pods, ml-backend, ml-streamlit

**Log Pipeline:**
- CRI parser for Kubernetes logs
- JSON parsing for structured logs
- Automatic labeling (namespace, pod, container, app)

### Grafana Configuration

**Datasources:**
1. **Prometheus** (Default)
   - URL: `http://prometheus.monitoring.svc.cluster.local:9090`
   - UID: `DS_PROMETHEUS`
   - Scrape interval: 15s

2. **Loki**
   - URL: `http://loki.monitoring.svc.cluster.local:3100`
   - UID: `DS_LOKI`
   - Max lines: 5000

**Dashboard Provisioning:**
- Auto-loaded from ConfigMap
- Update interval: 10 seconds
- Folder: "ML App Monitoring"
- Allow UI updates: Yes

## 📈 Monitoring Targets

### Backend Application

The FastAPI backend is automatically discovered by Prometheus via:
```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

**Required Metrics Endpoint:**
- The backend must expose metrics at `/metrics` endpoint
- Recommended: Use `prometheus-fastapi-instrumentator` or similar

### Streamlit Application

Logs are collected by Promtail via:
- Label: `service=streamlit`
- Namespace: `ml-speech-emotion`

## 🔍 Troubleshooting

### Dashboards Not Loading

1. **Check ConfigMap:**
```bash
kubectl get configmap grafana-dashboards -n monitoring
```

2. **Verify Dashboard Files:**
```bash
kubectl describe configmap grafana-dashboards -n monitoring | head -50
```

3. **Check Grafana Logs:**
```bash
kubectl logs -n monitoring -l app=grafana --tail=100
```

### No Metrics in Prometheus

1. **Check Prometheus Targets:**
```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```
Visit: http://localhost:9090/targets

2. **Verify Backend Annotations:**
```bash
kubectl get pods -n ml-speech-emotion -o yaml | grep -A5 "annotations:"
```

3. **Check Prometheus Logs:**
```bash
kubectl logs -n monitoring -l app=prometheus --tail=100
```

### No Logs in Loki

1. **Check Promtail Status:**
```bash
kubectl get pods -n monitoring -l app=promtail
kubectl logs -n monitoring -l app=promtail --tail=50
```

2. **Verify Loki is Running:**
```bash
kubectl get pods -n monitoring -l app=loki
kubectl logs -n monitoring -l app=loki --tail=50
```

3. **Test Loki API:**
```bash
kubectl port-forward -n monitoring svc/loki 3100:3100
curl http://localhost:3100/ready
```

### Grafana Performance Issues

**Common Causes:**
1. **Large time ranges**: Reduce query time range (e.g., last 15m instead of 24h)
2. **Too many series**: Reduce number of active panels or increase refresh interval
3. **Resource limits**: Increase Grafana memory/CPU limits in monitoring-stack.yaml

**Optimizations:**
```yaml
# Edit Grafana deployment
resources:
  limits:
    memory: "1Gi"  # Increase from 512Mi
    cpu: "500m"    # Increase from 200m
```

### Dashboard Updates Not Reflecting

**Force Refresh:**
```bash
# Delete and recreate the ConfigMap
kubectl delete configmap grafana-dashboards -n monitoring
kubectl apply -f monitoring-stack.yaml

# Restart Grafana
kubectl rollout restart deployment/grafana -n monitoring
```

## 🧹 Cleanup

### Remove Monitoring Stack Only

```bash
kubectl delete -f monitoring-stack.yaml
```

### Complete Cleanup (Including Application)

```bash
./deploy-local.sh --clean
```

## 📊 Resource Requirements

**Minimum Resources:**
- Prometheus: 512Mi memory, 250m CPU
- Grafana: 256Mi memory, 100m CPU
- Loki: 256Mi memory, 100m CPU
- Promtail: 64Mi memory, 50m CPU per node

**Total**: ~1Gi memory, 500m CPU (single node)

**Recommended for Production:**
- Increase memory limits by 2x
- Add persistent volumes for Prometheus and Loki
- Configure remote storage for long-term retention

## 🔐 Security Considerations

**Current Configuration (Local Development):**
- ✅ RBAC enabled for Prometheus and Promtail
- ✅ Non-root containers for Grafana
- ⚠️  Default admin password (change in production!)
- ⚠️  No TLS/SSL (local only)
- ⚠️  NodePort exposure (convenient for local access)

**Production Recommendations:**
1. Change default Grafana admin password
2. Enable TLS for all services
3. Use Ingress with authentication
4. Implement network policies
5. Use secrets for sensitive configuration
6. Enable audit logging

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [Promtail Configuration](https://grafana.com/docs/loki/latest/clients/promtail/)
- [FastAPI Prometheus Instrumentator](https://github.com/trallnag/prometheus-fastapi-instrumentator)

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Grafana dashboard queries
3. Inspect Kubernetes events: `kubectl get events -n monitoring`
4. Check resource usage: `kubectl top pods -n monitoring`

## 🎯 Next Steps

1. **Customize Dashboards**: Modify dashboard JSON files in `deployment/monitoring/grafana/dashboards/`
2. **Add Alerting**: Configure Prometheus alerting rules
3. **Add More Metrics**: Instrument additional application endpoints
4. **Enable Persistence**: Add PersistentVolumeClaims for production use
5. **Configure Retention**: Adjust retention policies based on requirements
