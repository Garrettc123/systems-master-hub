# 🚀 Omnibus Deployment System

Run the **entire** enterprise AI ecosystem with a single command.

## Quick Start

```bash
# Run everything
make omni

# Or directly
./run-all-omni.sh
```

## What is Omnibus?

**Omnibus** (Latin for "all") is a comprehensive deployment system that launches the complete $102M+ enterprise AI ecosystem in one orchestrated workflow. It manages:

- 🤖 AI & ML platforms (APEX, MLOps)
- ⛓️ Blockchain systems (AUTOHELIX, Stablecoin, NWU)
- 🏢 Enterprise platforms (Unified Platform, Tree of Life)
- 🌐 Web frontends (Portfolio, Dashboards)
- 📊 Monitoring stack (Prometheus, Grafana, ELK, Jaeger)
- 🗄️ Data infrastructure (PostgreSQL, Redis, Elasticsearch)

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     OMNIBUS ORCHESTRATOR                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  AI/ML Stack │  │  Blockchain  │  │  Enterprise  │    │
│  │              │  │              │  │              │    │
│  │ • APEX OS    │  │ • AUTOHELIX  │  │ • Unified    │    │
│  │ • MLOps      │  │ • Stablecoin │  │ • Tree Life  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Monitoring  │  │     Data     │  │   Frontend   │    │
│  │              │  │              │  │              │    │
│  │ • Prometheus │  │ • PostgreSQL │  │ • Portfolio  │    │
│  │ • Grafana    │  │ • Redis      │  │ • Dashboards │    │
│  │ • ELK        │  │ • Elastic    │  │              │    │
│  │ • Jaeger     │  │              │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Features

### 🎯 Automated Deployment
- **Pre-flight checks** - Validates Docker, disk space, and dependencies
- **Parallel execution** - Builds and starts services concurrently
- **Health monitoring** - Verifies all services are operational
- **Comprehensive logging** - Detailed logs for troubleshooting
- **Core fallback mode** - If private app images/contexts are unavailable, auto-starts monitoring + data backbone services

### 📊 Monitoring & Observability
- **Prometheus** - Metrics collection and alerting
- **Grafana** - Visual dashboards and analytics
- **Elasticsearch + Kibana** - Centralized logging
- **Jaeger** - Distributed tracing

### 🔒 Data Infrastructure
- **PostgreSQL** - Relational database for enterprise data
- **Redis** - In-memory cache and message broker
- **Elasticsearch** - Full-text search and analytics

### 🌐 Network Architecture
- Unified `enterprise-net` network for service communication
- Persistent volumes for data retention
- Health checks for automatic recovery

## Commands

### Main Commands

```bash
# Deploy entire ecosystem
make omni

# Check status of all services
make omni-status

# View logs from all services
make omni-logs

# Stop all services
make omni-stop
```

### Docker Compose Commands

```bash
# Start all services
docker-compose up -d

# View running services
docker-compose ps

# View logs
docker-compose logs -f [service-name]

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

## Access Points

Once deployed, access your services at:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3001 | admin / admin123 |
| **Prometheus** | http://localhost:9090 | - |
| **Kibana** | http://localhost:5601 | - |
| **Jaeger UI** | http://localhost:16686 | - |
| **Elasticsearch** | http://localhost:9200 | - |
| **Tree of Life** | http://localhost:8080 | - |
| **Unified Platform** | http://localhost:8000 | - |
| **Stablecoin API** | http://localhost:3000 | - |
| **Portfolio** | http://localhost:80 | - |
| **PostgreSQL** | localhost:5432 | enterprise / enterprise |
| **Redis** | localhost:6379 | - |

## System Requirements

### Minimum Requirements
- **CPU:** 4 cores
- **RAM:** 8GB
- **Disk:** 20GB free space
- **Docker:** 20.10+
- **Docker Compose:** 2.0+

### Recommended Requirements
- **CPU:** 8+ cores
- **RAM:** 16GB+
- **Disk:** 50GB+ free space
- **Network:** High-speed internet connection

## Folder Structure

```
systems-master-hub/
├── 01-core-infrastructure/       # AUTOHELIX, APEX, NWU
├── 02-ai-ml-platforms/           # MLOps, AI Business
├── 03-protocols-blockchain/      # Stablecoin, Smart Contracts
├── 04-business-automation/       # AI Ops, Process Copilot
├── 05-integration-hubs/          # Tree of Life, Unified Platform
├── 06-deployment-infrastructure/ # Kubernetes, Terraform, Docker
├── 07-api-services/              # FastAPI, GraphQL
├── 08-frontend-applications/     # Portfolio, Dashboards
├── 09-data-infrastructure/       # Pipelines, Databases
├── 10-monitoring-observability/  # Prometheus, Grafana, ELK
├── 11-security-compliance/       # Vault, RBAC, Compliance
├── 12-documentation/             # Architecture, API docs
├── 13-testing-qa/                # Tests, QA automation
├── 14-tools-utilities/           # CLI tools, Scripts
├── 15-projects-experimental/     # Research, Prototypes
├── docker-compose.yml            # Omnibus service definitions
├── run-all-omni.sh              # Main deployment script
├── Makefile                      # Quick command shortcuts
└── logs/                         # Deployment and runtime logs
```

## Logs

All deployment logs are stored in the `./logs` directory:

```bash
logs/
├── omni_deployment_YYYYMMDD_HHMMSS.log
└── deployment_report_YYYYMMDD_HHMMSS.md
```

View the latest deployment report:
```bash
ls -lt logs/*.md | head -1 | xargs cat
```

## Troubleshooting

### Services won't start
If private application images or build contexts are unavailable, omnibus automatically falls back to core infrastructure services (`prometheus`, `grafana`, `elasticsearch`, `kibana`, `jaeger`, `postgres`, `redis`) and continues.

```bash
# Check Docker daemon
docker info

# Check logs for specific service
docker-compose logs [service-name]

# Restart a specific service
docker-compose restart [service-name]

# Rebuild and restart
docker-compose up -d --build [service-name]
```

### Port conflicts
If you get port binding errors:
```bash
# Check what's using the port
lsof -i :[port-number]

# Kill the process or change the port in docker-compose.yml
```

### Out of disk space
```bash
# Clean up old containers and images
docker system prune -a

# Remove unused volumes
docker volume prune
```

### Memory issues
```bash
# Check resource usage
docker stats

# Adjust Elasticsearch memory in docker-compose.yml:
# ES_JAVA_OPTS=-Xms1g -Xmx1g  # Reduce from 2g to 1g
```

## Development

### Adding New Services

1. Define service in `docker-compose.yml`:
```yaml
my-service:
  image: my-image:latest
  build: ./path/to/service
  container_name: my-service
  restart: unless-stopped
  ports:
    - "8080:8080"
  networks:
    - enterprise-net
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

2. Add to monitoring in `prometheus.yml`:
```yaml
- job_name: 'my-service'
  static_configs:
    - targets: ['my-service:8080']
```

3. Test deployment:
```bash
docker-compose up -d my-service
docker-compose logs -f my-service
```

### Customizing the Deployment

Edit `run-all-omni.sh` to customize:
- Pre-flight checks
- Deployment phases
- Health check endpoints
- Logging behavior

## Performance Tuning

### Parallel Build
Adjust parallel jobs in `run-all-omni.sh`:
```bash
PARALLEL_JOBS=20  # Increase for faster builds
```

### Resource Limits
Set resource limits in `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 2G
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Deploy Omnibus
  run: |
    make omni
    make omni-status
```

### Jenkins
```groovy
stage('Deploy Omnibus') {
  steps {
    sh 'make omni'
    sh 'make omni-status'
  }
}
```

## Security Notes

⚠️ **Important**: This setup is for development/testing. For production:

1. Change default passwords in `docker-compose.yml`
2. Enable authentication on all services
3. Use secrets management (Vault, Docker Secrets)
4. Configure SSL/TLS certificates
5. Set up firewall rules
6. Enable security scanning
7. Implement backup strategies

## Support

- 📖 Documentation: `/12-documentation/`
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions
- 📧 Contact: Garrett Carrol (@Garrettc123)

## License

Proprietary - Garrett Carrol Enterprise Systems

## Roadmap

- [ ] Kubernetes deployment manifests
- [ ] Helm charts for easy deployment
- [ ] Auto-scaling configurations
- [ ] Multi-region support
- [ ] Backup and restore automation
- [ ] Performance benchmarking suite
- [ ] Security hardening guide

---

**Built with ❤️ by Garrett Carrol**
Enterprise AI Ecosystem - $102M+ Stack Value
