# 🚀 Complete Deployment Guide: Harmonized Enterprise Ecosystem

**Version**: 1.0
**Date**: December 29, 2025
**Status**: Production Ready

---

## 📋 Prerequisites

### Required Tools
```bash
# Install core dependencies
sudo apt update
sudo apt install -y git docker docker-compose python3.11 node npm

# Install cloud CLI tools
# AWS
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Verify installations
git --version
docker --version
python3 --version
node --version
aws --version
```

### API Keys & Credentials
Create a `.env` file with:
```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Polygon/Blockchain
POLYGON_RPC_URL=https://polygon-rpc.com
PRIVATE_KEY=0x...

# AWS (for quantum computing)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Database
POSTGRES_USER=admin
POSTGRES_PASSWORD=...
POSTGRES_DB=nwu_protocol

# Redis
REDIS_URL=redis://localhost:6379

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672
```

---

## 🎯 Deployment Strategy

### Option 1: Full Stack Deployment (Recommended)
Deploy all 89 systems with one command.

### Option 2: Modular Deployment
Deploy individual tiers based on your needs.

### Option 3: Development Environment
Local setup for testing and development.

---

## 🌐 Full Stack Deployment

### Step 1: Clone Master Hub
```bash
git clone https://github.com/Garrettc123/systems-master-hub.git
cd systems-master-hub
```

### Step 2: Initialize AUTOHELIX (Core Orchestrator)
```bash
# Clone quantum compute engine
git clone https://github.com/Garrettc123/autohelix.git
cd autohelix

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your AWS Braket credentials

# Deploy
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Verify
curl http://localhost:8000/
# Response: {"status": "operational"}
```

### Step 3: Deploy NWU Protocol (Blockchain Layer)
```bash
# Clone protocol
git clone https://github.com/Garrettc123/nwu-protocol.git
cd nwu-protocol

# Configure environment
cp .env.example .env
# Add OpenAI, Polygon keys

# Deploy via Docker (8 microservices)
docker-compose up -d

# Verify services
docker-compose ps
# All 8 services should show "Up"

# Access endpoints
# Frontend: http://localhost:3000
# API: http://localhost:8000/docs
# RabbitMQ: http://localhost:15672 (guest/guest)
```

### Step 4: Deploy Enterprise Platform (Dashboard)
```bash
# Clone platform
git clone https://github.com/Garrettc123/enterprise-unified-platform.git
cd enterprise-unified-platform/frontend

# Install dependencies
npm install

# Development
npm run dev

# Production build
npm run build
npm start

# Access dashboard
# http://localhost:3000
```

### Step 5: Deploy APEX AI OS (Orchestration)
```bash
# Clone APEX
git clone https://github.com/Garrettc123/APEX-Universal-AI-Operating-System.git
cd APEX-Universal-AI-Operating-System

# Install & deploy
npm install
npm run build
npm start

# Access at http://localhost:3000
```

---

## 🔧 Modular Deployment

### Tier 1: Quantum Intelligence Only
```bash
# Just AUTOHELIX for quantum optimization
cd autohelix
pip install -r requirements.txt
python -m uvicorn src.api.main:app --reload

# Test quantum optimization
curl -X POST http://localhost:8000/optimize/recovery \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-001",
    "services": {"db": 5, "api": 2, "web": 1}
  }'
```

### Tier 2: Blockchain Verification Only
```bash
# Just NWU Protocol
cd nwu-protocol
docker-compose up -d postgres redis ipfs backend

# Minimal stack without frontend
```

### Tier 3: Enterprise Applications Only
```bash
# Deploy dashboards without quantum/blockchain
cd enterprise-unified-platform
npm install && npm run dev
```

---

## 🐳 Docker Compose Master Stack

Create `docker-compose.master.yml`:

```yaml
version: '3.9'

services:
  # Quantum Layer
  autohelix:
    image: garrettc123/autohelix:latest
    ports:
      - "8001:8000"
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    networks:
      - harmonized-net

  # Blockchain Layer
  nwu-backend:
    image: garrettc123/nwu-protocol:latest
    ports:
      - "8002:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - POLYGON_RPC_URL=${POLYGON_RPC_URL}
    depends_on:
      - postgres
      - redis
      - ipfs
    networks:
      - harmonized-net

  # Enterprise Dashboard
  enterprise-platform:
    image: garrettc123/enterprise-platform:latest
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://nwu-backend:8000
    networks:
      - harmonized-net

  # Infrastructure
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: harmonized_db
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - harmonized-net

  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"
    networks:
      - harmonized-net

  ipfs:
    image: ipfs/kubo:latest
    ports:
      - "4001:4001"
      - "5001:5001"
      - "8080:8080"
    volumes:
      - ipfs-data:/data/ipfs
    networks:
      - harmonized-net

  kafka:
    image: confluentinc/cp-kafka:latest
    ports:
      - "9092:9092"
    environment:
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
    depends_on:
      - zookeeper
    networks:
      - harmonized-net

  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    networks:
      - harmonized-net

volumes:
  postgres-data:
  ipfs-data:

networks:
  harmonized-net:
    driver: bridge
```

**Deploy entire stack**:
```bash
docker-compose -f docker-compose.master.yml up -d
```

---

## ☁️ Cloud Deployment

### AWS Deployment
```bash
# Configure AWS
aws configure

# Deploy to ECS
aws ecs create-cluster --cluster-name harmonized-ecosystem

# Deploy task definitions
aws ecs register-task-definition --cli-input-json file://task-definitions/autohelix.json
aws ecs register-task-definition --cli-input-json file://task-definitions/nwu-protocol.json

# Create services
aws ecs create-service \
  --cluster harmonized-ecosystem \
  --service-name autohelix \
  --task-definition autohelix:1 \
  --desired-count 2
```

### Kubernetes Deployment
```bash
# Apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/autohelix/
kubectl apply -f k8s/nwu-protocol/
kubectl apply -f k8s/enterprise-platform/

# Verify deployments
kubectl get pods -n harmonized-ecosystem
```

---

## 🧪 Testing & Verification

### Health Checks
```bash
# AUTOHELIX
curl http://localhost:8001/

# NWU Protocol
curl http://localhost:8002/health

# Enterprise Dashboard
curl http://localhost:3000/api/health
```

### Integration Tests
```bash
# Test quantum → blockchain → dashboard flow
cd systems-master-hub/tests
python test_integration.py
```

### Load Testing
```bash
# Install k6
sudo apt install k6

# Run load test
k6 run load-tests/full-stack.js
```

---

## 📊 Monitoring

### Prometheus + Grafana
```bash
# Deploy monitoring stack
docker-compose -f monitoring/docker-compose.yml up -d

# Access Grafana
# http://localhost:3001 (admin/admin)

# Import dashboards
# - AUTOHELIX Performance
# - NWU Protocol Metrics
# - Enterprise Platform Analytics
```

### CloudWatch (AWS)
```bash
# Configure CloudWatch agent
aws cloudwatch put-metric-data \
  --namespace HarmonizedEcosystem \
  --metric-name SystemHealth \
  --value 1
```

---

## 🔄 Continuous Deployment

### GitHub Actions Workflow
Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy Harmonized Ecosystem

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy AUTOHELIX
        run: |
          cd autohelix
          docker build -t autohelix:${{ github.sha }} .
          docker push garrettc123/autohelix:${{ github.sha }}
          
      - name: Deploy NWU Protocol
        run: |
          cd nwu-protocol
          docker-compose build
          docker-compose push
          
      - name: Deploy to Production
        run: |
          kubectl set image deployment/autohelix autohelix=garrettc123/autohelix:${{ github.sha }}
```

---

## 🛡️ Security

### SSL/TLS Setup
```bash
# Install Certbot
sudo apt install certbot

# Generate certificates
sudo certbot certonly --standalone -d autohelix.yourcompany.com
sudo certbot certonly --standalone -d nwu.yourcompany.com

# Update nginx configs
```

### Secret Management
```bash
# Use AWS Secrets Manager
aws secretsmanager create-secret \
  --name harmonized-ecosystem/openai-key \
  --secret-string "${OPENAI_API_KEY}"
```

---

## 🆘 Troubleshooting

### Common Issues

**Issue**: Docker containers won't start
```bash
# Check logs
docker-compose logs -f [service-name]

# Restart services
docker-compose restart
```

**Issue**: Quantum optimization fails
```bash
# Verify AWS Braket access
aws braket get-device --device-arn arn:aws:braket:::device/quantum-simulator/amazon/sv1

# Fallback to classical
export AUTOHELIX_MODE=classical
```

**Issue**: Blockchain transactions failing
```bash
# Check Polygon network status
curl https://polygon-rpc.com -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

---

## 📈 Scaling Guide

### Horizontal Scaling
```bash
# Scale AUTOHELIX instances
kubectl scale deployment autohelix --replicas=5

# Scale NWU backend
docker-compose up -d --scale nwu-backend=3
```

### Vertical Scaling
```yaml
# Update resource limits in docker-compose.yml
services:
  autohelix:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

---

## ✅ Post-Deployment Checklist

- [ ] All services healthy and responding
- [ ] Database migrations complete
- [ ] SSL certificates installed
- [ ] Monitoring dashboards configured
- [ ] Backup strategy implemented
- [ ] CI/CD pipeline tested
- [ ] Load testing passed
- [ ] Security audit completed
- [ ] Documentation updated
- [ ] Team trained on operations

---

**Deployment Status**: Ready for Production 🚀
**Support**: Open issue in [systems-master-hub](https://github.com/Garrettc123/systems-master-hub/issues)
