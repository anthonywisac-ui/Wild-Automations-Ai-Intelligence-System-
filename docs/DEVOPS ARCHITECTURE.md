DEVOPS ARCHITECTURE
1. CI/CD Pipeline
1.1 Pipeline Architecture
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CI/CD PIPELINE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    BUILD STAGE                                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │   Code      │  │   Code      │  │   Unit      │  │   Build   │  │  │
│  │  │   Checkout  │──►│   Quality   │──►│   Tests    │──►│   Image   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    TEST STAGE                                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Integration│  │   Security  │  │  Performance│  │   UI      │  │  │
│  │  │   Tests     │──►│   Scan      │──►│   Tests    │──►│   Tests   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    DEPLOY STAGE                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │   Deploy    │  │   Smoke     │  │   Canary    │  │   Rollback│  │  │
│  │  │   Staging   │──►│   Tests     │──►│   Deploy    │──►│   Ready   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    RELEASE STAGE                                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │   Deploy    │  │   Monitor   │  │   Traffic   │  │   Release │  │  │
│  │  │   Production│──►│   Metrics   │──►│   Shift    │──►│   Done   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
1.2 GitHub Actions Workflow
yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run code quality checks
        run: |
          black --check .
          flake8 .
          mypy .
          bandit -r .

      - name: Run unit tests
        run: |
          pytest tests/unit -v --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests

      - name: Build Docker image
        run: |
          docker build -t ${{ env.IMAGE_NAME }}:${{ github.sha }} .
          docker tag ${{ env.IMAGE_NAME }}:${{ github.sha }} ${{ env.IMAGE_NAME }}:latest

      - name: Push to container registry
        run: |
          echo ${{ secrets.GITHUB_TOKEN }} | docker login ${{ env.REGISTRY }} -u ${{ github.actor }} --password-stdin
          docker push ${{ env.IMAGE_NAME }}:${{ github.sha }}
          docker push ${{ env.IMAGE_NAME }}:latest

  security-scan:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Trivy vulnerability scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.IMAGE_NAME }}:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  deploy-staging:
    runs-on: ubuntu-latest
    needs: [build, security-scan]
    if: github.ref == 'refs/heads/develop'
    environment: staging
    steps:
      - name: Deploy to staging
        uses: appleboy/ssh-action@v0.1.10
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /opt/wildautomations
            docker-compose pull
            docker-compose up -d
            docker system prune -f

      - name: Run smoke tests
        run: |
          python -m pytest tests/smoke -v

  deploy-production:
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Deploy to production (Canary)
        uses: appleboy/ssh-action@v0.1.10
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/wildautomations
            # Deploy to canary
            kubectl set image deployment/wildautomations-api-canary \
              wildautomations-api=${{ env.IMAGE_NAME }}:${{ github.sha }}
            # Wait for rollout
            kubectl rollout status deployment/wildautomations-api-canary

      - name: Canary validation
        run: |
          # Run canary validation tests
          python -m pytest tests/canary -v

      - name: Full deployment
        uses: appleboy/ssh-action@v0.1.10
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/wildautomations
            # Deploy to production
            kubectl set image deployment/wildautomations-api \
              wildautomations-api=${{ env.IMAGE_NAME }}:${{ github.sha }}
            # Wait for rollout
            kubectl rollout status deployment/wildautomations-api

      - name: Post-deployment checks
        run: |
          # Run health checks
          curl -f https://api.wildautomations.com/health
          curl -f https://wildautomations.com
2. Infrastructure as Code
2.1 Terraform Configuration
hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.0"
  
  backend "s3" {
    bucket = "wildautomations-terraform-state"
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.9"
    }
  }
}

# Provider configuration
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "WildAutomations"
      ManagedBy   = "Terraform"
    }
  }
}

# VPC Configuration
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "wildautomations-vpc"
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count = 2
  
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  
  tags = {
    Name = "wildautomations-public-${count.index}"
  }
}

# Private Subnets
resource "aws_subnet" "private" {
  count = 2
  
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 2)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false
  
  tags = {
    Name = "wildautomations-private-${count.index}"
  }
}

# EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = "wildautomations-${var.environment}"
  version  = "1.28"
  role_arn = aws_iam_role.eks_cluster.arn
  
  vpc_config {
    subnet_ids              = aws_subnet.private[*].id
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "wildautomations-eks"
  }
}

# EKS Node Group
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "wildautomations-ng"
  node_role_arn   = aws_iam_role.eks_node.arn
  
  subnet_ids = aws_subnet.private[*].id
  
  scaling_config {
    desired_size = 3
    max_size     = 10
    min_size     = 3
  }
  
  instance_types = ["t3.large"]
  
  tags = {
    Name = "wildautomations-node-group"
  }
}

# RDS Database
resource "aws_db_instance" "postgres" {
  identifier     = "wildautomations-db-${var.environment}"
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = "db.t3.large"
  
  allocated_storage     = 100
  storage_encrypted     = true
  storage_type          = "gp3"
  max_allocated_storage = 500
  
  db_name  = "wildautomations"
  username = "wildautomations"
  password = random_password.db_password.result
  
  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  performance_insights_enabled = true
  performance_insights_retention_period = 7
  
  enabled_cloudwatch_logs_exports = ["postgresql"]
  
  tags = {
    Name = "wildautomations-db"
  }
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "wildautomations-redis-${var.environment}"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  
  subnet_group_name = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]
  
  tags = {
    Name = "wildautomations-redis"
  }
}

# S3 Bucket for Artifacts
resource "aws_s3_bucket" "artifacts" {
  bucket = "wildautomations-artifacts-${var.environment}"
  force_destroy = true
  
  tags = {
    Name = "wildautomations-artifacts"
  }
}

# S3 Bucket for Backups
resource "aws_s3_bucket" "backups" {
  bucket = "wildautomations-backups-${var.environment}"
  force_destroy = false
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    enabled = true
    
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    
    expiration {
      days = 365
    }
  }
  
  tags = {
    Name = "wildautomations-backups"
  }
}

# Outputs
output "eks_cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

output "db_endpoint" {
  value = aws_db_instance.postgres.endpoint
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address
}
2.2 Kubernetes Configuration
yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wildautomations-api
  namespace: production
  labels:
    app: wildautomations-api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: wildautomations-api
  template:
    metadata:
      labels:
        app: wildautomations-api
    spec:
      containers:
      - name: api
        image: ghcr.io/wildautomations/api:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        - name: LOG_LEVEL
          value: "info"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: wildautomations-api
  namespace: production
spec:
  selector:
    app: wildautomations-api
  ports:
  - port: 80
    targetPort: 8000
    name: http
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: wildautomations-api-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: wildautomations-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: wildautomations-ingress
  namespace: production
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.wildautomations.com
    - wildautomations.com
    secretName: wildautomations-tls
  rules:
  - host: wildautomations.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: wildautomations-web
            port:
              number: 80
  - host: api.wildautomations.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: wildautomations-api
            port:
              number: 80
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cleanup-expired-opportunities
  namespace: production
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cleanup
            image: ghcr.io/wildautomations/admin
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: database-secret
                  key: url
            command: ["python", "-m", "scripts.cleanup_expired"]
          restartPolicy: OnFailure
3. Monitoring & Logging
3.1 Prometheus Configuration
yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - "alerts/*.yml"

scrape_configs:
  - job_name: 'kubernetes-apiservers'
    kubernetes_sd_configs:
      - role: endpoints
    scheme: https
    tls_config:
      ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
    relabel_configs:
      - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
        action: keep
        regex: default;kubernetes;https

  - job_name: 'kubernetes-nodes'
    kubernetes_sd_configs:
      - role: node
    scheme: https
    tls_config:
      ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
    relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)

  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
      - action: labelmap
        regex: __meta_kubernetes_pod_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        action: replace
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_pod_name]
        action: replace
        target_label: kubernetes_pod_name

  - job_name: 'wildautomations-api'
    static_configs:
      - targets: ['wildautomations-api:8000']
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: 'postgresql'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
3.2 Alert Rules
yaml
# prometheus/alerts/system.yml
groups:
  - name: system_alerts
    interval: 30s
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for more than 5 minutes"

      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is above 85% for more than 5 minutes"

      - alert: HighDiskUsage
        expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100 < 20
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High disk usage detected"
          description: "Disk usage is above 80% for more than 5 minutes"

  - name: application_alerts
    interval: 30s
    rules:
      - alert: APIErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High API error rate"
          description: "API error rate is above 5% for more than 5 minutes"

      - alert: HighAPILatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency"
          description: "95th percentile API latency is above 2 seconds"

      - alert: QueueBacklog
        expr: celery_queue_size > 1000
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Celery queue backlog"
          description: "Celery queue has more than 1000 pending tasks"

      - alert: DatabaseConnections
        expr: pg_stat_database_numbackends > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Database connections high"
          description: "Database connections are above 80 for more than 2 minutes"

      - alert: ScraperFailure
        expr: (scraper_success_total / scraper_attempts_total) * 100 < 80
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "Scraper failure rate high"
          description: "Scraper success rate is below 80% for more than 15 minutes"
4. Backup & Recovery
4.1 Backup Configuration
python
# scripts/backup.py
import os
import boto3
from datetime import datetime
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.backup_bucket = os.environ.get('BACKUP_BUCKET')
        self.encryption_key = os.environ.get('ENCRYPTION_KEY')
        
    def create_database_backup(self) -> str:
        """Create database backup"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_file = f'/tmp/db_backup_{timestamp}.sql.gz'
        
        # Dump database
        cmd = f"""
            pg_dump -h {os.environ['DB_HOST']} \
                    -U {os.environ['DB_USER']} \
                    -d {os.environ['DB_NAME']} \
                    | gzip > {backup_file}
        """
        
        subprocess.check_call(cmd, shell=True)
        logger.info(f"Database backup created: {backup_file}")
        
        return backup_file
    
    def upload_backup(self, backup_file: str):
        """Upload backup to S3"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        s3_key = f"database/backup_{timestamp}.sql.gz"
        
        # Encrypt backup
        encrypted_file = self._encrypt_file(backup_file)
        
        # Upload to S3
        self.s3_client.upload_file(
            encrypted_file,
            self.backup_bucket,
            s3_key,
            ExtraArgs={
                'ServerSideEncryption': 'AES256',
                'StorageClass': 'STANDARD_IA'
            }
        )
        
        logger.info(f"Backup uploaded to S3: {s3_key}")
        
        # Clean up local files
        os.remove(backup_file)
        os.remove(encrypted_file)
    
    def _encrypt_file(self, input_file: str) -> str:
        """Encrypt backup file"""
        encrypted_file = f"{input_file}.enc"
        
        cmd = f"""
            openssl enc -aes-256-cbc -salt \
                -in {input_file} \
                -out {encrypted_file} \
                -pass pass:{self.encryption_key}
        """
        
        subprocess.check_call(cmd, shell=True)
        logger.info(f"Backup encrypted: {encrypted_file}")
        
        return encrypted_file
    
    def restore_database(self, backup_key: str):
        """Restore database from backup"""
        # Download backup
        local_file = f'/tmp/restore_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.sql.gz'
        
        self.s3_client.download_file(
            self.backup_bucket,
            backup_key,
            local_file
        )
        
        # Decrypt backup
        decrypted_file = self._decrypt_file(local_file)
        
        # Restore database
        cmd = f"""
            gunzip -c {decrypted_file} | \
            psql -h {os.environ['DB_HOST']} \
                 -U {os.environ['DB_USER']} \
                 -d {os.environ['DB_NAME']}
        """
        
        subprocess.check_call(cmd, shell=True)
        logger.info(f"Database restored from: {backup_key}")
        
        # Clean up
        os.remove(local_file)
        os.remove(decrypted_file)
    
    def _decrypt_file(self, input_file: str) -> str:
        """Decrypt backup file"""
        decrypted_file = f"{input_file}.dec"
        
        cmd = f"""
            openssl enc -d -aes-256-cbc \
                -in {input_file} \
                -out {decrypted_file} \
                -pass pass:{self.encryption_key}
        """
        
        subprocess.check_call(cmd, shell=True)
        logger.info(f"Backup decrypted: {decrypted_file}")
        
        return decrypted_file

if __name__ == "__main__":
    backup_manager = BackupManager()
    
    # Create and upload backup
    backup_file = backup_manager.create_database_backup()
    backup_manager.upload_backup(backup_file)
