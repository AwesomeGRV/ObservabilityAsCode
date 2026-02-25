# Variables for Synthetic Monitoring Alerts Module

variable "alert_policy_id" {
  description = "ID of the New Relic alert policy"
  type        = string
}

variable "name_prefix" {
  description = "Prefix for alert names"
  type        = string
  default     = "Synthetic"
}

variable "monitor_name_pattern" {
  description = "Pattern to match synthetic monitor names"
  type        = string
  default     = ""
}

# Alert toggles
variable "create_availability_alerts" {
  description = "Create availability alerts"
  type        = bool
  default     = true
}

variable "create_response_time_alerts" {
  description = "Create response time alerts"
  type        = bool
  default     = true
}

variable "create_location_alerts" {
  description = "Create location-specific alerts"
  type        = bool
  default     = true
}

variable "create_error_rate_alerts" {
  description = "Create error rate alerts"
  type        = bool
  default     = true
}

variable "create_ssl_alerts" {
  description = "Create SSL certificate alerts"
  type        = bool
  default     = false
}

variable "create_business_hours_alerts" {
  description = "Create business hours alerts"
  type        = bool
  default     = false
}

variable "create_baseline_alerts" {
  description = "Create baseline performance alerts"
  type        = bool
  default     = false
}

# Availability thresholds
variable "availability_critical_threshold" {
  description = "Critical threshold for availability (percentage)"
  type        = number
  default     = 95
}

variable "availability_critical_duration" {
  description = "Critical threshold duration in seconds"
  type        = number
  default     = 300
}

variable "availability_warning_threshold" {
  description = "Warning threshold for availability (percentage)"
  type        = number
  default     = 98
}

variable "availability_warning_duration" {
  description = "Warning threshold duration in seconds"
  type        = number
  default     = 600
}

# Response time thresholds
variable "response_time_critical_threshold" {
  description = "Critical threshold for response time (seconds)"
  type        = number
  default     = 10.0
}

variable "response_time_critical_duration" {
  description = "Critical threshold duration in seconds"
  type        = number
  default     = 300
}

variable "response_time_warning_threshold" {
  description = "Warning threshold for response time (seconds)"
  type        = number
  default     = 5.0
}

variable "response_time_warning_duration" {
  description = "Warning threshold duration in seconds"
  type        = number
  default     = 600
}

# Location failure thresholds
variable "location_critical_threshold" {
  description = "Critical threshold for location availability (percentage)"
  type        = number
  default     = 90
}

variable "location_critical_duration" {
  description = "Critical threshold duration in seconds"
  type        = number
  default     = 600
}

variable "location_warning_threshold" {
  description = "Warning threshold for location availability (percentage)"
  type        = number
  default     = 95
}

variable "location_warning_duration" {
  description = "Warning threshold duration in seconds"
  type        = number
  default     = 900
}

# Error rate thresholds
variable "error_rate_critical_threshold" {
  description = "Critical threshold for error rate (percentage)"
  type        = number
  default     = 10.0
}

variable "error_rate_critical_duration" {
  description = "Critical threshold duration in seconds"
  type        = number
  default     = 300
}

variable "error_rate_warning_threshold" {
  description = "Warning threshold for error rate (percentage)"
  type        = number
  default     = 5.0
}

variable "error_rate_warning_duration" {
  description = "Warning threshold duration in seconds"
  type        = number
  default     = 600
}

# SSL certificate thresholds
variable "ssl_critical_threshold" {
  description = "Critical threshold for SSL certificate expiry (days)"
  type        = number
  default     = 7
}

variable "ssl_critical_duration" {
  description = "Critical threshold duration in seconds"
  type        = number
  default     = 300
}

variable "ssl_warning_threshold" {
  description = "Warning threshold for SSL certificate expiry (days)"
  type        = number
  default     = 30
}

variable "ssl_warning_duration" {
  description = "Warning threshold duration in seconds"
  type        = number
  default     = 3600
}

# Business hours thresholds
variable "business_hours_start" {
  description = "Business hours start (24-hour format)"
  type        = number
  default     = 9
}

variable "business_hours_end" {
  description = "Business hours end (24-hour format)"
  type        = number
  default     = 17
}

variable "business_hours_critical_threshold" {
  description = "Critical threshold for business hours availability (percentage)"
  type        = number
  default     = 99
}

variable "business_hours_critical_duration" {
  description = "Critical threshold duration in seconds"
  type        = number
  default     = 300
}

variable "business_hours_warning_threshold" {
  description = "Warning threshold for business hours availability (percentage)"
  type        = number
  default     = 95
}

variable "business_hours_warning_duration" {
  description = "Warning threshold duration in seconds"
  type        = number
  default     = 600
}

# Baseline thresholds
variable "baseline_critical_threshold" {
  description = "Critical threshold for baseline deviation (percentage)"
  type        = number
  default     = 50
}

variable "baseline_critical_duration" {
  description = "Critical threshold duration in seconds"
  type        = number
  default     = 600
}

variable "baseline_warning_threshold" {
  description = "Warning threshold for baseline deviation (percentage)"
  type        = number
  default     = 25
}

variable "baseline_warning_duration" {
  description = "Warning threshold duration in seconds"
  type        = number
  default     = 900
}

# General settings
variable "aggregation_window" {
  description = "Aggregation window for alerts in seconds"
  type        = number
  default     = 60
}

# Notification channels
variable "create_email_channel" {
  description = "Create email notification channel"
  type        = bool
  default     = true
}

variable "create_slack_channel" {
  description = "Create Slack notification channel"
  type        = bool
  default     = false
}

variable "create_pagerduty_channel" {
  description = "Create PagerDuty notification channel"
  type        = bool
  default     = false
}

variable "email_recipients" {
  description = "List of email recipients for alerts"
  type        = list(string)
  default     = []
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications"
  type        = string
  default     = ""
}

variable "slack_channel" {
  description = "Slack channel for notifications"
  type        = string
  default     = "#alerts"
}

variable "pagerduty_service_key" {
  description = "PagerDuty service key for notifications"
  type        = string
  default     = ""
}
