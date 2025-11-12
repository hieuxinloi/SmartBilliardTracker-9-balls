# 🚀 SmartBilliardTracker - Production Deployment Guide

Complete guide for deploying SmartBilliardTracker to production environments including cloud platforms (AWS, Azure, GCP) and on-premises servers.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Deployment Options](#deployment-options)
   - [Docker Deployment](#docker-deployment)
   - [AWS Deployment](#aws-deployment)
   - [Azure Deployment](#azure-deployment)
   - [GCP Deployment](#gcp-deployment)
4. [Production Checklist](#production-checklist)
5. [Monitoring & Maintenance](#monitoring--maintenance)
6. [Scaling Strategies](#scaling-strategies)
7. [Security Best Practices](#security-best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
- Docker 20.10+ and Docker Compose 1.29+
- Git 2.30+ with Git LFS
- Domain name (for HTTPS)
- SSL certificate (Let's Encrypt recommended)
- Cloud account (AWS/Azure/GCP) or on-premises server

### System Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 50 GB SSD
- Network: 100 Mbps

**Recommended:**
- CPU: 8+ cores (with GPU support)
- RAM: 16+ GB
- Storage: 200+ GB NVMe SSD
- Network: 1 Gbps
- GPU: NVIDIA GPU with 8+ GB VRAM (for faster processing)

---

## Environment Configuration

### 1. Create Production Environment File

Create `.env.production` in project root:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
GAME_API_PORT=8001

# CORS Settings
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOW_CREDENTIALS=true

# Database (if using)
DATABASE_URL=postgresql://user:password@db:5432/billiards
REDIS_URL=redis://redis:6379/0

# Storage
UPLOAD_DIR=/app/uploads
OUTPUT_DIR=/app/outputs
MODEL_DIR=/app/models
MAX_UPLOAD_SIZE=500000000  # 500MB

# AI Model Settings
MODEL_PATH=/app/models/yolov8n-ball-v.1.0.0.pt
CONFIDENCE_THRESHOLD=0.1
IOU_THRESHOLD=0.45

# Security
SECRET_KEY=your-secret-key-here-change-this
JWT_SECRET=your-jwt-secret-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Feature Flags
ENABLE_CAMERA=true
ENABLE_GPU=true
MAX_CONCURRENT_SESSIONS=10

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 2. Frontend Environment

Create `.env.production` in `frontend/`:

```bash
REACT_APP_API_URL=https://api.yourdomain.com
REACT_APP_WS_URL=wss://api.yourdomain.com/ws
REACT_APP_GAME_API_URL=https://api.yourdomain.com:8001
REACT_APP_GAME_WS_URL=wss://api.yourdomain.com:8001/ws/game
```

---

## Deployment Options

## Docker Deployment

### Standard Docker Compose

**Production docker-compose.prod.yml:**

```yaml
version: "3.8"

services:
  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./frontend/build:/usr/share/nginx/html:ro
    depends_on:
      - backend
      - backend-game
    networks:
      - billiard-network
    restart: unless-stopped

  # Video processing API
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
      args:
        - BUILD_ENV=production
    environment:
      - PYTHONUNBUFFERED=1
      - API_PORT=8000
    env_file:
      - .env.production
    volumes:
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
      - ./models:/app/models
      - ./logs:/app/logs
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
    networks:
      - billiard-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G

  # Game system API
  backend-game:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      - PYTHONUNBUFFERED=1
      - API_PORT=8001
    env_file:
      - .env.production
    volumes:
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
      - ./models:/app/models
      - ./match_history:/app/match_history
      - ./logs:/app/logs
    command: python backend/main_game.py
    networks:
      - billiard-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G

  # Redis for caching (optional)
  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    networks:
      - billiard-network
    restart: unless-stopped

  # PostgreSQL (optional, for user management)
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=billiards
      - POSTGRES_USER=billiards_user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - billiard-network
    restart: unless-stopped

networks:
  billiard-network:
    driver: bridge

volumes:
  postgres-data:
  redis-data:
  uploads:
  outputs:
  match_history:
```

### Nginx Production Configuration

**nginx.prod.conf:**

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend_api {
        server backend:8000;
    }

    upstream game_api {
        server backend-game:8001;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=2r/m;

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        
        # Redirect to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # Frontend
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
            
            # Cache static assets
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }

        # Video processing API
        location /api/ {
            limit_req zone=api_limit burst=20;
            
            proxy_pass http://backend_api;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
        }

        # WebSocket for video processing
        location /ws {
            proxy_pass http://backend_api;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 3600s;
        }

        # Game system API
        location /api/game/ {
            limit_req zone=api_limit burst=20;
            
            proxy_pass http://game_api;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # WebSocket for game system
        location /ws/game {
            proxy_pass http://game_api;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 3600s;
        }

        # File uploads
        location /api/sessions/upload {
            limit_req zone=upload_limit burst=2;
            
            client_max_body_size 500M;
            proxy_pass http://backend_api;
            proxy_request_buffering off;
            proxy_http_version 1.1;
        }

        # Health check
        location /health {
            access_log off;
            proxy_pass http://backend_api;
        }
    }
}
```

### Deploy with Docker

```bash
# 1. Clone repository
git clone https://github.com/yourusername/SmartBilliardTracker-9-balls.git
cd SmartBilliardTracker-9-balls

# 2. Setup Git LFS
git lfs install
git lfs pull

# 3. Configure environment
cp .env.example .env.production
nano .env.production  # Edit with your settings

# 4. Build frontend
cd frontend
npm install
npm run build
cd ..

# 5. Deploy
docker-compose -f docker-compose.prod.yml up -d --build

# 6. Check status
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

---

## AWS Deployment

### Option 1: ECS (Elastic Container Service)

**Infrastructure:**
- Application Load Balancer (ALB)
- ECS Fargate or EC2 cluster
- S3 for file storage
- CloudFront for CDN
- RDS PostgreSQL (optional)
- ElastiCache Redis (optional)

**Steps:**

```bash
# 1. Install AWS CLI
pip install awscli
aws configure

# 2. Create ECR repositories
aws ecr create-repository --repository-name billiards-backend
aws ecr create-repository --repository-name billiards-frontend

# 3. Build and push images
$(aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com)

docker build -t billiards-backend -f Dockerfile.backend .
docker tag billiards-backend:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/billiards-backend:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/billiards-backend:latest

# 4. Create ECS task definition (task-definition.json)
{
  "family": "billiards-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "8192",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/billiards-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "PYTHONUNBUFFERED", "value": "1"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/billiards",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "backend"
        }
      }
    }
  ]
}

# 5. Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 6. Create ECS service
aws ecs create-service \
  --cluster billiards-cluster \
  --service-name billiards-backend \
  --task-definition billiards-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

### Option 2: EC2 with Auto Scaling

```bash
# User data script for EC2 launch
#!/bin/bash
yum update -y
yum install -y docker git

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Start Docker
service docker start
usermod -a -G docker ec2-user

# Clone and deploy
cd /home/ec2-user
git clone https://github.com/yourusername/SmartBilliardTracker-9-balls.git
cd SmartBilliardTracker-9-balls
git lfs install
git lfs pull

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

---

## Azure Deployment

### Option 1: Azure Container Instances (ACI)

```bash
# 1. Login to Azure
az login

# 2. Create resource group
az group create --name billiards-rg --location eastus

# 3. Create Azure Container Registry
az acr create --resource-group billiards-rg --name billiardscr --sku Basic

# 4. Build and push images
az acr build --registry billiardscr --image billiards-backend:latest -f Dockerfile.backend .

# 5. Create container instance
az container create \
  --resource-group billiards-rg \
  --name billiards-backend \
  --image billiardscr.azurecr.io/billiards-backend:latest \
  --dns-name-label billiards-api \
  --ports 8000 8001 \
  --cpu 4 \
  --memory 8 \
  --environment-variables API_PORT=8000
```

### Option 2: Azure App Service

```bash
# Create App Service plan
az appservice plan create \
  --name billiards-plan \
  --resource-group billiards-rg \
  --is-linux \
  --sku P1V3

# Create web app
az webapp create \
  --resource-group billiards-rg \
  --plan billiards-plan \
  --name billiards-api \
  --deployment-container-image-name billiardscr.azurecr.io/billiards-backend:latest

# Configure
az webapp config appsettings set \
  --resource-group billiards-rg \
  --name billiards-api \
  --settings PYTHONUNBUFFERED=1 API_PORT=8000
```

---

## GCP Deployment

### Option 1: Cloud Run

```bash
# 1. Enable APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# 2. Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/billiards-backend

# 3. Deploy to Cloud Run
gcloud run deploy billiards-backend \
  --image gcr.io/PROJECT_ID/billiards-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 8Gi \
  --cpu 4 \
  --timeout 300 \
  --port 8000
```

### Option 2: GKE (Kubernetes Engine)

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: billiards-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: billiards-backend
  template:
    metadata:
      labels:
        app: billiards-backend
    spec:
      containers:
      - name: backend
        image: gcr.io/PROJECT_ID/billiards-backend:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        env:
        - name: PYTHONUNBUFFERED
          value: "1"
---
apiVersion: v1
kind: Service
metadata:
  name: billiards-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: billiards-backend
```

```bash
# Deploy to GKE
kubectl apply -f deployment.yaml
kubectl get services
```

---

## Production Checklist

### Pre-Deployment

- [ ] Update all environment variables
- [ ] Generate strong SECRET_KEY and JWT_SECRET
- [ ] Configure CORS origins
- [ ] Set up SSL certificates
- [ ] Configure firewall rules
- [ ] Set up backup strategy
- [ ] Configure monitoring and alerting
- [ ] Load test the application
- [ ] Document rollback procedure

### Security

- [ ] Enable HTTPS only
- [ ] Configure rate limiting
- [ ] Set up WAF (Web Application Firewall)
- [ ] Enable DDoS protection
- [ ] Implement authentication/authorization
- [ ] Secure database connections
- [ ] Encrypt sensitive data
- [ ] Regular security audits
- [ ] Keep dependencies updated

### Performance

- [ ] Enable caching (Redis)
- [ ] Configure CDN for static assets
- [ ] Optimize database queries
- [ ] Enable GPU acceleration if available
- [ ] Set up auto-scaling
- [ ] Monitor resource usage
- [ ] Optimize video processing

---

## Monitoring & Maintenance

### Health Checks

```bash
# API health
curl https://api.yourdomain.com/health

# Docker health
docker ps
docker stats
```

### Logging

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f backend-game

# Log aggregation (ELK Stack)
# Add to docker-compose.prod.yml
elasticsearch:
  image: elasticsearch:8.8.0
  ...
kibana:
  image: kibana:8.8.0
  ...
logstash:
  image: logstash:8.8.0
  ...
```

### Metrics

Use Prometheus + Grafana:

```yaml
# Add to docker-compose.prod.yml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  ports:
    - "3001:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## Scaling Strategies

### Horizontal Scaling

```bash
# Scale backend instances
docker-compose -f docker-compose.prod.yml up -d --scale backend=3 --scale backend-game=2
```

### Vertical Scaling

Update resource limits in docker-compose.prod.yml:

```yaml
deploy:
  resources:
    limits:
      cpus: '8'
      memory: 16G
```

### Load Balancing

Use Nginx, HAProxy, or cloud load balancers (ALB, Azure LB, GCP LB)

---

## Security Best Practices

1. **Use secrets management**: AWS Secrets Manager, Azure Key Vault, GCP Secret Manager
2. **Enable firewall**: Only allow necessary ports
3. **Regular updates**: Keep all dependencies current
4. **Backup strategy**: Daily automated backups
5. **Access control**: Implement RBAC
6. **Audit logging**: Track all API access
7. **Input validation**: Sanitize all user inputs
8. **Rate limiting**: Prevent API abuse

---

## Troubleshooting

### Common Issues

**1. Out of memory**
```bash
# Check memory usage
docker stats

# Increase memory limit
docker-compose -f docker-compose.prod.yml up -d backend --scale backend=1 --memory=12g
```

**2. Slow processing**
```bash
# Enable GPU
# Add to docker-compose.prod.yml under backend service:
runtime: nvidia
environment:
  - NVIDIA_VISIBLE_DEVICES=all
```

**3. WebSocket connection issues**
```nginx
# In nginx.conf, ensure:
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_read_timeout 3600s;
```

**4. File upload fails**
```nginx
# Increase client_max_body_size in nginx.conf:
client_max_body_size 500M;
```

---

## Support

For deployment assistance:
- GitHub Issues: https://github.com/yourusername/SmartBilliardTracker-9-balls/issues
- Documentation: See GAME_SYSTEM_README.md
- Email: support@yourdomain.com

---

**Last Updated**: 2025-11-12
**Version**: 2.0.0
