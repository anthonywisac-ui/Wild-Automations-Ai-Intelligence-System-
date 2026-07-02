MONITORING ARCHITECTURE
1. Monitoring Stack
1.1 Components
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MONITORING STACK                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    METRICS COLLECTION                                 │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Prometheus │  │  Node       │  │  Postgres   │  │  Redis    │  │  │
│  │  │  Exporter   │  │  Exporter   │  │  Exporter   │  │  Exporter │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Blackbox   │  │  StatsD     │  │  Alert      │  │  Push     │  │  │
│  │  │  Exporter   │  │  Exporter   │  │  Manager    │  │  Gateway  │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    LOG COLLECTION                                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Filebeat   │  │  Logstash   │  │  Elastic    │  │  Kibana   │  │  │
│  │  │  (Logs)     │──►│  (Parse)    │──►│  Search    │──►│  (UI)     │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    TRACE COLLECTION                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │  │
│  │  │  Jaeger     │  │  OpenTele   │  │  Collector  │  │  Tempo    │  │  │
│  │  │  Agent      │──►│  metry      │──►│  (Data)     │──►│  (Storage)│  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    VISUALIZATION                                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │  │
│  │  │  Grafana    │  │  Kibana     │  │  Jaeger UI                  │ │  │
│  │  │  (Metrics)  │  │  (Logs)     │  │  (Traces)                   │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

1.2 Grafana Dashboards

// grafana/dashboards/api_dashboard.json
{
  "dashboard": {
    "id": null,
    "title": "API Performance Dashboard",
    "tags": ["wildautomations", "api", "performance"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{path}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "API Latency (P95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "{{path}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])",
            "format": "percent"
          }
        ],
        "gridPos": {"h": 4, "w": 6, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "Active Users",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(active_users_total)",
            "format": "none"
          }
        ],
        "gridPos": {"h": 4, "w": 6, "x": 6, "y": 8}
      },
      {
        "id": 5,
        "title": "Service Uptime",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"wildautomations-api\"}",
            "format": "none"
          }
        ],
        "gridPos": {"h": 4, "w": 6, "x": 12, "y": 8}
      }
    ],
    "time": {
      "from": "now-24h",
      "to": "now"
    }
  },
  "overwrite": true
}

1.3 Logging Configuration
# config/logging.py
import logging
import sys
from pythonjsonlogger import jsonlogger

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id

def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level))
    
    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CustomJsonFormatter())
    root_logger.addHandler(console_handler)
    
    # Add file handler for errors
    file_handler = logging.FileHandler('/var/log/wildautomations/error.log')
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(CustomJsonFormatter())
    root_logger.addHandler(file_handler)

def get_logger(name: str) -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(name)

# Middleware for request logging
class RequestLoggingMiddleware:
    async def __call__(self, request, call_next):
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        request.state.request_id = request_id
        
        # Log request
        logger = get_logger('api')
        logger.info(
            f"Request started",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'query': str(request.query_params)
            }
        )
        
        start_time = time.time()
        response = await call_next(request)
        
        # Log response
        duration = time.time() - start_time
        logger.info(
            f"Request completed",
            extra={
                'request_id': request_id,
                'status_code': response.status_code,
                'duration': duration
            }
        )
        
        response.headers['X-Request-ID'] = request_id
        return response
		
2. APM & Tracing
2.1 OpenTelemetry Configuration

# config/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
import os

def setup_tracing(app):
    """Setup OpenTelemetry tracing"""
    
    # Set service name
    service_name = os.getenv('SERVICE_NAME', 'wildautomations-api')
    
    # Create TracerProvider
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    
    # Configure Jaeger exporter
    jaeger_endpoint = os.getenv('JAEGER_ENDPOINT', 'jaeger:6831')
    jaeger_exporter = JaegerExporter(
        agent_host_name=jaeger_endpoint.split(':')[0],
        agent_port=int(jaeger_endpoint.split(':')[1])
    )
    
    # Add span processor
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument HTTP requests
    RequestsInstrumentor().instrument()
    
    # Instrument SQLAlchemy
    from database import engine
    SQLAlchemyInstrumentor().instrument(
        engine=engine,
        service=service_name
    )
    
    return trace.get_tracer(__name__)

# Add context to async tasks
def trace_task(task_name: str):
    """Decorator to trace Celery tasks"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(f"task.{task_name}") as span:
                # Add metadata
                span.set_attribute("task.name", task_name)
                span.set_attribute("task.args", str(args))
                span.set_attribute("task.kwargs", str(kwargs))
                
                return func(*args, **kwargs)
        return wrapper
    return decorator
	
3. Health Checks
3.1 Health Check Endpoints

# api/health.py
from fastapi import APIRouter, Depends
from typing import Dict
import time

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict:
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

@router.get("/ready")
async def readiness_check() -> Dict:
    """Readiness check"""
    
    # Check database
    db_ready = await check_database()
    
    # Check Redis
    redis_ready = await check_redis()
    
    # Check AI services
    ai_ready = await check_ai_services()
    
    ready = db_ready and redis_ready and ai_ready
    
    return {
        "status": "ready" if ready else "not_ready",
        "timestamp": time.time(),
        "components": {
            "database": db_ready,
            "redis": redis_ready,
            "ai_services": ai_ready
        }
    }

@router.get("/live")
async def liveness_check() -> Dict:
    """Liveness check"""
    return {
        "status": "alive",
        "timestamp": time.time()
    }

@router.get("/metrics")
async def metrics() -> Dict:
    """Get application metrics"""
    return {
        "uptime": time.time() - start_time,
        "active_connections": get_active_connections(),
        "queue_size": get_queue_size(),
        "cache_hit_rate": get_cache_hit_rate()
    }

async def check_database() -> bool:
    """Check database connectivity"""
    try:
        from database import SessionLocal
        db = SessionLocal()
        result = db.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
    finally:
        db.close()

async def check_redis() -> bool:
    """Check Redis connectivity"""
    try:
        from redis import Redis
        redis_client = Redis.from_url(os.getenv('REDIS_URL'))
        return redis_client.ping()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False
		
3.2 Monitoring Alerts
# grafana/alerts/alerts.yml
groups:
  - name: api_alerts
    rules:
      - alert: APIDown
        expr: up{job="wildautomations-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "API is down"
          description: "API service has been down for more than 1 minute"

      - alert: HighErrorRate
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "API error rate is above 5% for more than 5 minutes"

      - alert: HighLatency
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 2
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

      - alert: DatabaseConnectionsHigh
        expr: pg_stat_database_numbackends > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Database connections high"
          description: "Database connections are above 80 for more than 2 minutes"

      - alert: DatabaseSlowQueries
        expr: rate(pg_stat_database_queries_duration_seconds_count[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database slow queries detected"
          description: "Database is experiencing slow queries"

      - alert: LowCacheHitRate
        expr: redis_cache_hit_rate < 0.7
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate"
          description: "Redis cache hit rate is below 70%"

      - alert: ScraperFailure
        expr: (scraper_success_total / scraper_attempts_total) * 100 < 80
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "Scraper failure rate high"
          description: "Scraper success rate is below 80% for more than 15 minutes"

      - alert: AIModelFailure
        expr: (ai_model_success_total / ai_model_attempts_total) * 100 < 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "AI model failure rate high"
          description: "AI model success rate is below 85% for more than 5 minutes"

      - alert: HighAICost
        expr: ai_model_cost_total > 0.01 * 60  # $0.01 per minute
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High AI model cost"
          description: "AI model cost is exceeding $0.01 per minute"
		  

