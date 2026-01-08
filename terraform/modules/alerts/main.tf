# Alert Policy Module
resource "newrelic_alert_policy" "standard_policy" {
  name = "${var.app_name} - Standard Monitoring Policy"
  incident_preference = "PER_POLICY"
}

# CPU Usage Alert
resource "newrelic_nrql_alert_condition" "cpu_high" {
  policy_id = newrelic_alert_policy.standard_policy.id
  name      = "High CPU Usage - ${var.app_name}"
  type      = "static"
  enabled   = true

  nrql {
    query = "SELECT average(cpuPercent) FROM SystemSample WHERE entity.name = '${var.app_name}'"
  }

  critical {
    operator              = "above"
    threshold             = 80
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }

  warning {
    operator              = "above"
    threshold             = 60
    threshold_duration    = 600
    threshold_occurrences = "at_least_once"
  }

  close_violations_on_expiration = true
}

# Memory Usage Alert
resource "newrelic_nrql_alert_condition" "memory_high" {
  policy_id = newrelic_alert_policy.standard_policy.id
  name      = "High Memory Usage - ${var.app_name}"
  type      = "static"
  enabled   = true

  nrql {
    query = "SELECT average(memoryUsedPercent) FROM SystemSample WHERE entity.name = '${var.app_name}'"
  }

  critical {
    operator              = "above"
    threshold             = 85
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }

  warning {
    operator              = "above"
    threshold             = 70
    threshold_duration    = 600
    threshold_occurrences = "at_least_once"
  }

  close_violations_on_expiration = true
}

# Disk Usage Alert
resource "newrelic_nrql_alert_condition" "disk_high" {
  policy_id = newrelic_alert_policy.standard_policy.id
  name      = "High Disk Usage - ${var.app_name}"
  type      = "static"
  enabled   = true

  nrql {
    query = "SELECT average(diskUsedPercent) FROM StorageSample WHERE entity.name = '${var.app_name}'"
  }

  critical {
    operator              = "above"
    threshold             = 90
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }

  warning {
    operator              = "above"
    threshold             = 75
    threshold_duration    = 600
    threshold_occurrences = "at_least_once"
  }

  close_violations_on_expiration = true
}

# Response Time Alert
resource "newrelic_nrql_alert_condition" "response_time_high" {
  policy_id = newrelic_alert_policy.standard_policy.id
  name      = "High Response Time - ${var.app_name}"
  type      = "static"
  enabled   = true

  nrql {
    query = "SELECT percentile(duration, 95) FROM Transaction WHERE appName = '${var.app_name}'"
  }

  critical {
    operator              = "above"
    threshold             = 2000
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }

  warning {
    operator              = "above"
    threshold             = 1000
    threshold_duration    = 600
    threshold_occurrences = "at_least_once"
  }

  close_violations_on_expiration = true
}

# Error Rate Alert
resource "newrelic_nrql_alert_condition" "error_rate_high" {
  policy_id = newrelic_alert_policy.standard_policy.id
  name      = "High Error Rate - ${var.app_name}"
  type      = "static"
  enabled   = true

  nrql {
    query = "SELECT percentage(count(*), WHERE error IS true) FROM Transaction WHERE appName = '${var.app_name}'"
  }

  critical {
    operator              = "above"
    threshold             = 5
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }

  warning {
    operator              = "above"
    threshold             = 2
    threshold_duration    = 600
    threshold_occurrences = "at_least_once"
  }

  close_violations_on_expiration = true
}

# Pod Restart Alert
resource "newrelic_nrql_alert_condition" "pod_restarts" {
  policy_id = newrelic_alert_policy.standard_policy.id
  name      = "Pod Restarts - ${var.app_name}"
  type      = "static"
  enabled   = true

  nrql {
    query = "SELECT count(kubernetes.pod.restartCount) FROM K8sPodSample WHERE appName = '${var.app_name}'"
  }

  critical {
    operator              = "above"
    threshold             = 5
    threshold_duration    = 300
    threshold_occurrences = "at_least_once"
  }

  warning {
    operator              = "above"
    threshold             = 2
    threshold_duration    = 600
    threshold_occurrences = "at_least_once"
  }

  close_violations_on_expiration = true
}
