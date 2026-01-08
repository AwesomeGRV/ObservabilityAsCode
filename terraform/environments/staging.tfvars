# Staging Environment Variables

newrelic_account_id = "YOUR_STAGING_ACCOUNT_ID"
newrelic_api_key = "YOUR_STAGING_API_KEY"
newrelic_region = "US"

applications = [
  {
    name        = "e-commerce-frontend-staging"
    environment = "staging"
    entity_id   = "entity-frontend-staging-001"
  },
  {
    name        = "e-commerce-backend-staging"
    environment = "staging"
    entity_id   = "entity-backend-staging-001"
  }
]

notification_email = "devops-staging@yourcompany.com"
