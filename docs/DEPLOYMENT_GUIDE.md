# MEMANTO Production Deployment Guide

## 🚀 Deployment Overview

MEMANTO is production-ready with enterprise-grade security, observability, and scalability features. This guide covers deployment options and operational considerations.

## 📋 Prerequisites

### System Requirements
- **Python**: 3.8+ 
- **Memory**: 2GB+ RAM recommended
- **CPU**: 2+ cores for production load
- **Storage**: 1GB+ for application and logs
- **Network**: HTTPS endpoint for Moorcheh API access

### Dependencies
- **Moorcheh API Key**: Valid API key with appropriate quotas
- **FastAPI**: Web framework and ASGI server
- **Pydantic**: Data validation and serialization
- **httpx**: HTTP client for Moorcheh SDK integration

## 🔧 Configuration

### Environment Variables
```bash
# Required
MOORCHEH_API_KEY=your_moorcheh_api_key_here

# Optional
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
ALLOWED_ORIGINS=*                 # CORS origins (comma-separated)
MAX_MEMORY_SIZE=1048576          # Max memory text size (bytes)
RATE_LIMIT_WRITES=60             # Writes per minute per tenant
RATE_LIMIT_READS=120             # Reads per minute per tenant
RATE_LIMIT_ANSWERS=30            # Answer generations per minute
```

### Configuration File (.env)
```bash
# Copy example configuration
cp .env.example .env

# Edit with your settings
MOORCHEH_API_KEY=your_actual_api_key
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

## 🐳 Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY *.py ./

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Commands
```bash
# Build image
docker build -t memanto:latest .

# Run container
docker run -d \
  --name memanto \
  -p 8000:8000 \
  -e MOORCHEH_API_KEY=your_key \
  -e LOG_LEVEL=INFO \
  --restart unless-stopped \
  memanto:latest

# Check health
curl http://localhost:8000/health
```

### Docker Compose
```yaml
version: '3.8'
services:
  memanto:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MOORCHEH_API_KEY=${MOORCHEH_API_KEY}
      - LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## ☸️ Kubernetes Deployment

### Deployment Manifest
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memanto
  labels:
    app: memanto
spec:
  replicas: 3
  selector:
    matchLabels:
      app: memanto
  template:
    metadata:
      labels:
        app: memanto
    spec:
      containers:
      - name: memanto
        image: memanto:latest
        ports:
        - containerPort: 8000
        env:
        - name: MOORCHEH_API_KEY
          valueFrom:
            secretKeyRef:
              name: memanto-secrets
              key: moorcheh-api-key
        - name: LOG_LEVEL
          value: "INFO"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: memanto-service
spec:
  selector:
    app: memanto
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: v1
kind: Secret
metadata:
  name: memanto-secrets
type: Opaque
data:
  moorcheh-api-key: <base64-encoded-api-key>
```

### Ingress Configuration
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: memanto-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - memanto.yourdomain.com
    secretName: memanto-tls
  rules:
  - host: memanto.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: memanto-service
            port:
              number: 80
```

## ☁️ Cloud Platform Deployment

### AWS ECS
```json
{
  "family": "memanto",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "memanto",
      "image": "your-account.dkr.ecr.region.amazonaws.com/memanto:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "MOORCHEH_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:memanto/moorcheh-api-key"
        }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/memanto",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Google Cloud Run
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: memanto
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
    spec:
      containerConcurrency: 100
      containers:
      - image: gcr.io/your-project/memanto:latest
        ports:
        - containerPort: 8000
        env:
        - name: MOORCHEH_API_KEY
          valueFrom:
            secretKeyRef:
              name: memanto-secrets
              key: moorcheh-api-key
        - name: LOG_LEVEL
          value: INFO
        resources:
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
```

## 📊 Monitoring & Observability

### Health Checks
```bash
# Basic health check
curl -f http://localhost:8000/health

# Detailed system info
curl http://localhost:8000/

# API documentation
curl http://localhost:8000/docs
```

### Logging Configuration
```python
# Structured JSON logging enabled by default
# Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
# Automatic request ID and trace ID generation
# Memory operation logging with redacted content
```

### Metrics Collection
```python
# Built-in metrics (if Prometheus enabled):
# - HTTP request duration and count
# - Memory operation counters
# - Moorcheh SDK call metrics
# - Error rate tracking
```

### Alerting Recommendations
```yaml
# Suggested alerts:
- name: MEMANTO High Error Rate
  condition: error_rate > 5%
  duration: 5m

- name: MEMANTO High Latency
  condition: p95_latency > 500ms
  duration: 2m

- name: MEMANTO Service Down
  condition: health_check_failed
  duration: 1m
```

## 🔒 Security Considerations

### Network Security
- **HTTPS Only**: Always use HTTPS in production
- **Firewall Rules**: Restrict access to necessary ports only
- **VPC/Network Isolation**: Deploy in private networks when possible

### Authentication
```python
# Bearer token authentication required for all endpoints
# Tenant isolation enforced at namespace level
# API key validation on startup
```

### Secrets Management
```bash
# Never commit API keys to version control
# Use environment variables or secret management systems
# Rotate API keys regularly
# Monitor for unauthorized access
```

## 📈 Performance Tuning

### Scaling Guidelines
```yaml
# Horizontal scaling recommendations:
CPU_THRESHOLD: 70%
MEMORY_THRESHOLD: 80%
MIN_REPLICAS: 2
MAX_REPLICAS: 10

# Vertical scaling:
MEMORY_REQUEST: 512Mi
MEMORY_LIMIT: 1Gi
CPU_REQUEST: 250m
CPU_LIMIT: 500m
```

### Rate Limiting
```python
# Default rate limits (per tenant):
WRITES_PER_MINUTE: 60
READS_PER_MINUTE: 120
ANSWERS_PER_MINUTE: 30

# Adjust based on usage patterns and Moorcheh quotas
```

## 🔄 CI/CD Pipeline

### GitHub Actions Example
```yaml
name: Deploy MEMANTO
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run tests
      run: |
        pytest tests/
        
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to production
      run: |
        docker build -t memanto:${{ github.sha }} .
        docker push your-registry/memanto:${{ github.sha }}
        kubectl set image deployment/memanto memanto=your-registry/memanto:${{ github.sha }}
```

## 🚨 Troubleshooting

### Common Issues
```bash
# API key validation failure
ERROR: "Invalid Moorcheh API key"
SOLUTION: Check MOORCHEH_API_KEY environment variable

# High memory usage
ERROR: Memory consumption growing
SOLUTION: Check for memory leaks, restart service

# Rate limit exceeded
ERROR: "Rate limit exceeded"
SOLUTION: Adjust rate limits or implement backoff
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with debug output
python app/main.py
```

## 📞 Support & Maintenance

### Regular Maintenance
- **Log Rotation**: Configure log rotation to prevent disk space issues
- **Health Monitoring**: Set up automated health checks and alerting
- **Security Updates**: Regular dependency updates and security patches
- **Performance Review**: Monthly performance and usage analysis

### Backup Strategy
- **Configuration Backup**: Version control all configuration files
- **Memory Data**: Moorcheh handles data persistence
- **Audit Logs**: Backup audit logs for compliance

---

**Deployment Status**: ✅ Production Ready  
**Last Updated**: January 2026  
**Project Team**: Dr. Majid Fekri, CTO and co-founder of Moorcheh.ai  
**Support**: Enterprise deployment support available