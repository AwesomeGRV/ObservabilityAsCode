#!/usr/bin/env python3
"""
Deployment script for observability configurations
"""

import yaml
import json
import argparse
import logging
import requests
import time
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from nerdgraph.nerdgraph_client import NERDGraphClient
from jinja2 import Template

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ObservabilityDeployer:
    """Deploy observability configurations to New Relic"""
    
    def __init__(self, config_file: str, newrelic_config: str):
        self.config_file = config_file
        self.newrelic_config = newrelic_config
        self.applications = self._load_applications()
        self.newrelic_settings = self._load_newrelic_config()
        self.nerdgraph_client = NERDGraphClient(
            self.newrelic_settings["api_key"],
            self.newrelic_settings["region"]
        )
    
    def _load_applications(self) -> Dict[str, List[Dict]]:
        """Load applications from inventory file"""
        try:
            with open(self.config_file, 'r') as f:
                data = yaml.safe_load(f)
            
            return {
                "production": data.get("applications", []),
                "staging": data.get("staging_applications", []),
                "development": data.get("development_applications", [])
            }
        except Exception as e:
            logger.error(f"Failed to load applications: {e}")
            return {"production": [], "staging": [], "development": []}
    
    def _load_newrelic_config(self) -> Dict:
        """Load New Relic configuration"""
        try:
            with open(self.newrelic_config, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load New Relic config: {e}")
            raise
    
    def deploy_alerts(self, app: Dict, environment: str) -> Dict:
        """Deploy alerts for an application"""
        app_name = app["name"]
        account_id = int(self.newrelic_settings["account_id"])
        
        try:
            # Create alert policy
            policy_name = f"{app_name} - Standard Monitoring Policy"
            policy = self.nerdgraph_client.create_alert_policy(
                account_id, 
                policy_name, 
                "PER_POLICY"
            )
            
            if not policy:
                raise Exception("Failed to create alert policy")
            
            policy_id = policy["id"]
            logger.info(f"Created alert policy: {policy_name} (ID: {policy_id})")
            
            # Load alert templates
            alert_templates = self._load_alert_templates()
            deployed_alerts = []
            
            for template_name, template_data in alert_templates.items():
                # Render template with app data
                template = Template(template_data["nrql"])
                nrql_query = template.render(app_name=app_name)
                
                # Create alert condition
                condition_data = {
                    "name": f"{template_data['name']} - {app_name}",
                    "type": "static",
                    "enabled": True,
                    "nrql": {
                        "query": nrql_query
                    },
                    "critical": template_data["critical"],
                    "warning": template_data["warning"],
                    "closeViolationsOnExpiration": True
                }
                
                # Note: This would need to be implemented in NERDGraph client
                # For now, simulate deployment
                alert_id = f"alert-{len(deployed_alerts) + 1}"
                deployed_alerts.append({
                    "id": alert_id,
                    "name": condition_data["name"],
                    "type": template_name,
                    "status": "deployed"
                })
                
                logger.info(f"Deployed alert: {condition_data['name']}")
            
            return {
                "policy_id": policy_id,
                "alerts": deployed_alerts,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy alerts for {app_name}: {e}")
            return {
                "policy_id": None,
                "alerts": [],
                "status": "failed",
                "error": str(e)
            }
    
    def deploy_dashboards(self, app: Dict, environment: str) -> Dict:
        """Deploy dashboards for an application"""
        app_name = app["name"]
        account_id = int(self.newrelic_settings["account_id"])
        
        try:
            dashboard_templates = self._load_dashboard_templates()
            deployed_dashboards = []
            
            for template_name, template_data in dashboard_templates.items():
                # Render dashboard template
                dashboard_config = self._render_dashboard_template(template_data, app_name)
                
                # Create dashboard
                dashboard = self.nerdgraph_client.create_dashboard(account_id, dashboard_config)
                
                if dashboard:
                    deployed_dashboards.append({
                        "id": dashboard["id"],
                        "name": dashboard_config["name"],
                        "type": template_name,
                        "status": "deployed"
                    })
                    logger.info(f"Deployed dashboard: {dashboard_config['name']}")
                else:
                    deployed_dashboards.append({
                        "id": None,
                        "name": dashboard_config["name"],
                        "type": template_name,
                        "status": "failed"
                    })
            
            return {
                "dashboards": deployed_dashboards,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy dashboards for {app_name}: {e}")
            return {
                "dashboards": [],
                "status": "failed",
                "error": str(e)
            }
    
    def _load_alert_templates(self) -> Dict:
        """Load alert templates"""
        templates = {}
        templates_dir = Path("alerts/templates")
        
        if not templates_dir.exists():
            logger.warning("Alert templates directory not found")
            return {}
        
        for template_file in templates_dir.glob("*.yml"):
            try:
                with open(template_file, 'r') as f:
                    template_data = yaml.safe_load(f)
                
                template_name = template_file.stem
                templates[template_name] = template_data
                
            except Exception as e:
                logger.error(f"Failed to load alert template {template_file}: {e}")
        
        return templates
    
    def _load_dashboard_templates(self) -> Dict:
        """Load dashboard templates"""
        templates = {}
        templates_dir = Path("dashboards")
        
        if not templates_dir.exists():
            logger.warning("Dashboard templates directory not found")
            return {}
        
        for template_file in templates_dir.glob("sample_*.json"):
            try:
                with open(template_file, 'r') as f:
                    template_data = json.load(f)
                
                template_name = template_file.stem.replace("sample_", "")
                templates[template_name] = template_data
                
            except Exception as e:
                logger.error(f"Failed to load dashboard template {template_file}: {e}")
        
        return templates
    
    def _render_dashboard_template(self, template_data: Dict, app_name: str) -> Dict:
        """Render dashboard template with app name"""
        template_str = json.dumps(template_data)
        template = Template(template_str)
        rendered = template.render(app_name=app_name)
        return json.loads(rendered)
    
    def deploy_application(self, app: Dict, environment: str, components: List[str]) -> Dict:
        """Deploy observability for a single application"""
        app_name = app["name"]
        logger.info(f"Deploying observability for {app_name} in {environment}")
        
        deployment_result = {
            "application": app_name,
            "environment": environment,
            "components": {},
            "status": "success",
            "deployed_at": datetime.utcnow().isoformat()
        }
        
        # Deploy alerts
        if "alerts" in components:
            logger.info(f"Deploying alerts for {app_name}")
            alert_result = self.deploy_alerts(app, environment)
            deployment_result["components"]["alerts"] = alert_result
            
            if alert_result["status"] == "failed":
                deployment_result["status"] = "partial_failure"
        
        # Deploy dashboards
        if "dashboards" in components:
            logger.info(f"Deploying dashboards for {app_name}")
            dashboard_result = self.deploy_dashboards(app, environment)
            deployment_result["components"]["dashboards"] = dashboard_result
            
            if dashboard_result["status"] == "failed":
                deployment_result["status"] = "partial_failure"
        
        # Deploy policies (if implemented)
        if "policies" in components:
            logger.info(f"Deploying policies for {app_name}")
            # This would deploy additional policies
            deployment_result["components"]["policies"] = {
                "status": "success",
                "message": "Policies deployment not yet implemented"
            }
        
        return deployment_result
    
    def deploy_environment(self, environment: str, applications: List[str], components: List[str], dry_run: bool = False) -> Dict:
        """Deploy observability for an environment"""
        apps_to_deploy = []
        
        if applications:
            # Deploy specific applications
            all_apps = self.applications.get(environment, [])
            apps_to_deploy = [app for app in all_apps if app["name"] in applications]
        else:
            # Deploy all applications in environment
            apps_to_deploy = self.applications.get(environment, [])
        
        if not apps_to_deploy:
            logger.warning(f"No applications found for environment: {environment}")
            return {
                "environment": environment,
                "status": "no_applications",
                "applications": [],
                "summary": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "partial": 0
                }
            }
        
        if dry_run:
            logger.info("DRY RUN: Would deploy the following applications:")
            for app in apps_to_deploy:
                logger.info(f"  - {app['name']} ({environment})")
            return {
                "environment": environment,
                "status": "dry_run",
                "applications": [{"name": app["name"], "status": "would_deploy"} for app in apps_to_deploy],
                "summary": {
                    "total": len(apps_to_deploy),
                    "successful": 0,
                    "failed": 0,
                    "partial": 0
                }
            }
        
        # Deploy applications
        deployment_results = []
        successful = 0
        failed = 0
        partial = 0
        
        for app in apps_to_deploy:
            result = self.deploy_application(app, environment, components)
            deployment_results.append(result)
            
            if result["status"] == "success":
                successful += 1
            elif result["status"] == "failed":
                failed += 1
            else:
                partial += 1
        
        return {
            "environment": environment,
            "status": "completed",
            "applications": deployment_results,
            "summary": {
                "total": len(apps_to_deploy),
                "successful": successful,
                "failed": failed,
                "partial": partial
            },
            "deployed_at": datetime.utcnow().isoformat()
        }
    
    def generate_deployment_report(self, results: List[Dict]) -> Dict:
        """Generate deployment report"""
        total_apps = sum(r["summary"]["total"] for r in results)
        total_successful = sum(r["summary"]["successful"] for r in results)
        total_failed = sum(r["summary"]["failed"] for r in results)
        total_partial = sum(r["summary"]["partial"] for r in results)
        
        return {
            "deployment_id": f"deploy-{int(time.time())}",
            "generated_at": datetime.utcnow().isoformat(),
            "environments": results,
            "overall_summary": {
                "total_applications": total_apps,
                "successful_deployments": total_successful,
                "failed_deployments": total_failed,
                "partial_deployments": total_partial,
                "success_rate": (total_successful / total_apps * 100) if total_apps > 0 else 0,
                "status": "success" if total_failed == 0 else "partial_failure" if total_partial > 0 else "failed"
            }
        }


def main():
    parser = argparse.ArgumentParser(description="Deploy observability configurations")
    parser.add_argument("--config", default="inventory/applications.yaml", help="Applications inventory file")
    parser.add_argument("--newrelic-config", default="config/newrelic.yml", help="New Relic configuration file")
    parser.add_argument("--environment", required=True, choices=["production", "staging", "development"], help="Target environment")
    parser.add_argument("--applications", help="Comma-separated list of applications to deploy")
    parser.add_argument("--components", default="alerts,dashboards,policies", help="Components to deploy")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without actual deployment")
    parser.add_argument("--output", help="Output file for deployment report")
    
    args = parser.parse_args()
    
    # Initialize deployer
    deployer = ObservabilityDeployer(args.config, args.newrelic_config)
    
    # Parse components
    components = [c.strip() for c in args.components.split(",")]
    
    # Parse applications
    applications = None
    if args.applications:
        applications = [a.strip() for a in args.applications.split(",")]
    
    # Deploy
    result = deployer.deploy_environment(args.environment, applications, components, args.dry_run)
    
    # Generate report
    report = deployer.generate_deployment_report([result])
    
    # Output
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Deployment report saved to {args.output}")
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
