# Outputs for Synthetic Monitoring Alerts Module

output "alert_condition_ids" {
  description = "List of created alert condition IDs"
  value = compact([
    var.create_availability_alerts ? newrelic_nrql_alert_condition.synthetic_availability[0].id : "",
    var.create_response_time_alerts ? newrelic_nrql_alert_condition.synthetic_response_time[0].id : "",
    var.create_location_alerts ? newrelic_nrql_alert_condition.synthetic_location_failure[0].id : "",
    var.create_error_rate_alerts ? newrelic_nrql_alert_condition.synthetic_error_rate[0].id : "",
    var.create_ssl_alerts ? newrelic_nrql_alert_condition.synthetic_ssl_expiry[0].id : "",
    var.create_business_hours_alerts ? newrelic_nrql_alert_condition.synthetic_business_hours[0].id : "",
    var.create_baseline_alerts ? newrelic_nrql_alert_condition.synthetic_baseline[0].id : ""
  ])
}

output "notification_channel_ids" {
  description = "List of created notification channel IDs"
  value = compact([
    var.create_email_channel ? newrelic_alert_channel.email[0].id : "",
    var.create_slack_channel ? newrelic_alert_channel.slack[0].id : "",
    var.create_pagerduty_channel ? newrelic_alert_channel.pagerduty[0].id : ""
  ])
}

output "availability_alert_id" {
  description = "ID of the availability alert condition"
  value = var.create_availability_alerts ? newrelic_nrql_alert_condition.synthetic_availability[0].id : null
}

output "response_time_alert_id" {
  description = "ID of the response time alert condition"
  value = var.create_response_time_alerts ? newrelic_nrql_alert_condition.synthetic_response_time[0].id : null
}

output "location_failure_alert_id" {
  description = "ID of the location failure alert condition"
  value = var.create_location_alerts ? newrelic_nrql_alert_condition.synthetic_location_failure[0].id : null
}

output "error_rate_alert_id" {
  description = "ID of the error rate alert condition"
  value = var.create_error_rate_alerts ? newrelic_nrql_alert_condition.synthetic_error_rate[0].id : null
}

output "ssl_expiry_alert_id" {
  description = "ID of the SSL expiry alert condition"
  value = var.create_ssl_alerts ? newrelic_nrql_alert_condition.synthetic_ssl_expiry[0].id : null
}

output "business_hours_alert_id" {
  description = "ID of the business hours alert condition"
  value = var.create_business_hours_alerts ? newrelic_nrql_alert_condition.synthetic_business_hours[0].id : null
}

output "baseline_alert_id" {
  description = "ID of the baseline alert condition"
  value = var.create_baseline_alerts ? newrelic_nrql_alert_condition.synthetic_baseline[0].id : null
}

output "email_channel_id" {
  description = "ID of the email notification channel"
  value = var.create_email_channel ? newrelic_alert_channel.email[0].id : null
}

output "slack_channel_id" {
  description = "ID of the Slack notification channel"
  value = var.create_slack_channel ? newrelic_alert_channel.slack[0].id : null
}

output "pagerduty_channel_id" {
  description = "ID of the PagerDuty notification channel"
  value = var.create_pagerduty_channel ? newrelic_alert_channel.pagerduty[0].id : null
}
