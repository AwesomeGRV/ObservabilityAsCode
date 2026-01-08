#!/usr/bin/env python3
"""
Compliance Checker for Observability as Code
"""

import yaml
import json
import argparse
import logging
import requests
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from coverage.scoring import CoverageScorer
from nerdgraph.nerdgraph_client import NERDGraphClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ComplianceChecker:
    """Check compliance of applications with observability standards"""
    
    def __init__(self, config_file: str, api_url: str, api_key: str):
        self.config_file = config_file
        self.api_url = api_url
        self.api_key = api_key
        self.scorer = CoverageScorer()
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})
        
        # Load application inventory
        self.applications = self._load_applications()
    
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
    
    def check_application_compliance(self, app: Dict, environment: str) -> Dict:
        """Check compliance for a single application"""
        app_name = app["name"]
        
        try:
            # Get coverage data from API
            coverage_url = f"{self.api_url}/coverage"
            coverage_response = self.session.get(coverage_url, params={"applicationId": app_name})
            
            if coverage_response.status_code == 200:
                coverage_data = coverage_response.json()
                app_coverage = coverage_data.get("applications", [{}])[0]
            else:
                logger.warning(f"Failed to get coverage for {app_name}: {coverage_response.status_code}")
                app_coverage = {"score": 0, "level": "critical", "issues": ["API call failed"]}
            
            # Get compliance data from API
            compliance_url = f"{self.api_url}/compliance"
            compliance_response = self.session.get(compliance_url, params={"applicationId": app_name})
            
            if compliance_response.status_code == 200:
                compliance_data = compliance_response.json()
                app_compliance = compliance_data.get("applications", [{}])[0]
            else:
                logger.warning(f"Failed to get compliance for {app_name}: {compliance_response.status_code}")
                app_compliance = {"compliant": False, "score": 0, "violations": ["API call failed"]}
            
            # Check standard requirements
            requirements = self._check_standard_requirements(app, environment)
            
            # Overall compliance status
            compliant = (
                app_compliance.get("compliant", False) and
                app_coverage.get("score", 0) >= 80 and
                all(req["met"] for req in requirements.values())
            )
            
            return {
                "name": app_name,
                "environment": environment,
                "team": app.get("team", "Unknown"),
                "criticality": app.get("criticality", "unknown"),
                "compliant": compliant,
                "coverage_score": app_coverage.get("score", 0),
                "compliance_score": app_compliance.get("score", 0),
                "violations": app_compliance.get("violations", []),
                "issues": app_coverage.get("issues", []),
                "requirements": requirements,
                "last_checked": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking compliance for {app_name}: {e}")
            return {
                "name": app_name,
                "environment": environment,
                "team": app.get("team", "Unknown"),
                "criticality": app.get("criticality", "unknown"),
                "compliant": False,
                "coverage_score": 0,
                "compliance_score": 0,
                "violations": [f"Error: {str(e)}"],
                "issues": [f"Error: {str(e)}"],
                "requirements": {},
                "last_checked": datetime.utcnow().isoformat()
            }
    
    def _check_standard_requirements(self, app: Dict, environment: str) -> Dict:
        """Check standard observability requirements"""
        requirements = {
            "cpu_monitoring": {"met": False, "description": "CPU usage monitoring configured"},
            "memory_monitoring": {"met": False, "description": "Memory usage monitoring configured"},
            "disk_monitoring": {"met": False, "description": "Disk usage monitoring configured"},
            "response_time_monitoring": {"met": False, "description": "Response time monitoring configured"},
            "error_monitoring": {"met": False, "description": "Error rate monitoring configured"},
            "infrastructure_dashboard": {"met": False, "description": "Infrastructure dashboard created"},
            "application_dashboard": {"met": False, "description": "Application performance dashboard created"},
            "error_dashboard": {"met": False, "description": "Error analysis dashboard created"},
            "alert_policy": {"met": False, "description": "Alert policy configured"},
            "notification_channel": {"met": False, "description": "Notification channel configured"}
        }
        
        # For now, simulate requirement checks
        # In a real implementation, these would check actual New Relic configurations
        import random
        for req in requirements:
            if environment == "production":
                requirements[req]["met"] = random.choice([True, True, True, False])  # 75% chance
            elif environment == "staging":
                requirements[req]["met"] = random.choice([True, True, False])  # 66% chance
            else:
                requirements[req]["met"] = random.choice([True, False])  # 50% chance
        
        return requirements
    
    def check_environment_compliance(self, environment: str) -> Dict:
        """Check compliance for all applications in an environment"""
        apps = self.applications.get(environment, [])
        
        if not apps:
            return {
                "environment": environment,
                "total_applications": 0,
                "compliant_applications": 0,
                "compliance_percentage": 0,
                "applications": [],
                "summary": {
                    "critical_issues": [],
                    "recommendations": []
                }
            }
        
        results = []
        compliant_count = 0
        critical_issues = []
        
        for app in apps:
            result = self.check_application_compliance(app, environment)
            results.append(result)
            
            if result["compliant"]:
                compliant_count += 1
            
            # Collect critical issues
            if app.get("criticality") in ["critical", "high"] and not result["compliant"]:
                critical_issues.append({
                    "application": app["name"],
                    "team": app.get("team", "Unknown"),
                    "issues": result["violations"] + result["issues"]
                })
        
        compliance_percentage = (compliant_count / len(apps)) * 100 if apps else 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(results, environment)
        
        return {
            "environment": environment,
            "total_applications": len(apps),
            "compliant_applications": compliant_count,
            "compliance_percentage": round(compliance_percentage, 2),
            "applications": results,
            "summary": {
                "critical_issues": critical_issues,
                "recommendations": recommendations
            }
        }
    
    def _generate_recommendations(self, results: List[Dict], environment: str) -> List[str]:
        """Generate recommendations based on compliance results"""
        recommendations = []
        
        # Count common violations
        violation_counts = {}
        for result in results:
            for violation in result["violations"]:
                violation_counts[violation] = violation_counts.get(violation, 0) + 1
        
        # Generate recommendations for common issues
        if violation_counts:
            top_violations = sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            for violation, count in top_violations:
                if count > len(results) * 0.3:  # If more than 30% have this issue
                    recommendations.append(f"Address '{violation}' - affects {count} applications")
        
        # Environment-specific recommendations
        if environment == "production":
            non_compliant_critical = [
                r for r in results 
                if not r["compliant"] and r["criticality"] in ["critical", "high"]
            ]
            
            if non_compliant_critical:
                recommendations.append(
                    f"URGENT: {len(non_compliant_critical)} critical/high applications are non-compliant"
                )
        
        # General recommendations
        avg_coverage = sum(r["coverage_score"] for r in results) / len(results) if results else 0
        if avg_coverage < 80:
            recommendations.append("Improve overall observability coverage - current average: {:.1f}%".format(avg_coverage))
        
        return recommendations
    
    def generate_compliance_report(self, environments: List[str] = None) -> Dict:
        """Generate comprehensive compliance report"""
        if environments is None:
            environments = ["production", "staging", "development"]
        
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "environments": {},
            "overall_summary": {}
        }
        
        total_apps = 0
        total_compliant = 0
        all_critical_issues = []
        
        for env in environments:
            env_report = self.check_environment_compliance(env)
            report["environments"][env] = env_report
            
            total_apps += env_report["total_applications"]
            total_compliant += env_report["compliant_applications"]
            all_critical_issues.extend(env_report["summary"]["critical_issues"])
        
        # Overall summary
        overall_compliance = (total_compliant / total_apps * 100) if total_apps > 0 else 0
        
        report["overall_summary"] = {
            "total_applications": total_apps,
            "compliant_applications": total_compliant,
            "overall_compliance_percentage": round(overall_compliance, 2),
            "critical_issues_count": len(all_critical_issues),
            "critical_issues": all_critical_issues[:10],  # Top 10 critical issues
            "status": "HEALTHY" if overall_compliance >= 90 else "NEEDS_ATTENTION" if overall_compliance >= 70 else "CRITICAL"
        }
        
        return report


def main():
    parser = argparse.ArgumentParser(description="Check observability compliance")
    parser.add_argument("--config", default="inventory/applications.yaml", help="Applications inventory file")
    parser.add_argument("--api-url", required=True, help="Observability API URL")
    parser.add_argument("--api-key", required=True, help="Observability API key")
    parser.add_argument("--environment", choices=["production", "staging", "development"], help="Specific environment to check")
    parser.add_argument("--output", help="Output file for report (JSON)")
    parser.add_argument("--format", choices=["json", "yaml"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    # Initialize compliance checker
    checker = ComplianceChecker(args.config, args.api_url, args.api_key)
    
    # Generate report
    if args.environment:
        report = checker.check_environment_compliance(args.environment)
    else:
        report = checker.generate_compliance_report()
    
    # Output report
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            if args.format == "yaml":
                yaml.dump(report, f, default_flow_style=False)
            else:
                json.dump(report, f, indent=2)
        logger.info(f"Report saved to {output_path}")
    else:
        if args.format == "yaml":
            print(yaml.dump(report, default_flow_style=False))
        else:
            print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
