variable "app_name" {
  description = "Application name for monitoring"
  type        = string
}

variable "notification_email" {
  description = "Email address for notifications"
  type        = string
  default     = "devops@yourcompany.com"
}

variable "cpu_critical_threshold" {
  description = "CPU critical threshold percentage"
  type        = number
  default     = 80
}

variable "cpu_warning_threshold" {
  description = "CPU warning threshold percentage"
  type        = number
  default     = 60
}

variable "memory_critical_threshold" {
  description = "Memory critical threshold percentage"
  type        = number
  default     = 85
}

variable "memory_warning_threshold" {
  description = "Memory warning threshold percentage"
  type        = number
  default     = 70
}

variable "disk_critical_threshold" {
  description = "Disk critical threshold percentage"
  type        = number
  default     = 90
}

variable "disk_warning_threshold" {
  description = "Disk warning threshold percentage"
  type        = number
  default     = 75
}
