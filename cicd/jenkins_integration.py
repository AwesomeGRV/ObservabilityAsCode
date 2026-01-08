"""
Jenkins CI/CD Integration for Observability as Code
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import os
import time

logger = logging.getLogger(__name__)


@dataclass
class JenkinsJob:
    """Jenkins job configuration"""
    name: str
    url: str
    token: str
    parameters: Dict[str, str] = None


@dataclass
class DeploymentConfig:
    """Deployment configuration"""
    environment: str
    applications: List[str]
    components: List[str]
    dry_run: bool = False
    force: bool = False


class JenkinsClient:
    """Client for interacting with Jenkins API"""
    
    def __init__(self, jenkins_url: str, username: str, api_token: str):
        self.jenkins_url = jenkins_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.auth = (username, api_token)
        self.session = requests.Session()
        self.session.auth = self.auth
    
    def trigger_job(self, job_name: str, parameters: Dict[str, str] = None) -> Dict:
        """Trigger a Jenkins job"""
        job_url = f"{self.jenkins_url}/job/{job_name}/build"
        
        if parameters:
            # Trigger with parameters
            job_url += f"/withParameters"
            response = self.session.post(job_url, data=parameters)
        else:
            # Trigger without parameters
            response = self.session.post(job_url)
        
        if response.status_code == 201:
            # Get the build number from location header
            build_url = response.headers.get('Location', '')
            build_number = build_url.split('/')[-1] if build_url else 'unknown'
            
            return {
                "status": "triggered",
                "build_number": build_number,
                "build_url": f"{self.jenkins_url}/job/{job_name}/{build_number}"
            }
        else:
            raise Exception(f"Failed to trigger job: {response.status_code} - {response.text}")
    
    def get_build_status(self, job_name: str, build_number: int) -> Dict:
        """Get build status"""
        url = f"{self.jenkins_url}/job/{job_name}/{build_number}/api/json"
        
        response = self.session.get(url)
        if response.status_code == 200:
            build_data = response.json()
            return {
                "number": build_data.get("number"),
                "result": build_data.get("result"),
                "building": build_data.get("building", False),
                "timestamp": build_data.get("timestamp"),
                "duration": build_data.get("duration"),
                "status_url": f"{self.jenkins_url}/job/{job_name}/{build_number}"
            }
        else:
            raise Exception(f"Failed to get build status: {response.status_code}")
    
    def wait_for_completion(self, job_name: str, build_number: int, timeout: int = 1800) -> Dict:
        """Wait for job completion"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                status = self.get_build_status(job_name, build_number)
                
                if not status["building"]:
                    return status
                
                time.sleep(30)  # Wait 30 seconds before checking again
                
            except Exception as e:
                logger.error(f"Error checking build status: {e}")
                time.sleep(30)
        
        raise TimeoutError(f"Job {job_name} #{build_number} did not complete within {timeout} seconds")


class ObservabilityPipeline:
    """CI/CD pipeline for observability configurations"""
    
    def __init__(self, jenkins_client: JenkinsClient, api_base_url: str, api_key: str):
        self.jenkins_client = jenkins_client
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})
    
    def deploy_alerts_and_dashboards(self, config: DeploymentConfig) -> Dict:
        """Deploy alerts and dashboards via Jenkins pipeline"""
        
        # Prepare Jenkins job parameters
        parameters = {
            "ENVIRONMENT": config.environment,
            "APPLICATIONS": ",".join(config.applications),
            "COMPONENTS": ",".join(config.components),
            "DRY_RUN": str(config.dry_run).lower(),
            "FORCE": str(config.force).lower(),
            "API_BASE_URL": self.api_base_url,
            "API_KEY": self.api_key
        }
        
        try:
            # Trigger Jenkins job
            job_result = self.jenkins_client.trigger_job("deploy-observability", parameters)
            
            logger.info(f"Triggered Jenkins job: {job_result['build_url']}")
            
            # Wait for completion (if not dry run)
            if not config.dry_run:
                build_status = self.jenkins_client.wait_for_completion(
                    "deploy-observability", 
                    int(job_result["build_number"])
                )
                
                return {
                    "deployment_id": f"jenkins-{job_result['build_number']}",
                    "status": build_status["result"].lower(),
                    "build_url": job_result["build_url"],
                    "build_number": job_result["build_number"],
                    "completed_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "deployment_id": f"jenkins-dryrun-{job_result['build_number']}",
                    "status": "initiated",
                    "build_url": job_result["build_url"],
                    "build_number": job_result["build_number"],
                    "message": "Dry run - job triggered but not waiting for completion"
                }
                
        except Exception as e:
            logger.error(f"Failed to deploy observability configs: {e}")
            raise
    
    def validate_configurations(self, applications: List[str]) -> Dict:
        """Validate observability configurations"""
        validation_results = []
        
        for app_name in applications:
            try:
                # Get application coverage
                coverage_url = f"{self.api_base_url}/coverage"
                response = self.session.get(coverage_url, params={"applicationId": app_name})
                
                if response.status_code == 200:
                    coverage_data = response.json()
                    
                    # Get compliance status
                    compliance_url = f"{self.api_base_url}/compliance"
                    compliance_response = self.session.get(compliance_url, params={"applicationId": app_name})
                    
                    compliance_data = compliance_response.json() if compliance_response.status_code == 200 else {}
                    
                    validation_results.append({
                        "application": app_name,
                        "valid": True,
                        "coverage_score": coverage_data.get("summary", {}).get("average_coverage_score", 0),
                        "compliance_score": compliance_data.get("overall_compliance", 0),
                        "issues": []
                    })
                else:
                    validation_results.append({
                        "application": app_name,
                        "valid": False,
                        "coverage_score": 0,
                        "compliance_score": 0,
                        "issues": [f"Failed to get coverage: {response.status_code}"]
                    })
                    
            except Exception as e:
                validation_results.append({
                    "application": app_name,
                    "valid": False,
                    "coverage_score": 0,
                    "compliance_score": 0,
                    "issues": [str(e)]
                })
        
        return {
            "validation_id": f"validation-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "results": validation_results,
            "overall_valid": all(result["valid"] for result in validation_results)
        }
    
    def rollback_deployment(self, deployment_id: str) -> Dict:
        """Rollback a deployment"""
        # Extract build number from deployment ID
        if deployment_id.startswith("jenkins-"):
            build_number = deployment_id.replace("jenkins-", "").replace("jenkins-dryrun-", "")
            
            # Trigger rollback job
            parameters = {
                "BUILD_NUMBER": build_number,
                "ROLLBACK_REASON": "Manual rollback request"
            }
            
            try:
                job_result = self.jenkins_client.trigger_job("rollback-observability", parameters)
                
                return {
                    "rollback_id": f"rollback-{job_result['build_number']}",
                    "status": "initiated",
                    "build_url": job_result["build_url"],
                    "original_deployment": deployment_id
                }
                
            except Exception as e:
                logger.error(f"Failed to rollback deployment: {e}")
                raise
        else:
            raise ValueError(f"Invalid deployment ID format: {deployment_id}")


class PipelineManager:
    """Manager for observability CI/CD pipelines"""
    
    def __init__(self):
        self.jenkins_client = None
        self.pipeline = None
        self._initialize_from_env()
    
    def _initialize_from_env(self):
        """Initialize from environment variables"""
        jenkins_url = os.getenv("JENKINS_URL")
        jenkins_username = os.getenv("JENKINS_USERNAME")
        jenkins_token = os.getenv("JENKINS_API_TOKEN")
        api_base_url = os.getenv("OBSERVABILITY_API_URL")
        api_key = os.getenv("OBSERVABILITY_API_KEY")
        
        if all([jenkins_url, jenkins_username, jenkins_token]):
            self.jenkins_client = JenkinsClient(jenkins_url, jenkins_username, jenkins_token)
        
        if all([api_base_url, api_key]):
            self.pipeline = ObservabilityPipeline(
                self.jenkins_client, 
                api_base_url, 
                api_key
            )
    
    def create_deployment_pipeline(self, config: DeploymentConfig) -> Dict:
        """Create and execute deployment pipeline"""
        if not self.pipeline:
            raise RuntimeError("Pipeline not initialized. Check environment variables.")
        
        return self.pipeline.deploy_alerts_and_dashboards(config)
    
    def create_validation_pipeline(self, applications: List[str]) -> Dict:
        """Create and execute validation pipeline"""
        if not self.pipeline:
            raise RuntimeError("Pipeline not initialized. Check environment variables.")
        
        return self.pipeline.validate_configurations(applications)
    
    def create_rollback_pipeline(self, deployment_id: str) -> Dict:
        """Create and execute rollback pipeline"""
        if not self.pipeline:
            raise RuntimeError("Pipeline not initialized. Check environment variables.")
        
        return self.pipeline.rollback_deployment(deployment_id)


# CLI Interface
def main():
    """CLI interface for pipeline operations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Observability CI/CD Pipeline Manager")
    parser.add_argument("action", choices=["deploy", "validate", "rollback"], help="Action to perform")
    parser.add_argument("--environment", required=True, help="Target environment")
    parser.add_argument("--applications", required=True, help="Comma-separated list of applications")
    parser.add_argument("--components", default="alerts,dashboards,policies", help="Components to deploy")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run")
    parser.add_argument("--force", action="store_true", help="Force deployment")
    parser.add_argument("--deployment-id", help="Deployment ID for rollback")
    
    args = parser.parse_args()
    
    manager = PipelineManager()
    
    if args.action == "deploy":
        config = DeploymentConfig(
            environment=args.environment,
            applications=args.applications.split(","),
            components=args.components.split(","),
            dry_run=args.dry_run,
            force=args.force
        )
        
        result = manager.create_deployment_pipeline(config)
        print(f"Deployment initiated: {result}")
        
    elif args.action == "validate":
        applications = args.applications.split(",")
        result = manager.create_validation_pipeline(applications)
        print(f"Validation completed: {result}")
        
    elif args.action == "rollback":
        if not args.deployment_id:
            print("Error: --deployment-id required for rollback")
            return
        
        result = manager.create_rollback_pipeline(args.deployment_id)
        print(f"Rollback initiated: {result}")


if __name__ == "__main__":
    main()
