terraform {
  required_providers {
    newrelic = {
      source  = "newrelic/newrelic"
      version = "~> 3.0"
    }
  }
  required_version = ">= 1.0"
}

provider "newrelic" {
  account_id = var.newrelic_account_id
  api_key    = var.newrelic_api_key
  region     = var.newrelic_region
}

# Variables
variable "newrelic_account_id" {
  description = "New Relic Account ID"
  type        = string
}

variable "newrelic_api_key" {
  description = "New Relic API Key"
  type        = string
  sensitive   = true
}

variable "newrelic_region" {
  description = "New Relic Region (US or EU)"
  type        = string
  default     = "US"
}

variable "applications" {
  description = "List of applications to monitor"
  type = list(object({
    name        = string
    environment = string
    entity_id   = string
  }))
}

variable "notification_email" {
  description = "Email for notifications"
  type        = string
  default     = "devops@yourcompany.com"
}

# Deploy alerts and dashboards for each application
module "observability" {
  for_each = { for app in var.applications : app.name => app }
  source   = "./modules"
  
  app_name           = each.value.name
  environment        = each.value.environment
  entity_id         = each.value.entity_id
  notification_email = var.notification_email
}
