# Observability as Code for New Relic

This repository provides a comprehensive observability-as-code solution for managing New Relic monitoring configurations across multiple applications.

## Features

- **Standardized Alert Templates**: Pre-configured alerts for CPU, Memory, Disk, Pods, Latency, and Web Response metrics
- **Dashboard Templates**: Consistent dashboards for all monitored applications
- **Application Inventory**: Track which applications are fully onboarded
- **Compliance Checker**: Verify all applications have correct alerts and dashboards
- **Production Ready**: Automated deployment and validation scripts

## Structure

```
├── alerts/                 # Alert condition templates
├── dashboards/            # Dashboard templates
├── applications/          # Application-specific configurations
├── scripts/               # Deployment and management scripts
├── inventory/             # Application inventory and compliance
└── docs/                  # Documentation
```

## Quick Start

1. **Configure New Relic credentials:**
   ```bash
   cp config/newrelic.yml.example config/newrelic.yml
   # Edit config/newrelic.yml with your credentials
   ```

2. **Define your applications:**
   ```bash
   # Edit inventory/applications.yaml with your application details
   ```

3. **Start the API server:**
   ```bash
   # Option 1: Direct Python
   pip install -r requirements.txt
   python api/app.py
   
   # Option 2: Docker
   docker-compose up api
   ```

4. **Run compliance checker:**
   ```bash
   python scripts/check_compliance.py --api-url http://localhost:8000 --api-key your-key
   ```

5. **Deploy configurations:**
   ```bash
   python scripts/deploy.py --environment production
   ```

## Architecture Overview

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
                    └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Coverage       │    │  NERDGraph      │    │  Compliance     │
│  Scoring       │    │  Client         │    │  Checker       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   New Relic     │
                    │   Platform      │
                    └─────────────────┘
```

## Requirements

- Python 3.8+
- New Relic Account ID and API Key
- Docker (optional, for containerized deployment)
- Jenkins (optional, for CI/CD integration)
- Terraform (optional, for infrastructure deployment)

## Features

### Standardized Monitoring Templates
- **Alert Templates**: Pre-configured alerts for CPU, Memory, Disk, Pods, Latency, and Web Response metrics
- **Dashboard Templates**: Consistent dashboards for Infrastructure, Application Performance, Kubernetes, and Error Analysis
- **Customizable**: Easy to modify thresholds and configurations per application

### Coverage Scoring Algorithm
- **Automated Scoring**: Calculates observability coverage percentage (0-100%)
- **Compliance Levels**: Excellent (90%+), Good (75%+), Fair (60%+), Poor (40%+), Critical (<40%)
- **Gap Analysis**: Identifies missing alerts, dashboards, and monitoring components
- **Recommendations**: Provides actionable insights for improvement

### Infrastructure as Code
- **Terraform Modules**: Reusable Terraform modules for New Relic resources
- **NERDGraph Queries**: Comprehensive GraphQL queries for New Relic API interactions
- **Version Control**: All configurations stored in Git for audit trails

### CI/CD Integration
- **Jenkins Pipeline**: Automated deployment with approval gates
- **Validation**: Pre-deployment compliance and coverage checks
- **Rollback**: Automated rollback capabilities for failed deployments
- **Multi-Environment**: Support for production, staging, and development environments

### REST API
- **OpenAPI Specification**: Complete API contract with documentation
- **Application Management**: CRUD operations for application inventory
- **Deployment API**: Programmatic deployment of observability configurations
- **Reporting API**: Coverage and compliance reporting endpoints

### Container Support
- **Docker Compose**: Complete stack with API, Redis, PostgreSQL, Grafana, and Prometheus
- **Health Checks**: Built-in health monitoring for all services
- **Scalable**: Easy to scale and deploy in containerized environments

## Key Components

### Alert Templates
- CPU Usage (Critical: 80%, Warning: 60%)
- Memory Usage (Critical: 85%, Warning: 70%)
- Disk Usage (Critical: 90%, Warning: 75%)
- Response Time (Critical: 2s, Warning: 1s)
- Error Rate (Critical: 5%, Warning: 2%)
- Pod Health (Critical: 5 restarts, Warning: 2 restarts)

### Dashboard Types
- **Infrastructure Monitoring**: CPU, Memory, Disk, Network, Load Average
- **Application Performance**: Response Time, Throughput, Error Rate, Apdex
- **Kubernetes Monitoring**: Pod Status, Resource Usage, Cluster Health
- **Error Analysis**: Error Types, Error Rates, Browser Errors, HTTP Status Codes

### Compliance Standards
- CPU Monitoring
- Memory Monitoring
- Disk Monitoring
- Response Time Monitoring
- Error Monitoring
- Infrastructure Dashboard
- Application Dashboard
- Error Dashboard
- Alert Policy
- Notification Channel
