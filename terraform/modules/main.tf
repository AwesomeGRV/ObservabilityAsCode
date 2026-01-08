# Main module that combines alerts and dashboards

module "alerts" {
  source = "./alerts"
  
  app_name           = var.app_name
  notification_email = var.notification_email
}

module "dashboards" {
  source = "./dashboards"
  
  app_name = var.app_name
}
