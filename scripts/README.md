# 🛠️ Deployment Scripts

This directory contains management scripts for all three deployment strategies of the ML Speech Emotion Recognition application.

## 📁 Strategy 1: Local Execution Scripts

### `start-local.sh`
Starts all services natively without containers.

**Usage:**
```bash
./scripts/start-local.sh
```

**What it does:**
- Checks dependencies (Python, Poetry, Node.js, npm)
- Starts FastAPI backend on port 8000
- Starts Streamlit app on port 8501
- Waits for services to be ready
- Saves process PIDs for cleanup

### `stop-local.sh`
Stops all locally running services.

**Usage:**
```bash
./scripts/stop-local.sh
```

**What it does:**
- Stops services using saved PIDs or by port/process name
- Forces cleanup if needed
- Removes PID files
- Cleans up temporary files

### `check-local.sh`
Checks the status of local services.

**Usage:**
```bash
./scripts/check-local.sh
```

**What it shows:**
- Dependency versions
- Service status by port
- Process status
- API endpoint health checks
- System resource usage
- Overall deployment health

## 🐳 Strategy 2: Docker Execution Scripts

### `docker-compose-manage.sh`
Manages Docker Compose deployment.

**Usage:**
```bash
./scripts/docker-compose-manage.sh {start|stop|restart|status|logs|clean}
```

**Commands:**
- `start` - Build and start all services
- `stop` - Stop all services
- `restart` - Restart all services
- `status` - Show container and resource status
- `logs [service]` - Show logs (all services or specific)
- `clean [--volumes]` - Clean up containers and images

**Examples:**
```bash
./scripts/docker-compose-manage.sh start
./scripts/docker-compose-manage.sh logs backend
./scripts/docker-compose-manage.sh clean --volumes
```

## ☸️ Strategy 3: Kubernetes Scripts

### `deployment/k8s/deploy.sh`
Manages Kubernetes deployments.

**Usage:**
```bash
cd deployment/k8s
./deploy.sh {local|prod} {deploy|delete|status}
```

**Commands:**
- `local deploy` - Deploy to local Kubernetes (Minikube/Docker Desktop)
- `local delete` - Remove local deployment
- `local status` - Show local deployment status
- `prod deploy` - Deploy to production Kubernetes
- `prod delete` - Remove production deployment
- `prod status` - Show production deployment status

## 🔧 Additional Scripts

### `deployment/docker/build.sh`
Builds Docker images for all services.

**Usage:**
```bash
cd deployment/docker
./build.sh {service|all} {tag}
```

**Services:**
- `backend` - FastAPI backend service
- `streamlit` - Streamlit ML interface
- `frontend` - React dashboard (deprecated)
- `all` - Build all services

**Examples:**
```bash
./build.sh all latest
./build.sh backend v1.0.0
```

## 🚀 Quick Start Guide

### For Development (Strategy 1)
```bash
# Start local development
./scripts/start-local.sh

# Check status
./scripts/check-local.sh

# Stop when done
./scripts/stop-local.sh
```

### For Team Collaboration (Strategy 2)
```bash
# Start Docker Compose
./scripts/docker-compose-manage.sh start

# Check status
./scripts/docker-compose-manage.sh status

# View logs
./scripts/docker-compose-manage.sh logs

# Stop when done
./scripts/docker-compose-manage.sh stop
```

### For Production Testing (Strategy 3)
```bash
# Deploy to local Kubernetes
cd deployment/k8s
./deploy.sh local deploy

# Check status
./deploy.sh local status

# Remove when done
./deploy.sh local delete
```

## 🔍 Troubleshooting

### Port Conflicts
- Use `./scripts/check-local.sh` to see what's running
- Use `./scripts/stop-local.sh` to clean up local processes
- Use `./scripts/docker-compose-manage.sh clean` to clean up Docker

### Permission Issues
```bash
chmod +x scripts/*.sh
```

### Docker Issues
- Ensure Docker Desktop is running
- Check Docker daemon status with `docker info`
- Restart Docker Desktop if needed

### Dependencies Missing
- Strategy 1: Check Python, Poetry, Node.js installations
- Strategy 2: Ensure Docker and Docker Compose are installed
- Strategy 3: Verify kubectl and Minikube/Docker Desktop K8s

## 📋 Script Dependencies

| Strategy | Required Software |
|----------|-------------------|
| **Local** | Python 3.11+, Poetry, Node.js, npm |
| **Docker** | Docker, Docker Compose |
| **Kubernetes** | kubectl, Minikube or Docker Desktop K8s |

## 🔄 Script Relationships

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Strategy 1    │    │   Strategy 2     │    │   Strategy 3    │
│  (Local)        │    │  (Docker)        │    │ (Kubernetes)    │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ start-local.sh  │    │docker-compose-   │    │deployment/k8s/  │
│ stop-local.sh   │    │manage.sh         │    │deploy.sh        │
│ check-local.sh  │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                    ┌──────────────────────┐
                    │   Common Scripts      │
                    ├──────────────────────┤
                    │ deployment/docker/    │
                    │ build.sh              │
                    └──────────────────────┘
```

## 🎯 Best Practices

1. **Always check status before starting** - Use the appropriate check script
2. **Stop services properly** - Use the provided stop/clean scripts
3. **Monitor resources** - Check system resources during operation
4. **Use appropriate strategy** - Choose the right deployment method for your use case
5. **Read the logs** - Use log commands to troubleshoot issues

## 📞 Support

For script-related issues:
1. Check the script output for error messages
2. Verify all dependencies are installed
3. Consult the main deployment guide: `docs/DEPLOYMENT_GUIDE.md`
4. Check individual script help with `-h` or `--help` where available

---

**Note**: These scripts are designed to work together with the comprehensive deployment guide. Always refer to the main guide for detailed setup instructions and troubleshooting steps.