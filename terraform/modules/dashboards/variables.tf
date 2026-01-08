variable "app_name" {
  description = "Application name for dashboard"
  type        = string
}

variable "timeframe" {
  description = "Default timeframe for dashboard"
  type        = string
  default     = "1 hour"
}

variable "refresh_interval" {
  description = "Dashboard refresh interval in seconds"
  type        = number
  default     = 60
}
