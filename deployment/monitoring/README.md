# Monitoring Setup - ML Speech Emotion Recognition

This directory contains the monitoring infrastructure for the ML Speech Emotion Recognition application using Prometheus, Grafana, Loki, and Promtail.

## 🚀 Quick Start

### Start Monitoring Stack

```bash
# From project root directory
docker-compose --profile monitoring up -d
```

This starts:
- **Prometheus** - Metrics collection (port 9090)
- **Grafana** - Visualization dashboards (port 3001)
- **Loki** - Log aggregation (port 3100)
- **Promtail** - Log collection agent

### Access Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3001 | `admin` / `admin` |
| **Prometheus** | http://localhost:9090 | None |
| **Backend API** | http://localhost:8000 | None |
| **Backend Metrics** | http://localhost:8000/metrics | None |

## 📊 Available Metrics

The FastAPI backend exposes the following Prometheus metrics at `/metrics`:

### HTTP Metrics
- **`http_requests_total`** - Total HTTP requests
  - Labels: `method`, `endpoint`, `status_code`

- **`http_request_duration_seconds`** - HTTP request latency
  - Labels: `method`, `endpoint`
  - Type: Histogram

### Application Metrics
- **`prediction_requests_total`** - Total emotion prediction requests
  - Labels: `emotion`, `confidence_level`

- **`audio_processing_duration_seconds`** - Audio processing time
  - Type: Histogram

## 📁 Directory Structure

```
deployment/monitoring/
├── README.md                              # This file
├── prometheus/
│   └── prometheus.yml                     # Prometheus configuration
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── loki.yml                   # Datasource config (Prometheus + Loki)
│   │   └── dashboards/
│   │       └── dashboard.yml              # Dashboard provisioning config
│   └── dashboards/
│       ├── metrics-dashboard.json         # Pre-built metrics dashboard
│       └── log-dashboard.json             # Pre-built logs dashboard
├── loki/
│   └── loki.yml                           # Loki configuration
└── promtail/
    └── promtail.yml                       # Promtail configuration
```

## 📈 Pre-Built Dashboards

Grafana comes with two pre-configured dashboards:

### 1. ML Emotion Recognition - Metrics
**File:** `grafana/dashboards/metrics-dashboard.json`

**Panels:**
- Request Rate (requests/sec) by method and status code
- Request Duration (P50, P95, P99 latencies)
- Prediction Requests by emotion type
- Audio Processing Duration distribution
- Error Rate percentage

### 2. ML Emotion Recognition - Logs
**File:** `grafana/dashboards/log-dashboard.json`

**Panels:**
- Real-time log stream
- Log level distribution
- Error log analysis
- Application event timeline

## 🔧 Configuration

### Prometheus Scrape Configuration

**File:** `prometheus/prometheus.yml`

```yaml
scrape_configs:
  # FastAPI Backend
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  # Streamlit Frontend
  - job_name: 'streamlit'
    static_configs:
      - targets: ['streamlit:8501']
    metrics_path: '/_stcore/metrics'
    scrape_interval: 30s
```

### Grafana Datasources

**File:** `grafana/provisioning/datasources/loki.yml`

Two datasources are auto-configured:
1. **Prometheus** (default) - `http://prometheus:9090`
2. **Loki** - `http://loki:3100`

## 🎯 Common Operations

### View Metrics in Prometheus

1. Open http://localhost:9090/graph
2. Try these queries:

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

### View Dashboards in Grafana

1. Open http://localhost:3001
2. Login with `admin` / `admin`
3. Navigate to **Dashboards → Browse**
4. Select:
   - "ML Emotion Recognition - Metrics"
   - "ML Emotion Recognition - Logs"

### Import Additional Community Dashboards

1. In Grafana, click **Dashboards → Import**
2. Enter dashboard ID and click "Load"
3. Select Prometheus datasource
4. Click "Import"

**Recommended Dashboards:**
- **16110** - FastAPI Observability
- **3662** - Prometheus 2.0 Stats
- **1860** - Node Exporter Full

### Generate Test Traffic

To see metrics populate in dashboards:

```bash
# Health check requests
for i in {1..100}; do curl http://localhost:8000/health; done

# View API docs (counts as request)
curl http://localhost:8000/docs

# Check metrics endpoint
curl http://localhost:8000/metrics
```

## 🛠️ Troubleshooting

### Prometheus Not Scraping Backend

1. Check Prometheus targets: http://localhost:9090/targets
2. Verify backend is running: `docker-compose ps backend`
3. Test metrics endpoint: `curl http://localhost:8000/metrics`
4. Check Prometheus logs: `docker-compose logs prometheus`

### Grafana Dashboards Not Showing Data

1. Verify Prometheus datasource is connected:
   - Grafana → Configuration → Data Sources → Prometheus
   - Click "Test" button
2. Check time range in dashboard (top-right corner)
3. Generate some traffic to the backend
4. Verify Prometheus is collecting metrics: http://localhost:9090/graph

### No Logs in Grafana

1. Check Loki is running: `docker-compose ps loki`
2. Check Promtail is running: `docker-compose ps promtail`
3. Verify Loki datasource: Grafana → Configuration → Data Sources → Loki
4. Check Promtail logs: `docker-compose logs promtail`

### Grafana Can't Connect to Prometheus

Ensure all services are on the same Docker network:

```bash
# Check networks
docker network ls

# Inspect the network
docker network inspect ml-speech-emotion-recognition_ml-emotion-network
```

## 🔄 Stop/Restart Monitoring

### Stop Monitoring Stack

```bash
# Stop only monitoring services
docker-compose stop prometheus grafana loki promtail

# Or remove monitoring services (preserves data in volumes)
docker-compose down prometheus grafana loki promtail
```

### Restart Monitoring

```bash
# Restart all monitoring services
docker-compose restart prometheus grafana loki promtail

# Or start if stopped
docker-compose --profile monitoring up -d
```

### Reset Monitoring Data

⚠️ **Warning:** This will delete all historical metrics and logs!

```bash
# Stop services
docker-compose down

# Remove volumes
docker volume rm ml-speech-emotion-recognition_prometheus_data
docker volume rm ml-speech-emotion-recognition_grafana_data
docker volume rm ml-speech-emotion-recognition_loki_data

# Restart
docker-compose --profile monitoring up -d
```

## 📊 Metrics Retention

- **Prometheus:** Default 15 days retention
- **Loki:** Configured retention period (check `loki/loki.yml`)
- **Grafana:** Persistent dashboards and settings

## 🔐 Security Notes

- Default Grafana credentials are `admin`/`admin` - change on first login!
- Monitoring ports are exposed only on localhost by default
- For production: Configure authentication, HTTPS, and access controls

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Gallery](https://grafana.com/grafana/dashboards/)

## 🆘 Need Help?

If you encounter issues:

1. Check service logs: `docker-compose logs [service-name]`
2. Verify all services are running: `docker-compose ps`
3. Test connectivity between services
4. Review this README for troubleshooting steps

---

**Last Updated:** 2025-12-01
**Maintained by:** ML Speech Emotion Recognition Team
