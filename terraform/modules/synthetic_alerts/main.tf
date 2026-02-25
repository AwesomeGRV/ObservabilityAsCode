# Synthetic Monitoring Alerts Terraform Module

terraform {
  required_version = ">= 1.0"
  required_providers {
    newrelic = {
      source  = "newrelic/newrelic"
      version = "~> 3.0"
    }
  }
}

# Synthetic Monitor Availability Alert
resource "newrelic_nrql_alert_condition" "synthetic_availability" {
  count = var.create_availability_alerts ? 1 : 0
  
  policy_id = var.alert_policy_id
  name      = "${var.name_prefix} - Synthetic Monitor Availability"
  type      = "static"
  enabled   = true
  
  nrql {
    query = "SELECT percentage(count(*), WHERE result = 'SUCCESS') FROM SyntheticCheck WHERE monitorName LIKE '%${var.monitor_name_pattern}%'"
  }
  
  critical {
    operator              = "below"
    threshold             = var.availability_critical_threshold
    threshold_duration    = var.availability_critical_duration
    threshold_occurrences = "at_least_once"
  }
  
  warning {
    operator              = "below"
    threshold             = var.availability_warning_threshold
    threshold_duration    = var.availability_warning_duration
    threshold_occurrences = "at_least_once"
  }
  
  fill_option        = "static"
  fill_value         = 100
  aggregation_window = var.aggregation_window
  
  description = "Alert when synthetic monitor availability falls below threshold"
}

# Synthetic Monitor Response Time Alert
resource "newrelic_nrql_alert_condition" "synthetic_response_time" {
  count = var.create_response_time_alerts ? 1 : 0
  
  policy_id = var.alert_policy_id
  name      = "${var.name_prefix} - Synthetic Monitor Response Time"
  type      = "static"
  enabled   = true
  
  nrql {
    query = "SELECT average(duration) FROM SyntheticCheck WHERE result = 'SUCCESS' AND monitorName LIKE '%${var.monitor_name_pattern}%'"
  }
  
  critical {
    operator              = "above"
    threshold             = var.response_time_critical_threshold
    threshold_duration    = var.response_time_critical_duration
    threshold_occurrences = "at_least_once"
  }
  
  warning {
    operator              = "above"
    threshold             = var.response_time_warning_threshold
    threshold_duration    = var.response_time_warning_duration
    threshold_occurrences = "at_least_once"
  }
  
  fill_option        = "static"
  fill_value         = 0
  aggregation_window = var.aggregation_window
  
  description = "Alert when synthetic monitor response time exceeds threshold"
}

# Synthetic Monitor Location Failure Alert
resource "newrelic_nrql_alert_condition" "synthetic_location_failure" {
  count = var.create_location_alerts ? 1 : 0
  
  policy_id = var.alert_policy_id
  name      = "${var.name_prefix} - Synthetic Monitor Location Failure"
  type      = "static"
  enabled   = true
  
  nrql {
    query = "SELECT percentage(count(*), WHERE result = 'SUCCESS') FROM SyntheticCheck WHERE monitorName LIKE '%${var.monitor_name_pattern}%' FACET location"
  }
  
  critical {
    operator              = "below"
    threshold             = var.location_critical_threshold
    threshold_duration    = var.location_critical_duration
    threshold_occurrences = "at_least_once"
  }
  
  warning {
    operator              = "below"
    threshold             = var.location_warning_threshold
    threshold_duration    = var.location_warning_duration
    threshold_occurrences = "at_least_once"
  }
  
  fill_option        = "static"
  fill_value         = 100
  aggregation_window = var.aggregation_window
  
  description = "Alert when synthetic monitor fails from specific location"
}

# Synthetic Monitor Error Rate Alert
resource "newrelic_nrql_alert_condition" "synthetic_error_rate" {
  count = var.create_error_rate_alerts ? 1 : 0
  
  policy_id = var.alert_policy_id
  name      = "${var.name_prefix} - Synthetic Monitor Error Rate"
  type      = "static"
  enabled   = true
  
  nrql {
    query = "SELECT percentage(count(*), WHERE result = 'FAILED') FROM SyntheticCheck WHERE monitorName LIKE '%${var.monitor_name_pattern}%'"
  }
  
  critical {
    operator              = "above"
    threshold             = var.error_rate_critical_threshold
    threshold_duration    = var.error_rate_critical_duration
    threshold_occurrences = "at_least_once"
  }
  
  warning {
    operator              = "above"
    threshold             = var.error_rate_warning_threshold
    threshold_duration    = var.error_rate_warning_duration
    threshold_occurrences = "at_least_once"
  }
  
  fill_option        = "static"
  fill_value         = 0
  aggregation_window = var.aggregation_window
  
  description = "Alert when synthetic monitor error rate exceeds threshold"
}

# Synthetic Monitor SSL Certificate Alert
resource "newrelic_nrql_alert_condition" "synthetic_ssl_expiry" {
  count = var.create_ssl_alerts ? 1 : 0
  
  policy_id = var.alert_policy_id
  name      = "${var.name_prefix} - Synthetic Monitor SSL Certificate Expiry"
  type      = "static"
  enabled   = true
  
  nrql {
    query = "SELECT average(daysUntilExpiry) FROM SyntheticCheck WHERE checkType = 'SSL' AND monitorName LIKE '%${var.monitor_name_pattern}%'"
  }
  
  critical {
    operator              = "below"
    threshold             = var.ssl_critical_threshold
    threshold_duration    = var.ssl_critical_duration
    threshold_occurrences = "at_least_once"
  }
  
  warning {
    operator              = "below"
    threshold             = var.ssl_warning_threshold
    threshold_duration    = var.ssl_warning_duration
    threshold_occurrences = "at_least_once"
  }
  
  fill_option        = "static"
  fill_value         = 365
  aggregation_window = var.aggregation_window
  
  description = "Alert when SSL certificate is expiring"
}

# Synthetic Monitor Business Hours Alert
resource "newrelic_nrql_alert_condition" "synthetic_business_hours" {
  count = var.create_business_hours_alerts ? 1 : 0
  
  policy_id = var.alert_policy_id
  name      = "${var.name_prefix} - Synthetic Monitor Business Hours"
  type      = "static"
  enabled   = true
  
  nrql {
    query = "SELECT percentage(count(*), WHERE result = 'SUCCESS') FROM SyntheticCheck WHERE monitorName LIKE '%${var.monitor_name_pattern}%' AND hourOf(timestamp) >= ${var.business_hours_start} AND hourOf(timestamp) <= ${var.business_hours_end}"
  }
  
  critical {
    operator              = "below"
    threshold             = var.business_hours_critical_threshold
    threshold_duration    = var.business_hours_critical_duration
    threshold_occurrences = "at_least_once"
  }
  
  warning {
    operator              = "below"
    threshold             = var.business_hours_warning_threshold
    threshold_duration    = var.business_hours_warning_duration
    threshold_occurrences = "at_least_once"
  }
  
  fill_option        = "static"
  fill_value         = 100
  aggregation_window = var.aggregation_window
  
  description = "Alert when synthetic monitor fails during business hours"
}

# Synthetic Monitor Baseline Performance Alert
resource "newrelic_nrql_alert_condition" "synthetic_baseline" {
  count = var.create_baseline_alerts ? 1 : 0
  
  policy_id = var.alert_policy_id
  name      = "${var.name_prefix} - Synthetic Monitor Baseline Performance"
  type      = "baseline"
  enabled   = true
  
  nrql {
    query = "SELECT average(duration) FROM SyntheticCheck WHERE result = 'SUCCESS' AND monitorName LIKE '%${var.monitor_name_pattern}%'"
  }
  
  critical {
    operator              = "above"
    threshold             = var.baseline_critical_threshold
    threshold_duration    = var.baseline_critical_duration
    threshold_occurrences = "at_least_once"
  }
  
  warning {
    operator              = "above"
    threshold             = var.baseline_warning_threshold
    threshold_duration    = var.baseline_warning_duration
    threshold_occurrences = "at_least_once"
  }
  
  baseline_direction = "upper_only"
  
  description = "Alert when synthetic monitor performance deviates from baseline"
}

# Notification Channels
resource "newrelic_alert_channel" "email" {
  count = var.create_email_channel ? 1 : 0
  
  name = "${var.name_prefix} - Email Notifications"
  type = "email"
  
  config {
    recipients              = var.email_recipients
    include_json_attachment = "1"
  }
}

resource "newrelic_alert_channel" "slack" {
  count = var.create_slack_channel ? 1 : 0
  
  name = "${var.name_prefix} - Slack Notifications"
  type = "slack"
  
  config {
    url             = var.slack_webhook_url
    channel         = var.slack_channel
    include_json_attachment = "1"
  }
}

resource "newrelic_alert_channel" "pagerduty" {
  count = var.create_pagerduty_channel ? 1 : 0
  
  name = "${var.name_prefix} - PagerDuty Notifications"
  type = "pagerduty"
  
  config {
    service_key = var.pagerduty_service_key
  }
}

# Alert Policy and Channel Association
resource "newrelic_alert_policy_channel" "main" {
  policy_id  = var.alert_policy_id
  channel_ids = compact([
    var.create_email_channel ? newrelic_alert_channel.email[0].id : "",
    var.create_slack_channel ? newrelic_alert_channel.slack[0].id : "",
    var.create_pagerduty_channel ? newrelic_alert_channel.pagerduty[0].id : ""
  ])
}
