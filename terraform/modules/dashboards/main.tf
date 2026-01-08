resource "newrelic_dashboard" "standard_dashboard" {
  name = "${var.app_name} - Standard Monitoring Dashboard"
  
  widget {
    title         = "CPU Usage"
    visualization = "facet_table"
    row           = 1
    column        = 1
    width         = 2
    height        = 2
    
    nrql_query {
      query = "SELECT average(cpuPercent) FROM SystemSample WHERE entity.name = '${var.app_name}' TIMESERIES AUTO"
    }
  }

  widget {
    title         = "Memory Usage"
    visualization = "facet_table"
    row           = 1
    column        = 3
    width         = 2
    height        = 2
    
    nrql_query {
      query = "SELECT average(memoryUsedPercent) FROM SystemSample WHERE entity.name = '${var.app_name}' TIMESERIES AUTO"
    }
  }

  widget {
    title         = "Disk Usage"
    visualization = "facet_table"
    row           = 1
    column        = 5
    width         = 2
    height        = 2
    
    nrql_query {
      query = "SELECT average(diskUsedPercent) FROM StorageSample WHERE entity.name = '${var.app_name}' TIMESERIES AUTO"
    }
  }

  widget {
    title         = "Response Time (95th percentile)"
    visualization = "line_chart"
    row           = 3
    column        = 1
    width         = 3
    height        = 2
    
    nrql_query {
      query = "SELECT percentile(duration, 95) FROM Transaction WHERE appName = '${var.app_name}' TIMESERIES AUTO"
    }
  }

  widget {
    title         = "Throughput (RPM)"
    visualization = "line_chart"
    row           = 3
    column        = 4
    width         = 3
    height        = 2
    
    nrql_query {
      query = "SELECT count(*) FROM Transaction WHERE appName = '${var.app_name}' TIMESERIES AUTO"
    }
  }

  widget {
    title         = "Error Rate"
    visualization = "line_chart"
    row           = 5
    column        = 1
    width         = 3
    height        = 2
    
    nrql_query {
      query = "SELECT percentage(count(*), WHERE error IS true) FROM Transaction WHERE appName = '${var.app_name}' TIMESERIES AUTO"
    }
  }

  widget {
    title         = "Apdex Score"
    visualization = "line_chart"
    row           = 5
    column        = 4
    width         = 3
    height        = 2
    
    nrql_query {
      query = "SELECT apdex(duration, t: 0.5) FROM Transaction WHERE appName = '${var.app_name}' TIMESERIES AUTO"
    }
  }

  widget {
    title         = "Running Pods"
    visualization = "billboard"
    row           = 7
    column        = 1
    width         = 2
    height        = 2
    
    nrql_query {
      query = "SELECT count(*) FROM K8sPodSample WHERE appName = '${var.app_name}' AND phase = 'Running'"
    }
  }

  widget {
    title         = "Pod Restarts"
    visualization = "line_chart"
    row           = 7
    column        = 3
    width         = 2
    height        = 2
    
    nrql_query {
      query = "SELECT sum(kubernetes.pod.restartCount) FROM K8sPodSample WHERE appName = '${var.app_name}' TIMESERIES AUTO"
    }
  }

  widget {
    title         = "Database Response Time"
    visualization = "line_chart"
    row           = 7
    column        = 5
    width         = 2
    height        = 2
    
    nrql_query {
      query = "SELECT average(duration) FROM DatastoreSample WHERE appName = '${var.app_name}' TIMESERIES AUTO"
    }
  }
}
