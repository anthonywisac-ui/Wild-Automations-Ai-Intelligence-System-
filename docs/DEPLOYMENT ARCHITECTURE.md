DEPLOYMENT ARCHITECTURE
1. Deployment Strategy
1.1 Strategy Overview
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT STRATEGY                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    BLUE-GREEN DEPLOYMENT                             │  │
│  │                                                                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │  │
│  │  │  Load       │  │  Blue       │  │  Green                      │ │  │
│  │  │  Balancer   │──►│  (Active)   │  │  (Standby)                 │ │  │
│  │  │             │  │  v1.0       │  │  v1.1                      │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    CANARY DEPLOYMENT                                 │  │
│  │                                                                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │  │
│  │  │  Load       │  │  Stable     │  │  Canary                     │ │  │
│  │  │  Balancer   │──►│  (95%)     │──►│  (5%)                      │ │  │
│  │  │             │  │  v1.0       │  │  v1.1                      │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    ROLLING UPDATE                                    │  │
│  │                                                                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │  │
│  │  │  Instance 1 │  │  Instance 2 │  │  Instance N                 │ │  │
│  │  │  v1.0       │──►│  v1.0       │──►│  v1.1                      │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

1.2 Deployment Configurations

# k8s/blue-green/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: wildautomations-ingress
  namespace: production
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: api.wildautomations.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: wildautomations-service
            port:
              number: 80

---
apiVersion: v1
kind: Service
metadata:
  name: wildautomations-service
  namespace: production
  labels:
    app: wildautomations
spec:
  selector:
    app: wildautomations
    environment: active
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wildautomations-blue
  namespace: production
  labels:
    app: wildautomations
    environment: active
    version: v1.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: wildautomations
      environment: active
  template:
    metadata:
      labels:
        app: wildautomations
        environment: active
        version: v1.0
    spec:
      containers:
      - name: wildautomations-api
        image: wildautomations/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: VERSION
          value: "v1.0"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wildautomations-green
  namespace: production
  labels:
    app: wildautomations
    environment: standby
    version: v1.1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: wildautomations
      environment: standby
  template:
    metadata:
      labels:
        app: wildautomations
        environment: standby
        version: v1.1
    spec:
      containers:
      - name: wildautomations-api
        image: wildautomations/api:new
        ports:
        - containerPort: 8000
        env:
        - name: VERSION
          value: "v1.1"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
			
1.3 Deployment Script

# scripts/deploy.py
import subprocess
import json
import time
import sys
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeploymentManager:
    def __init__(self, namespace: str = 'production'):
        self.namespace = namespace
        
    def deploy(self, version: str, strategy: str = 'rolling'):
        """Deploy new version"""
        
        if strategy == 'blue-green':
            self._deploy_blue_green(version)
        elif strategy == 'canary':
            self._deploy_canary(version)
        else:
            self._deploy_rolling(version)
    
    def _deploy_blue_green(self, version: str):
        """Blue-Green deployment"""
        
        logger.info(f"Starting Blue-Green deployment for version {version}")
        
        # Deploy to green environment
        self._update_deployment('green', version)
        
        # Wait for green to be ready
        self._wait_for_deployment('green')
        
        # Run validation tests
        if self._validate_deployment('green'):
            logger.info("Green deployment validated")
            # Switch traffic to green
            self._switch_traffic('green')
            # Decommission blue
            self._decommission_deployment('blue')
        else:
            logger.error("Green deployment validation failed")
            self._rollback('green')
    
    def _deploy_canary(self, version: str):
        """Canary deployment"""
        
        logger.info(f"Starting Canary deployment for version {version}")
        
        # Deploy canary
        self._update_deployment('canary', version)
        self._wait_for_deployment('canary')
        
        # Start with 5% traffic
        self._update_traffic_distribution({'canary': 5, 'stable': 95})
        
        # Monitor for 10 minutes
        if self._monitor_canary(10):
            # Gradual rollout
            stages = [10, 25, 50, 75, 100]
            for percentage in stages:
                logger.info(f"Rolling out to {percentage}%")
                self._update_traffic_distribution(
                    {'canary': percentage, 'stable': 100 - percentage}
                )
                time.sleep(60)
                
            # Complete rollout
            self._update_traffic_distribution({'canary': 100})
        else:
            logger.error("Canary deployment failed")
            self._rollback_canary()
    
    def _update_deployment(self, env: str, version: str):
        """Update deployment image"""
        cmd = f"""
            kubectl set image deployment/wildautomations-{env} \
                wildautomations-api=wildautomations/api:{version} \
                -n {self.namespace}
        """
        subprocess.check_call(cmd, shell=True)
    
    def _wait_for_deployment(self, env: str, timeout: int = 300):
        """Wait for deployment to be ready"""
        cmd = f"""
            kubectl rollout status deployment/wildautomations-{env} \
                -n {self.namespace} \
                --timeout={timeout}s
        """
        subprocess.check_call(cmd, shell=True)
    
    def _validate_deployment(self, env: str) -> bool:
        """Validate deployment"""
        # Get service endpoint
        cmd = f"""
            kubectl get service wildautomations-{env} \
                -n {self.namespace} \
                -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'
        """
        ip = subprocess.check_output(cmd, shell=True).decode().strip()
        
        # Run health checks
        try:
            # Check health endpoint
            subprocess.check_call(
                f'curl -f http://{ip}/health',
                shell=True
            )
            
            # Run smoke tests
            subprocess.check_call(
                f'python -m pytest tests/smoke --base-url http://{ip}',
                shell=True
            )
            
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _switch_traffic(self, env: str):
        """Switch traffic to new environment"""
        # Update service selector
        cmd = f"""
            kubectl patch service wildautomations-service \
                -n {self.namespace} \
                -p '{{"spec":{{"selector":{{"environment":"{env}"}}}}}}'
        """
        subprocess.check_call(cmd, shell=True)
    
    def _update_traffic_distribution(self, distribution: Dict):
        """Update traffic distribution for canary"""
        annotations = {}
        for env, percentage in distribution.items():
            if env == 'canary':
                annotations['nginx.ingress.kubernetes.io/canary-weight'] = str(percentage)
            elif env == 'stable':
                annotations['nginx.ingress.kubernetes.io/canary-weight'] = str(100 - percentage)
        
        # Update ingress annotations
        for key, value in annotations.items():
            cmd = f"""
                kubectl annotate ingress wildautomations-ingress \
                    -n {self.namespace} \
                    {key}={value} --overwrite
            """
            subprocess.check_call(cmd, shell=True)
			
2. Containerization
2.1 Dockerfile

# Dockerfile
FROM python:3.11-slim-bullseye AS builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run tests
RUN python -m pytest tests/unit -v

# Build stage
FROM python:3.11-slim-bullseye

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY --from=builder /app /app

# Create non-root user
RUN useradd -m -u 1000 wildautomations && \
    chown -R wildautomations:wildautomations /app

USER wildautomations

# Set environment variables
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

2.2 Docker Compose

# docker-compose.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./nginx/locations:/etc/nginx/locations:ro
    depends_on:
      - api
    networks:
      - wildautomations-network

  api:
    build: .
    image: wildautomations/api:${VERSION:-latest}
    container_name: api
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=${ENVIRONMENT:-development}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    volumes:
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    networks:
      - wildautomations-network
    restart: unless-stopped

  worker:
    build: .
    image: wildautomations/worker:${VERSION:-latest}
    container_name: worker
    command: celery -A tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=${ENVIRONMENT:-development}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    volumes:
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    networks:
      - wildautomations-network
    restart: unless-stopped

  beat:
    build: .
    image: wildautomations/beat:${VERSION:-latest}
    container_name: beat
    command: celery -A tasks beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=${ENVIRONMENT:-development}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    volumes:
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    networks:
      - wildautomations-network
    restart: unless-stopped

  postgres:
    image: pgvector/pgvector:pg15
    container_name: postgres
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - wildautomations-network
    restart: unless-stopped

  redis:
    image: redis:alpine
    container_name: redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - wildautomations-network
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:v2.45.0
    container_name: prometheus
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - wildautomations-network
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.2.0
    container_name: grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    ports:
      - "3000:3000"
    networks:
      - wildautomations-network
    restart: unless-stopped

  elk:
    image: sebp/elk:8.6.2
    container_name: elk
    environment:
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
      - LOGSTASH_CONF=/etc/logstash/conf.d/logstash.conf
    volumes:
      - elk_data:/var/lib/elasticsearch
      - ./elk/logstash.conf:/etc/logstash/conf.d/logstash.conf:ro
    ports:
      - "9200:9200"
      - "5601:5601"
      - "5044:5044"
    networks:
      - wildautomations-network
    restart: unless-stopped

networks:
  wildautomations-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
  elk_data:
  
3. Database Migration
3.1 Alembic Migration

# migrations/script.py.mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade() -> None:
    ${upgrades if upgrades else "pass"}

def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
	
# migrations/versions/001_initial_schema.py
"""initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', UUID, primary_key=True, default=uuid.uuid4),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('phone', sa.String(20), unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100)),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('email_verified', sa.Boolean, default=False),
        sa.Column('phone_verified', sa.Boolean, default=False),
        sa.Column('active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('preferences', JSONB)
    )
    
    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_phone', 'users', ['phone'])
    
    # Create profiles table
    op.create_table(
        'user_profiles',
        sa.Column('profile_id', UUID, primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID, nullable=False),
        sa.Column('country', sa.String(100)),
        sa.Column('city', sa.String(100)),
        sa.Column('date_of_birth', sa.Date),
        sa.Column('gender', sa.String(20)),
        sa.Column('nationality', sa.String(100)),
        sa.Column('education_level', sa.String(50)),
        sa.Column('degree', sa.String(100)),
        sa.Column('field_of_study', sa.String(100)),
        sa.Column('institution', sa.String(200)),
        sa.Column('graduation_year', sa.Integer),
        sa.Column('experience_years', sa.Integer),
        sa.Column('current_title', sa.String(100)),
        sa.Column('current_company', sa.String(200)),
        sa.Column('skills', sa.ARRAY(sa.String)),
        sa.Column('languages', sa.ARRAY(sa.String)),
        sa.Column('visa_status', sa.String(50)),
        sa.Column('preferred_countries', sa.ARRAY(sa.String)),
        sa.Column('preferred_cities', sa.ARRAY(sa.String)),
        sa.Column('budget_range', JSONB),
        sa.Column('salary_range', JSONB),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create foreign key constraints
    op.create_foreign_key(
        'fk_user_profiles_user_id',
        'user_profiles',
        'users',
        ['user_id'],
        ['user_id'],
        ondelete='CASCADE'
    )
    
    # Create opportunities table
    op.create_table(
        'opportunities',
        sa.Column('opportunity_id', UUID, primary_key=True, default=uuid.uuid4),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('source_id', sa.String(255), nullable=False),
        sa.Column('domain', sa.String(50), nullable=False),
        sa.Column('source_url', sa.Text),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('raw_data', JSONB),
        sa.Column('normalized_data', JSONB),
        sa.Column('embedding', sa.Text),  # Vector type
        sa.Column('score', sa.Float),
        sa.Column('confidence', sa.Float),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('posted_date', sa.DateTime),
        sa.Column('expiry_date', sa.DateTime),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create unique constraint
    op.create_unique_constraint(
        'uq_opportunities_source_source_id',
        'opportunities',
        ['source', 'source_id']
    )
    
    # Create indexes
    op.create_index('idx_opportunities_domain_status', 'opportunities', ['domain', 'status'])
    op.create_index('idx_opportunities_source', 'opportunities', ['source'])
    op.create_index('idx_opportunities_posted_date', 'opportunities', ['posted_date'])
    
    # Create pgvector extension if not exists
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('opportunities')
    op.drop_table('user_profiles')
    op.drop_table('users')
	
