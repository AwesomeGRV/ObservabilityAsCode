# Deployment Guide

This guide provides step-by-step instructions for deploying the observability-as-code solution.

## Prerequisites

- Python 3.8+
- New Relic Account with API access
- Jenkins server (for CI/CD integration)
- Terraform (optional, for infrastructure deployment)

## Quick Setup

### 1. Configure New Relic

Edit `config/newrelic.yml` with your New Relic credentials:

```yaml
account_id: "YOUR_ACCOUNT_ID"
api_key: "YOUR_API_KEY"
region: "US"  # or "EU"
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Applications

Edit `inventory/applications.yaml` to define your applications:

```yaml
applications:
  - name: "my-app"
    environment: "production"
    entity_id: "entity-123"
    team: "My Team"
    criticality: "high"
```

## Deployment Methods

### Method 1: Using Python Scripts

#### Deploy to Environment

```bash
# Deploy all components to production
python scripts/deploy.py --environment production

# Deploy specific applications
python scripts/deploy.py --environment production --applications "app1,app2"

# Deploy specific components only
python scripts/deploy.py --environment production --components "alerts,dashboards"

# Dry run
python scripts/deploy.py --environment production --dry-run
```

#### Check Compliance

```bash
# Check all environments
python scripts/check_compliance.py --api-url http://localhost:8000 --api-key your-key

# Check specific environment
python scripts/check_compliance.py --environment production --api-url http://localhost:8000 --api-key your-key

# Save report to file
python scripts/check_compliance.py --output compliance_report.json --api-url http://localhost:8000 --api-key your-key
```

### Method 2: Using Terraform

#### Initialize Terraform

```bash
cd terraform
terraform init
```

#### Plan Deployment

```bash
terraform plan -var-file="environments/production.tfvars"
```

#### Apply Changes

```bash
terraform apply -var-file="environments/production.tfvars"
```

### Method 3: Using Jenkins CI/CD

#### Set Environment Variables

```bash
export JENKINS_URL="https://jenkins.yourcompany.com"
export JENKINS_USERNAME="your-username"
export JENKINS_API_TOKEN="your-token"
export OBSERVABILITY_API_URL="http://your-api-server:8000"
export OBSERVABILITY_API_KEY="your-api-key"
```

#### Trigger Deployment

```bash
python cicd/jenkins_integration.py deploy \
  --environment production \
  --applications "app1,app2" \
  --components "alerts,dashboards"
```

#### Validate Before Deployment

```bash
python cicd/jenkins_integration.py validate \
  --applications "app1,app2"
```

## API Server Deployment

### Start the API Server

```bash
cd api
python app.py
```

The API will be available at `http://localhost:8000`

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Monitoring the Deployment

### Check Deployment Status

```bash
# Get coverage report
curl -H "X-API-Key: your-key" http://localhost:8000/coverage

# Get compliance status
curl -H "X-API-Key: your-key" http://localhost:8000/compliance

# Get applications list
curl -H "X-API-Key: your-key" http://localhost:8000/applications
```

### Sample Dashboard URLs

After deployment, access dashboards in New Relic:

- Infrastructure Dashboard: `https://one.newrelic.com/dashboard/your-dashboard-id`
- Application Performance: `https://one.newrelic.com/dashboard/your-dashboard-id`
- Error Analysis: `https://one.newrelic.com/dashboard/your-dashboard-id`

## Troubleshooting

### Common Issues

1. **API Key Authentication Failed**
   - Verify your New Relic API key is correct
   - Check if the key has sufficient permissions

2. **Application Not Found**
   - Ensure the application exists in New Relic
   - Verify the entity ID is correct

3. **Terraform State Issues**
   - Run `terraform refresh` to sync state
   - Check `terraform.tfstate` file

4. **Jenkins Job Failures**
   - Check Jenkins job logs
   - Verify environment variables are set correctly

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python scripts/deploy.py --environment production
```

## Production Considerations

### Security

- Store API keys in secure vaults
- Use environment variables for sensitive data
- Enable API authentication

### Scalability

- Use Jenkins agents for parallel deployments
- Implement rate limiting for API calls
- Cache frequently accessed data

### Monitoring

- Monitor the deployment pipeline itself
- Set up alerts for deployment failures
- Track deployment success rates

## Rollback Procedures

### Manual Rollback

```bash
# Using Terraform
terraform destroy -var-file="environments/production.tfvars"

# Using API
curl -X POST -H "X-API-Key: your-key" \
  http://localhost:8000/deploy \
  -d '{"application_ids": ["app1"], "rollback": true}'
```

### Jenkins Rollback

```bash
python cicd/jenkins_integration.py rollback \
  --deployment-id deploy-123456
```

## Support

For issues and questions:

1. Check the logs in the respective components
2. Review the API documentation
3. Contact the DevOps team

## Next Steps

1. Set up automated monitoring for the observability system
2. Implement custom alert templates
3. Create additional dashboard templates
4. Set up automated compliance reporting
