variable "app_name" {
  description = "Application name for monitoring"
  type        = string
}

variable "environment" {
  description = "Application environment"
  type        = string
}

variable "entity_id" {
  description = "New Relic entity ID"
  type        = string
}

variable "notification_email" {
  description = "Email for notifications"
  type        = string
}
