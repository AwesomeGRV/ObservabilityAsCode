# Production Environment Variables

newrelic_account_id = "YOUR_PRODUCTION_ACCOUNT_ID"
newrelic_api_key = "YOUR_PRODUCTION_API_KEY"
newrelic_region = "US"

applications = [
  {
    name        = "e-commerce-frontend"
    environment = "production"
    entity_id   = "entity-frontend-001"
  },
  {
    name        = "e-commerce-backend"
    environment = "production"
    entity_id   = "entity-backend-001"
  },
  {
    name        = "payment-service"
    environment = "production"
    entity_id   = "entity-payment-001"
  },
  {
    name        = "inventory-service"
    environment = "production"
    entity_id   = "entity-inventory-001"
  },
  {
    name        = "user-service"
    environment = "production"
    entity_id   = "entity-user-001"
  },
  {
    name        = "notification-service"
    environment = "production"
    entity_id   = "entity-notification-001"
  },
  {
    name        = "analytics-service"
    environment = "production"
    entity_id   = "entity-analytics-001"
  },
  {
    name        = "search-service"
    environment = "production"
    entity_id   = "entity-search-001"
  },
  {
    name        = "order-service"
    environment = "production"
    entity_id   = "entity-order-001"
  },
  {
    name        = "shipping-service"
    environment = "production"
    entity_id   = "entity-shipping-001"
  }
]

notification_email = "devops@yourcompany.com"
