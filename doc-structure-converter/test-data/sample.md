# API Reference Guide

This document demonstrates structure-aware page breaking for tables and code blocks. The content is intentionally designed to test page boundary behavior.

## 1. Authentication

All API requests require authentication via Bearer tokens. The following example shows how to obtain and use tokens.

### 1.1 Token Request

To authenticate, send a POST request to the token endpoint:

```bash
curl -X POST https://api.example.com/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "grant_type": "client_credentials",
    "scope": "read write admin"
  }'
```

The response will include an access token valid for 3600 seconds.

### 1.2 Error Codes

Authentication can fail for several reasons. The following table lists all possible error codes:

| Error Code | HTTP Status | Description | Resolution |
|-----------|------------|-------------|------------|
| AUTH_001 | 401 | Invalid client credentials | Verify client_id and client_secret |
| AUTH_002 | 401 | Expired token | Request a new token |
| AUTH_003 | 403 | Insufficient scope | Request additional permissions |
| AUTH_004 | 429 | Rate limit exceeded | Wait and retry after the specified delay |
| AUTH_005 | 400 | Malformed request | Check request body format |
| AUTH_006 | 503 | Auth service unavailable | Retry with exponential backoff |
| AUTH_007 | 401 | Revoked token | Re-authenticate from scratch |
| AUTH_008 | 400 | Invalid grant type | Use client_credentials or authorization_code |

## 2. User Management

The User API provides CRUD operations for managing user accounts.

### 2.1 Create User

```javascript
async function createUser(userData) {
  const response = await fetch('https://api.example.com/users', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      name: userData.name,
      email: userData.email,
      role: userData.role || 'viewer',
      department: userData.department,
      preferences: {
        notifications: true,
        theme: 'system',
        language: 'en',
      },
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Failed to create user: ${error.message}`);
  }

  return response.json();
}
```

### 2.2 User Roles and Permissions

Each user has a role that determines their access level. The permissions matrix is as follows:

| Role | Read | Write | Delete | Admin | Audit Log | API Access |
|------|------|-------|--------|-------|-----------|------------|
| Viewer | Yes | No | No | No | No | Read-only |
| Editor | Yes | Yes | No | No | No | Read/Write |
| Manager | Yes | Yes | Yes | No | Yes | Full |
| Admin | Yes | Yes | Yes | Yes | Yes | Full |
| Super Admin | Yes | Yes | Yes | Yes | Yes | Full + Config |
| Service Account | Yes | Yes | No | No | Yes | Scoped |
| Auditor | Yes | No | No | No | Yes | Read-only |
| Guest | Limited | No | No | No | No | None |

Some additional text here to push content further. The system supports hierarchical role inheritance, meaning a Manager inherits all permissions of an Editor, and an Admin inherits all permissions of a Manager. Custom roles can be defined through the Roles API endpoint.

## 3. Data Processing Pipeline

The pipeline processes incoming data through several stages.

### 3.1 Pipeline Configuration

```python
class DataPipeline:
    """Multi-stage data processing pipeline with error handling."""

    def __init__(self, config):
        self.stages = []
        self.error_handlers = {}
        self.metrics = PipelineMetrics()
        self.config = config

    def add_stage(self, name, processor, retry_count=3):
        """Add a processing stage to the pipeline."""
        self.stages.append({
            'name': name,
            'processor': processor,
            'retry_count': retry_count,
            'timeout': self.config.get('stage_timeout', 30),
        })
        return self

    def execute(self, data):
        """Execute all pipeline stages sequentially."""
        result = data
        for stage in self.stages:
            try:
                self.metrics.start_stage(stage['name'])
                result = stage['processor'](result)
                self.metrics.end_stage(stage['name'], success=True)
            except Exception as e:
                self.metrics.end_stage(stage['name'], success=False)
                handler = self.error_handlers.get(stage['name'])
                if handler:
                    result = handler(result, e)
                else:
                    raise PipelineError(stage['name'], e)
        return result
```

### 3.2 Stage Performance Metrics

The following table shows typical performance characteristics of each pipeline stage:

| Stage | Avg Latency | P99 Latency | Throughput | Memory | CPU | Error Rate |
|-------|------------|-------------|------------|--------|-----|------------|
| Ingestion | 12ms | 45ms | 10,000/s | 256MB | 15% | 0.01% |
| Validation | 3ms | 8ms | 50,000/s | 128MB | 5% | 0.1% |
| Transformation | 25ms | 120ms | 5,000/s | 512MB | 45% | 0.05% |
| Enrichment | 50ms | 200ms | 2,000/s | 1GB | 30% | 0.5% |
| Deduplication | 8ms | 30ms | 20,000/s | 2GB | 10% | 0.001% |
| Indexing | 15ms | 60ms | 8,000/s | 512MB | 25% | 0.02% |
| Archival | 100ms | 500ms | 1,000/s | 256MB | 5% | 0.1% |
| Notification | 20ms | 80ms | 15,000/s | 128MB | 8% | 1.0% |

### 3.3 Error Recovery

When a stage fails, the error recovery mechanism activates:

```typescript
interface ErrorRecoveryConfig {
  maxRetries: number;
  backoffMs: number;
  backoffMultiplier: number;
  deadLetterQueue: string;
  alertThreshold: number;
}

class ErrorRecovery {
  private config: ErrorRecoveryConfig;
  private retryCount: Map<string, number> = new Map();

  async recover(stageId: string, error: Error, data: unknown): Promise<unknown> {
    const attempts = this.retryCount.get(stageId) || 0;

    if (attempts >= this.config.maxRetries) {
      await this.sendToDeadLetter(stageId, error, data);
      this.retryCount.delete(stageId);
      throw new UnrecoverableError(stageId, error);
    }

    const delay = this.config.backoffMs *
      Math.pow(this.config.backoffMultiplier, attempts);

    await this.sleep(delay);
    this.retryCount.set(stageId, attempts + 1);

    return this.retryStage(stageId, data);
  }

  private async sendToDeadLetter(
    stageId: string,
    error: Error,
    data: unknown
  ): Promise<void> {
    // Send failed record to dead letter queue for manual review
    console.warn(`Stage ${stageId} failed permanently: ${error.message}`);
  }
}
```

## 4. Deployment Configuration

### 4.1 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| API_HOST | Yes | - | API server hostname |
| API_PORT | No | 8080 | HTTP listener port |
| DB_URL | Yes | - | PostgreSQL connection string |
| REDIS_URL | No | localhost:6379 | Redis cache endpoint |
| LOG_LEVEL | No | info | Logging verbosity |
| MAX_WORKERS | No | 4 | Worker thread count |
| QUEUE_SIZE | No | 1000 | Message queue buffer size |
| HEALTH_CHECK_INTERVAL | No | 30s | Health check frequency |
| SSL_CERT_PATH | Conditional | - | TLS certificate path |
| SSL_KEY_PATH | Conditional | - | TLS private key path |

### 4.2 Docker Compose Example

```yaml
version: '3.8'
services:
  api:
    image: myapp/api:latest
    ports:
      - "8080:8080"
    environment:
      - API_HOST=0.0.0.0
      - DB_URL=postgresql://user:pass@db:5432/myapp
      - REDIS_URL=redis:6379
      - LOG_LEVEL=info
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

## 5. Summary

This document covered the complete API reference including authentication, user management, data processing pipelines, and deployment configuration. Each section contains tables and code blocks that should remain intact across page boundaries when using structure-aware PDF conversion.
