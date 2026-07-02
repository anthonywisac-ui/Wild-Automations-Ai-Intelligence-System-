1. Architecture Overview
1.1 Architecture Style
The system implements a Microservices Architecture with Event-Driven communication patterns. This design enables:

Independent scaling of components

Isolation of failures

Technology flexibility

Team autonomy

Easy deployment and updates

1.2 Architecture Principles
Stateless Services: Services don't maintain state between requests

Event Sourcing: System state changes captured as events

CQRS: Separate read and write models

Circuit Breakers: Graceful failure handling

Bulkheading: Resource isolation between components

2. Component Architecture
2.1 Service Components
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SERVICES LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  API Gateway     │  │  Auth Service    │  │  User Service            │  │
│  │                  │  │                  │  │                          │  │
│  │  • Routing       │  │  • Authentication│  │  • Profile Management   │  │
│  │  • Rate Limit    │  │  • Authorization │  │  • Preferences          │  │
│  │  • Load Balance  │  │  • JWT Issuer    │  │  • Search History       │  │
│  │  • SSL Term      │  │  • SSO          │  │  • Activity Tracking     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  Search Service  │  │  AI Service      │  │  Notification Service    │  │
│  │                  │  │                  │  │                          │  │
│  │  • Semantic      │  │  • Intent Detect │  │  • Matching              │  │
│  │  • Keyword       │  │  • Extract       │  │  • Formatting            │  │
│  │  • Hybrid        │  │  • Generate      │  │  • Channel Selection     │  │
│  │  • Caching       │  │  • Model Mgmt    │  │  • Delivery Tracking     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  Scraper Service │  │  Admin Service   │  │  WhatsApp Service        │  │
│  │                  │  │                  │  │                          │  │
│  │  • Source Mgmt   │  │  • Monitoring    │  │  • Message Processing    │  │
│  │  • Scheduling    │  │  • Analytics     │  │  • Session Management    │  │
│  │  • Execution     │  │  • User Mgmt     │  │  • Media Handling        │  │
│  │  • Deduplication │  │  • Source Mgmt   │  │  • Template Rendering    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
2.2 Infrastructure Components
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INFRASTRUCTURE LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  Load Balancer   │  │  Message Queue   │  │  Redis Cache             │  │
│  │  (NGINX)         │  │  (Redis)         │  │                          │  │
│  │                  │  │                  │  │  • Session Storage       │  │
│  │  • HTTP/HTTPS    │  │  • Task Queue    │  │  • Rate Limiting         │  │
│  │  • Health Check  │  │  • Pub/Sub       │  │  • Search Cache          │  │
│  │  • SSL Certs     │  │  • Streams       │  │  • Lock Manager          │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  PostgreSQL      │  │  Celery Workers  │  │  Monitoring              │  │
│  │  (Primary)       │  │                  │  │                          │  │
│  │                  │  │  • Async Tasks   │  │  • Prometheus            │  │
│  │  • OLTP          │  │  • Scheduled     │  │  • Grafana              │  │
│  │  • pgvector      │  │  • Retry         │  │  • Loki                 │  │
│  │  • Replication   │  │  • Rate Limit    │  │  • Tempo                │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  PostgreSQL      │  │  Object Storage  │  │  DNS/SSL                 │  │
│  │  (Read Replicas) │  │  (S3-compatible) │  │                          │  │
│  │                  │  │                  │  │  • Domain Management     │  │
│  │  • Reporting     │  │  • Raw Data      │  │  • SSL Cert Renewal      │  │
│  │  • Analytics     │  │  • Images        │  │  • CDN Integration       │  │
│  │  • Search        │  │  • Backups       │  │  • DNS Load Balancing    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
3. Deployment Architecture
3.1 Containerization Strategy
yaml
# Docker Compose Structure
services:
  # Load Balancer
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api

  # API Service
  api:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
      - AI_API_KEYS=...
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  # Celery Workers
  worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - postgres
    deploy:
      replicas: 5
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # Database
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      - POSTGRES_DB=wildautomations
      - POSTGRES_USER=wildautomations
      - POSTGRES_PASSWORD=...
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

  # Redis
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # Monitoring
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
3.2 Kubernetes Deployment
yaml
# Kubernetes Deployment Manifest
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wildautomations-api
  namespace: production
spec:
  replicas: 3
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
        image: wildautomations/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
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
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
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
4. Communication Architecture
4.1 Service Communication Patterns
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                     COMMUNICATION PATTERNS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   SYNCHRONOUS (HTTP/REST)               ASYNCHRONOUS (Events)              │
│   ┌───────────────────────────┐        ┌───────────────────────────┐      │
│   │ API Gateway ←───→ Services│        │ Services ────→ Event Bus │      │
│   │                           │        │                           │      │
│   │ Webhooks ←───→ Endpoints │        │ Services ←───→ Event Bus │      │
│   │                           │        │                           │      │
│   │ Health Checks             │        │ Task Queue ←───→ Workers │      │
│   └───────────────────────────┘        └───────────────────────────┘      │
│                                                                             │
│   HYBRID (Request-Reply with Queues)   STREAMING (WebSocket)               │
│   ┌───────────────────────────┐        ┌───────────────────────────┐      │
│   │ Client → Queue → Worker   │        │ WhatsApp ←───→ WebSocket │      │
│   │         │                 │        │                           │      │
│   │ Client ←─┘                │        │ Real-time Updates         │      │
│   └───────────────────────────┘        └───────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
4.2 Event-Driven Architecture
yaml
Events:
  - OpportunityCreated:
      payload: { opportunity_id, domain, source }
      handlers: [NotificationService, SearchService, AnalyticsService]
      
  - OpportunityUpdated:
      payload: { opportunity_id, changes }
      handlers: [SearchService, NotificationService]
      
  - UserRegistered:
      payload: { user_id, email }
      handlers: [ProfileService, AnalyticsService, WelcomeService]
      
  - UserSearch:
      payload: { user_id, query, results }
      handlers: [AnalyticsService, RecommendationService]
      
  - NotificationDelivered:
      payload: { notification_id, user_id, channel, status }
      handlers: [AnalyticsService, UserService]
5. Security Architecture
5.1 Security Layers
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY LAYERS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   NETWORK LAYER                                                            │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │  • SSL/TLS Termination (NGINX)                                  │      │
│   │  • Rate Limiting (per IP, per User)                            │      │
│   │  • DDoS Protection (Cloudflare)                               │      │
│   │  • IP Whitelisting for Admin                                  │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│   APPLICATION LAYER                                                         │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │  • JWT Authentication (Bearer Token)                           │      │
│   │  • RBAC Authorization (Admin/User/Premium)                    │      │
│   │  • API Key Validation (External Services)                     │      │
│   │  • Input Validation (Pydantic)                                │      │
│   │  • SQL Injection Prevention (ORM)                             │      │
│   │  • XSS Prevention (Sanitization)                              │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│   DATA LAYER                                                                │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │  • Encryption at Rest (AES-256)                               │      │
│   │  • Encryption in Transit (TLS 1.3)                            │      │
│   │  • Data Masking (PII)                                         │      │
│   │  • Audit Logging (All Operations)                             │      │
│   │  • Backup Encryption                                          │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
5.2 Authentication Flow
text
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Client     │    │   API        │    │   Auth       │    │   Database   │
│              │    │   Gateway    │    │   Service    │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
      │                    │                    │                    │
      │ ① Login Request   │                    │                    │
      ├───────────────────►│                    │                    │
      │                    │                    │                    │
      │                    │ ② Validate         │                    │
      │                    ├───────────────────►│                    │
      │                    │                    │                    │
      │                    │                    │ ③ Check Creds     │
      │                    │                    ├───────────────────►│
      │                    │                    │                    │
      │                    │                    │ ④ User Found      │
      │                    │                    │◄───────────────────│
      │                    │                    │                    │
      │                    │ ⑤ JWT Token       │                    │
      │                    │◄───────────────────│                    │
      │                    │                    │                    │
      │ ⑥ Token + Profile │                    │                    │
      │◄───────────────────│                    │                    │
      │                    │                    │                    │
      │ ⑦ Subsequent      │                    │                    │
      │    Requests with   │                    │                    │
      │    Bearer Token    │                    │                    │
      ├───────────────────►│                    │                    │
      │                    │                    │                    │
      │                    │ ⑧ Validate Token  │                    │
      │                    ├───────────────────►│                    │
      │                    │                    │                    │
      │                    │ ⑨ Token Valid     │                    │
      │                    │◄───────────────────│                    │
      │                    │                    │                    │
      │ ⑩ Response        │                    │                    │
      │◄───────────────────│                    │                    │
      │                    │                    │                    │
6. Data Architecture
6.1 Data Flow Architecture
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   DATA INGESTION                DATA PROCESSING            DATA STORAGE    │
│   ┌──────────────────┐         ┌──────────────────┐      ┌───────────────┐ │
│   │  Scraped Data    │────────►│  Raw Storage    │─────►│  S3 Bucket    │ │
│   │  (External)      │         │  (JSON)         │      │  (Raw)        │ │
│   └──────────────────┘         └──────────────────┘      └───────────────┘ │
│           │                            │                         │         │
│           │                            ▼                         ▼         │
│   ┌──────────────────┐         ┌──────────────────┐      ┌───────────────┐ │
│   │  API Data        │────────►│  AI Processing   │─────►│  PostgreSQL   │ │
│   │  (External)      │         │  (Extraction)    │      │  (Normalized) │ │
│   └──────────────────┘         └──────────────────┘      └───────────────┘ │
│           │                            │                         │         │
│           │                            ▼                         ▼         │
│   ┌──────────────────┐         ┌──────────────────┐      ┌───────────────┐ │
│   │  RSS/Webhook     │────────►│  Normalization   │─────►│  Vector Store │ │
│   │  (External)      │         │  (Validation)    │      │  (pgvector)   │ │
│   └──────────────────┘         └──────────────────┘      └───────────────┘ │
│                                                                             │
│   DATA QUERY                    DATA DELIVERY                              │
│   ┌──────────────────┐         ┌──────────────────┐                        │
│   │  User Query      │────────►│  Search Engine   │───► Response           │
│   └──────────────────┘         └──────────────────┘                        │
│           │                             │                                  │
│           ▼                             ▼                                  │
│   ┌──────────────────┐         ┌──────────────────┐                        │
│   │  Cache Lookup    │         │  Notification    │───► Delivery           │
│   │  (Redis)         │         │  Engine          │                        │
│   └──────────────────┘         └──────────────────┘                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
6.2 Caching Strategy
yaml
Cache Layers:
  Application Cache:
    - Search Results: TTL=1 minute
    - User Profiles: TTL=5 minutes
    - AI Responses: TTL=10 minutes
    
  Database Cache:
    - Query Cache: TTL=30 seconds
    - Vector Cache: TTL=5 minutes
    - Lookup Tables: TTL=1 hour
    
  Content Cache:
    - Static Assets: TTL=24 hours
    - API Responses: TTL=5 minutes
    - Image Assets: TTL=7 days
    
  Cache Invalidation:
    - Write-through for user changes
    - Cache-aside for search
    - Event-based invalidation
7. Monitoring Architecture
7.1 Monitoring Stack
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MONITORING STACK                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   METRICS                    LOGS                     TRACES               │
│   ┌──────────────────┐      ┌──────────────────┐    ┌──────────────────┐   │
│   │  Prometheus      │      │  Loki            │    │  Tempo           │   │
│   │                  │      │                  │    │                  │   │
│   │  • System        │      │  • Application   │    │  • Distributed   │   │
│   │  • Application   │      │  • Access        │    │  • Performance   │   │
│   │  • Business      │      │  • Error         │    │  • Bottlenecks   │   │
│   └──────────────────┘      └──────────────────┘    └──────────────────┘   │
│            │                         │                        │            │
│            ▼                         ▼                        ▼            │
│   ┌──────────────────────────────────────────────────────────────────┐    │
│   │                          Grafana                                 │    │
│   │  • Dashboards                                                   │    │
│   │  • Alerts                                                       │    │
│   │  • Visualization                                                │    │
│   └──────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
7.2 Key Metrics
yaml
System Metrics:
  - CPU Usage per service
  - Memory Usage per service
  - Network I/O
  - Disk I/O
  - File Descriptors

Application Metrics:
  - Request Rate
  - Error Rate
  - Response Time (P50, P95, P99)
  - Active Users
  - Session Duration

Business Metrics:
  - Search Rate
  - Notification Rate
  - Click-Through Rate
  - User Acquisition Rate
  - Revenue per User

AI Metrics:
  - Model Latency
  - Token Usage
  - Cost per Request
  - Accuracy Metrics
  - Fallback Rate
