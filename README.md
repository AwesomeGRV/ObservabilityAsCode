# Observability as Code for New Relic

A comprehensive, production-ready observability-as-code solution for managing New Relic monitoring configurations across multiple applications with modern API architecture, database integration, and CI/CD automation.

##  Features

### Core Functionality
- **Standardized Alert Templates**: Pre-configured alerts for CPU, Memory, Disk, Pods, Latency, and Web Response metrics
- **Dashboard Templates**: Consistent dashboards for Infrastructure, Application Performance, Kubernetes, and Error Analysis
- **Application Inventory**: Track which applications are fully onboarded
- **Compliance Checker**: Verify all applications have correct alerts and dashboards
- **Coverage Scoring**: Automated scoring algorithm (0-100%) with gap analysis

### Modern Architecture
- **RESTful API**: FastAPI-based with OpenAPI documentation
- **Database Integration**: PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Authentication & Authorization**: JWT tokens, API keys, role-based permissions
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Monitoring & Metrics**: Prometheus metrics, health checks, system monitoring
- **Container Support**: Multi-stage Docker builds with security best practices

### Development & Operations
- **Comprehensive Testing**: Unit and integration tests with pytest
- **CI/CD Pipeline**: GitHub Actions with automated testing, security scanning, and deployment
- **API Versioning**: Versioned endpoints (`/api/v1/`) for backward compatibility
- **Error Handling**: Custom exception handlers with detailed error responses
- **Configuration Management**: Environment-based settings with Pydantic validation

##  Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Docker & Docker Compose (optional)
- New Relic Account ID and API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ObservabilityAsCode
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up database:**
   ```bash
   # Create database
   createdb observability
   
   # Run migrations
   alembic upgrade head
   ```

5. **Start the API server:**
   ```bash
   # Development
   python -m api.app
   
   # Production with Docker Compose
   docker-compose up -d
   ```

### Configuration

#### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/observability

# New Relic
NEW_RELIC_ACCOUNT_ID=your-account-id
NEW_RELIC_API_KEY=your-api-key

# Security
SECRET_KEY=your-secret-key
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# Logging
LOG_LEVEL=INFO
DEBUG=false
```

##  Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Applications   │    │   Terraform     │    │   Jenkins CI/CD │
│   Inventory     │────│   Modules       │────│   Integration   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Observability │
                    │      API        │
                    │   (FastAPI)     │
                    └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  PostgreSQL     │    │  Redis Cache    │    │  Prometheus     │
│  Database       │    │                 │    │  Metrics        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   New Relic     │
                    │   Platform      │
                    └─────────────────┘
```

##  API Documentation

### Base URL
- Development: `http://localhost:8000`
- Production: `https://your-api-domain.com`

### Authentication
The API supports multiple authentication methods:

1. **JWT Tokens** (for users)
2. **API Keys** (for service accounts)

#### Generate API Key
```bash
curl -X POST "http://localhost:8000/api/v1/auth/api-keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Service Key", "permissions": ["read", "write"]}'
```

### Key Endpoints

#### Applications
```bash
# List applications
GET /api/v1/applications

# Create application
POST /api/v1/applications
{
  "name": "My Application",
  "environment": "production",
  "entity_id": "nr-entity-123",
  "team": "platform"
}

# Get application details
GET /api/v1/applications/{app_id}

# Clone application
POST /api/v1/applications/{app_id}/clone
{
  "environment": "staging",
  "name": "My App (Staging)"
}
```

#### Alerts
```bash
# Create alert
POST /api/v1/applications/{app_id}/alerts
{
  "name": "High CPU Usage",
  "type": "cpu_usage",
  "nrql_query": "SELECT average(cpuPercent) FROM SystemSample",
  "thresholds": {"critical": 80, "warning": 60},
  "severity": "warning"
}

# List alerts
GET /api/v1/alerts?application_id={app_id}

# Batch update alerts
POST /api/v1/alerts/batch-update
{
  "filters": {"alert_type": "cpu_usage"},
  "updates": {"enabled": false}
}
```

#### Dashboards
```bash
# Create dashboard
POST /api/v1/applications/{app_id}/dashboards
{
  "name": "Infrastructure Overview",
  "type": "infrastructure",
  "widgets": [
    {
      "title": "CPU Usage",
      "visualization": "line_chart",
      "nrql": "SELECT average(cpuPercent) FROM SystemSample"
    }
  ]
}

# Add widget to dashboard
POST /api/v1/dashboards/{dashboard_id}/widgets
{
  "title": "Memory Usage",
  "visualization": "area_chart",
  "nrql": "SELECT average(memoryUsedPercent) FROM SystemSample"
}
```

#### Coverage & Compliance
```bash
# Get coverage report
GET /api/v1/coverage?application_id={app_id}

# Get compliance status
GET /api/v1/compliance?standard=enhanced

# Get recommendations
GET /api/v1/coverage/recommendations?priority=high
```

#### Deployments
```bash
# Create deployment
POST /api/v1/deploy
{
  "application_ids": ["app-123"],
  "components": ["alerts", "dashboards"],
  "dry_run": false
}

# Get deployment status
GET /api/v1/deployments/{deployment_id}

# Get deployment summary
GET /api/v1/deployments/summary?days=30
```

##  Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov-report=html

# Run specific test file
pytest tests/test_app.py

# Run with verbose output
pytest -v
```

### Test Structure
```
tests/
├── conftest.py          # Test configuration and fixtures
├── test_app.py          # Integration tests
├── test_auth.py         # Authentication tests
├── test_coverage.py     # Coverage scoring tests
└── performance/         # Performance tests
    └── locustfile.py
```

##  Docker Deployment

### Development
```bash
# Build and run with Docker Compose
docker-compose up --build

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Production
```bash
# Use production configuration
docker-compose -f docker-compose.prod.yml up -d

# Scale API service
docker-compose -f docker-compose.prod.yml up -d --scale api=4
```

### Docker Images
- Multi-stage builds for optimized production images
- Non-root user execution
- Health checks and graceful shutdowns
- Security scanning with Trivy

##  CI/CD Pipeline

### GitHub Actions Workflow
The repository includes a comprehensive CI/CD pipeline:

1. **Code Quality**: Black, isort, flake8, mypy
2. **Testing**: pytest with coverage reporting
3. **Security**: Bandit, Safety, Trivy vulnerability scanning
4. **Build**: Docker image building and pushing
5. **Deployment**: Automated deployment to staging/production

### Pipeline Stages
```yaml
lint → test → security → build → deploy-staging → deploy-production
```

##  Monitoring & Observability

### Health Checks
```bash
# Basic health check
GET /health

# Detailed health status
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:00:00Z",
  "checks": {
    "database": {"status": "healthy"},
    "memory": {"status": "healthy", "usage_percent": 45.2},
    "disk": {"status": "warning", "usage_percent": 82.1},
    "cpu": {"status": "healthy", "usage_percent": 23.5}
  }
}
```

### Metrics
```bash
# Prometheus metrics
GET /metrics

# Available metrics:
# - http_requests_total
# - http_request_duration_seconds
# - active_connections
# - cpu_usage_percent
# - memory_usage_percent
# - api_errors_total
```

### Logging
Structured JSON logging with:
- Request correlation IDs
- Performance metrics
- Error tracking
- Security events

##  Configuration

### Settings Management
Configuration is managed through `config/settings.py` using Pydantic:

```python
# Database settings
database_url: str = "postgresql://..."
database_pool_size: int = 5

# API settings
api_prefix: str = "/api/v1"
max_request_size: int = 10 * 1024 * 1024

# Security settings
access_token_expire_minutes: int = 30
algorithm: str = "HS256"

# Coverage thresholds
coverage_excellent_threshold: float = 90.0
coverage_good_threshold: float = 75.0
```

### Environment-Specific Configs
- Development: Debug mode, local database
- Staging: Production-like setup with test data
- Production: Optimized settings with monitoring

##  Security

### Authentication & Authorization
- JWT tokens with expiration
- API key management
- Role-based permissions (read, write, delete, admin)
- Password hashing with bcrypt

### Security Features
- CORS configuration
- Input validation with Pydantic
- SQL injection prevention with SQLAlchemy
- Rate limiting (configurable)
- Security headers middleware

### Security Scanning
- Automated vulnerability scanning with Trivy
- Dependency security checks with Safety
- Code security analysis with Bandit

##  Performance

### Optimization Features
- Database connection pooling
- Redis caching for frequently accessed data
- Gzip compression for API responses
- Async/await for concurrent request handling
- Database query optimization

### Performance Monitoring
- Request duration tracking
- Database query performance
- Memory and CPU usage monitoring
- Error rate tracking

##  Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Code Standards
- Follow PEP 8 style guidelines
- Use Black for code formatting
- Write comprehensive tests
- Update documentation
- Ensure all CI checks pass

##  License

This project is licensed under the MIT License - see the LICENSE file for details.

##  Support

### Documentation
- API documentation: `/docs` (Swagger UI)
- ReDoc documentation: `/redoc`
- OpenAPI spec: `/openapi.json`

### Troubleshooting
- Check health endpoint: `GET /health`
- Review application logs
- Verify database connectivity
- Check New Relic credentials

### Common Issues
1. **Database Connection**: Ensure PostgreSQL is running and credentials are correct
2. **API Key Issues**: Verify key is active and not expired
3. **New Relic Integration**: Check account ID and API key validity
4. **Performance**: Monitor memory usage and database query performance

##  Roadmap

### Upcoming Features
- [ ] Multi-tenant support
- [ ] Advanced alerting with machine learning
- [ ] Real-time dashboard updates
- [ ] GraphQL API support
- [ ] Kubernetes operator
- [ ] Terraform provider
- [ ] Webhook integrations
- [ ] Advanced analytics and reporting

### Version History
- **v2.0.0**: Complete rewrite with modern architecture
- **v1.5.0**: Added CI/CD and containerization
- **v1.0.0**: Initial release with basic functionality
