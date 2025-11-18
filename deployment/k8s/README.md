# Kubernetes Deployment Guide

This directory contains Kubernetes manifests and deployment scripts for the ML Speech Emotion Recognition application, supporting both local Minikube development and production EKS deployment.

## 🏗️ Architecture

### Local (Minikube)
- **Namespace**: `ml-emotion`
- **Ingress**: Local development with multiple hostnames
- **Storage**: EmptyDir volumes
- **Security**: Basic security contexts

### Production (EKS)
- **Namespace**: `ml-emotion-prod`
- **Ingress**: AWS ALB with SSL termination
- **Storage**: Persistent volumes for monitoring
- **Security**: Enhanced with Pod Security Standards, non-root containers
- **Scaling**: Horizontal Pod Autoscalers (HPA)
- **Monitoring**: Prometheus + Grafana stack

## 📁 Directory Structure

```
deployment/k8s/
├── local/                   # Local Minikube manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── backend-deployment.yaml
│   ├── streamlit-deployment.yaml
│   ├── frontend-deployment.yaml
│   └── ingress.yaml
├── prod/                    # Production EKS manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── backend-deployment.yaml
│   ├── streamlit-deployment.yaml
│   ├── frontend-deployment.yaml
│   └── ingress.yaml
├── monitoring.yaml          # Production monitoring stack
├── deploy.sh               # Deployment script
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

#### For Local Development (Minikube)
```bash
# Install and start Minikube
minikube start --cpus=4 --memory=8192

# Enable ingress addon
minikube addons enable ingress

# Verify installation
kubectl cluster-info
```

#### For Production (EKS)
```bash
# Install AWS CLI and configure credentials
aws configure

# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Install AWS Load Balancer Controller
# Follow: https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html
```

### Build Docker Images

Before deploying, build the Docker images:

```bash
# From project root
cd deployment/docker

# Build all images
./build.sh all latest

# Or build specific services
./build.sh backend latest
./build.sh streamlit latest
./build.sh frontend latest

# Load images into Minikube (for local development)
minikube image load ml-emotion-recognition/backend:latest
minikube image load ml-emotion-recognition/streamlit:latest
minikube image load ml-emotion-recognition/frontend:latest
```

### Deploy with Script

The `deploy.sh` script provides an easy way to manage deployments:

```bash
# Deploy to local Minikube
./deploy.sh local deploy

# Deploy to production EKS
./deploy.sh prod deploy

# Check deployment status
./deploy.sh local status

# Delete deployment
./deploy.sh local delete
```

### Manual Deployment

```bash
# Local deployment
kubectl apply -f local/namespace.yaml
kubectl apply -f local/configmap.yaml
kubectl apply -f local/backend-deployment.yaml
kubectl apply -f local/streamlit-deployment.yaml
kubectl apply -f local/frontend-deployment.yaml
kubectl apply -f local/ingress.yaml

# Production deployment
kubectl apply -f prod/namespace.yaml
kubectl apply -f prod/secrets.yaml
kubectl apply -f prod/configmap.yaml
kubectl apply -f prod/backend-deployment.yaml
kubectl apply -f prod/streamlit-deployment.yaml
kubectl apply -f prod/frontend-deployment.yaml
kubectl apply -f prod/ingress.yaml
kubectl apply -f monitoring.yaml
```

## 🔧 Configuration

### Environment-Specific Settings

#### Local Development
- **Debug Mode**: Enabled
- **Image Pull Policy**: Never (uses local images)
- **Replicas**: 1 per service
- **Resources**: Minimal for development
- **Storage**: EmptyDir volumes

#### Production
- **Debug Mode**: Disabled
- **Image Pull Policy**: Always
- **Replicas**: 2-3 per service with HPA
- **Resources**: Production-grade with limits
- **Security**: Enhanced with Pod Security Standards
- **Monitoring**: Full Prometheus + Grafana stack

### Secrets Configuration

For production deployment, update the secrets in `prod/secrets.yaml`:

```yaml
stringData:
  secret-key: "REPLACE_WITH_PRODUCTION_SECRET_KEY"
  sagemaker-endpoint-name: "prod-emotion-recognition-endpoint"
  s3-bucket-name: "ml-emotion-prod-bucket"
  redis-url: "redis://prod-redis:6379"
  # ... other secrets
```

### IAM Roles and Service Accounts

Update the ARNs in `prod/secrets.yaml`:

```yaml
eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ml-emotion-backend-role
```

## 🌐 Access URLs

### Local Development

Add these entries to `/etc/hosts`:

```hosts
127.0.0.1 ml-emotion.local
127.0.0.1 dashboard.ml-emotion.local
127.0.0.1 streamlit.ml-emotion.local
```

Services will be available at:
- **Main App**: http://ml-emotion.local
- **Dashboard**: http://dashboard.ml-emotion.local
- **Streamlit**: http://streamlit.ml-emotion.local
- **Local**: http://localhost

### Production

Update the domain names and SSL certificates in `prod/ingress.yaml`:

```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/...
    external-dns.alpha.kubernetes.io/hostname: "ml-emotion.example.com,app.ml-emotion.example.com"
```

Services will be available at:
- **Main App**: https://ml-emotion.example.com
- **API**: https://api.ml-emotion.example.com
- **Dashboard**: https://dashboard.ml-emotion.example.com
- **Streamlit**: https://app.ml-emotion.example.com

## 📊 Monitoring

### Production Monitoring Stack

The production deployment includes a comprehensive monitoring stack:

```bash
# Check monitoring status
kubectl get pods -n monitoring -l app=prometheus

# Port forward to access Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Access Prometheus at http://localhost:9090
```

### Application Metrics

All services expose Prometheus metrics on port 9090:

- **Backend**: `/metrics` endpoint
- **Custom Metrics**: Request duration, error rates, prediction latency
- **Resource Metrics**: CPU, memory, disk usage

## 🔒 Security Features

### Production Security

- **Pod Security Standards**: Enforced via security contexts
- **Non-root Containers**: All containers run as non-root users
- **Read-only Filesystems**: Where applicable
- **Resource Limits**: CPU and memory limits enforced
- **Network Policies**: Isolate services (optional)
- **RBAC**: Service accounts with limited permissions
- **Secrets Management**: Kubernetes secrets for sensitive data
- **TLS/SSL**: HTTPS with valid certificates

### Security Contexts

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
    - ALL
```

## 📈 Scaling

### Horizontal Pod Autoscaling

Production deployments include HPAs:

```bash
# Check HPA status
kubectl get hpa -n ml-emotion-prod

# Describe HPA
kubectl describe hpa backend-hpa -n ml-emotion-prod
```

### Manual Scaling

```bash
# Scale backend to 5 replicas
kubectl scale deployment backend -n ml-emotion-prod --replicas=5

# Check rollout status
kubectl rollout status deployment/backend -n ml-emotion-prod
```

## 🐛 Troubleshooting

### Common Issues

#### Pods Not Starting
```bash
# Check pod status
kubectl get pods -n ml-emotion-prod

# Describe pod
kubectl describe pod <pod-name> -n ml-emotion-prod

# Check logs
kubectl logs <pod-name> -n ml-emotion-prod -f
```

#### Ingress Not Working
```bash
# Check ingress status
kubectl get ingress -n ml-emotion-prod

# Describe ingress
kubectl describe ingress ml-emotion-ingress -n ml-emotion-prod

# Check ingress controller logs
kubectl logs -n ingress-nginx controller-<pod-name>
```

#### Image Pull Issues
```bash
# Check image pull secrets
kubectl get secret -n ml-emotion-prod

# Verify image exists
docker images | grep ml-emotion-recognition
```

### Health Checks

All services include comprehensive health checks:

- **Liveness Probe**: Detects if service is running
- **Readiness Probe**: Detects if service is ready for traffic
- **Startup Probe**: Handles slow-starting services

### Resource Monitoring

```bash
# Check resource usage
kubectl top pods -n ml-emotion-prod

# Check node resources
kubectl top nodes

# Describe resource quotas
kubectl describe resourcequota -n ml-emotion-prod
```

## 🔄 Updates and Rollbacks

### Rolling Updates

```bash
# Update image version
kubectl set image deployment/backend backend=ml-emotion-recognition/backend:v2 -n ml-emotion-prod

# Check rollout status
kubectl rollout status deployment/backend -n ml-emotion-prod

# View rollout history
kubectl rollout history deployment/backend -n ml-emotion-prod
```

### Rollbacks

```bash
# Rollback to previous version
kubectl rollout undo deployment/backend -n ml-emotion-prod

# Rollback to specific revision
kubectl rollout undo deployment/backend -n ml-emotion-prod --to-revision=2
```

## 🧪 Testing

### Integration Testing

```bash
# Port forward to service
kubectl port-forward -n ml-emotion-prod svc/backend 8000:8000

# Test health endpoint
curl http://localhost:8000/health

# Test API endpoints
curl -X POST http://localhost:8000/api/predict -H "Content-Type: application/json" -d '{"test": "data"}'
```

### Load Testing

```bash
# Install k6 or use your preferred load testing tool

# Example k6 test
k6 run --vus 10 --duration 30s test.js
```

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Minikube Documentation](https://minikube.sigs.k8s.io/docs/)
- [EKS Documentation](https://docs.aws.amazon.com/eks/)
- [AWS Load Balancer Controller](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [Prometheus Monitoring](https://prometheus.io/docs/)

## 🆘 Support

For issues with Kubernetes deployment:

1. Check the troubleshooting section above
2. Review pod logs and events
3. Verify all prerequisites are met
4. Check AWS/EKS console for cluster status
5. Review IAM roles and permissions

For application-specific issues, refer to the main project documentation.