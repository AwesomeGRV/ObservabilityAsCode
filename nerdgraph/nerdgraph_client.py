"""
NERDGraph Client for New Relic API interactions
"""

import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class NERDGraphClient:
    """Client for interacting with New Relic NERDGraph API"""
    
    def __init__(self, api_key: str, region: str = "US"):
        self.api_key = api_key
        self.region = region.lower()
        self.base_url = f"https://api-{self.region}.newrelic.com/graphql"
        self.headers = {
            "API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"NERDGraph query failed: {e}")
            raise
    
    def get_applications(self) -> List[Dict]:
        """Get all applications in the account"""
        query = """
        query GetApplications {
          actor {
            entitySearch(query: "type = 'APPLICATION'") {
              results {
                entities {
                  name
                  guid
                  entityType
                  domain
                  type
                  ... on ApplicationEntity {
                    name
                    accountId
                    reporting
                  }
                }
              }
            }
          }
        }
        """
        
        result = self.execute_query(query)
        return result.get("data", {}).get("actor", {}).get("entitySearch", {}).get("results", {}).get("entities", [])
    
    def get_alert_policies(self, account_id: int) -> List[Dict]:
        """Get alert policies for an account"""
        query = """
        query GetAlertPolicies($accountId: Int!) {
          actor {
            account(id: $accountId) {
              alerts {
                policiesSearch {
                  policies {
                    id
                    name
                    incidentPreference
                    createdAt
                    updatedAt
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {"accountId": account_id}
        result = self.execute_query(query, variables)
        return result.get("data", {}).get("actor", {}).get("account", {}).get("alerts", {}).get("policiesSearch", {}).get("policies", [])
    
    def get_alert_conditions(self, policy_id: int) -> List[Dict]:
        """Get alert conditions for a policy"""
        query = """
        query GetAlertConditions($policyId: Int!) {
          actor {
            account(id: 123456) {
              alerts {
                policy(id: $policyId) {
                  name
                  incidentPreference
                  conditions {
                    id
                    name
                    type
                    enabled
                    nrql {
                      query
                    }
                    critical {
                      operator
                      threshold
                      thresholdDuration
                      thresholdOccurrences
                    }
                    warning {
                      operator
                      threshold
                      thresholdDuration
                      thresholdOccurrences
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {"policyId": policy_id}
        result = self.execute_query(query, variables)
        policy_data = result.get("data", {}).get("actor", {}).get("account", {}).get("alerts", {}).get("policy", {})
        return policy_data.get("conditions", [])
    
    def get_dashboards(self, account_id: int) -> List[Dict]:
        """Get all dashboards for an account"""
        query = """
        query GetDashboards($accountId: Int!) {
          actor {
            account(id: $accountId) {
              dashboardSearch(searchCriteria: {}) {
                dashboards {
                  id
                  name
                  description
                  createdAt
                  updatedAt
                  widgets {
                    title
                    visualization {
                      id
                    }
                    rawConfiguration
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {"accountId": account_id}
        result = self.execute_query(query, variables)
        return result.get("data", {}).get("actor", {}).get("account", {}).get("dashboardSearch", {}).get("dashboards", [])
    
    def create_alert_policy(self, account_id: int, policy_name: str, incident_preference: str = "PER_POLICY") -> Dict:
        """Create a new alert policy"""
        mutation = """
        mutation CreateAlertPolicy($accountId: Int!, $policyName: String!, $incidentPreference: IncidentPreference!) {
          actor {
            account(id: $accountId) {
              alerts {
                policyCreate(policy: {
                  name: $policyName
                  incidentPreference: $incidentPreference
                }) {
                  id
                  name
                  incidentPreference
                }
              }
            }
          }
        }
        """
        
        variables = {
            "accountId": account_id,
            "policyName": policy_name,
            "incidentPreference": incident_preference
        }
        
        result = self.execute_query(mutation, variables)
        return result.get("data", {}).get("actor", {}).get("account", {}).get("alerts", {}).get("policyCreate", {})
    
    def create_dashboard(self, account_id: int, dashboard_config: Dict) -> Dict:
        """Create a new dashboard"""
        mutation = """
        mutation CreateDashboard($accountId: Int!, $dashboard: DashboardInput!) {
          actor {
            account(id: $accountId) {
              dashboardCreate(dashboard: $dashboard) {
                id
                name
                description
              }
            }
          }
        }
        """
        
        variables = {
            "accountId": account_id,
            "dashboard": dashboard_config
        }
        
        result = self.execute_query(mutation, variables)
        return result.get("data", {}).get("actor", {}).get("account", {}).get("dashboardCreate", {})
    
    def get_recent_incidents(self, account_id: int, hours: int = 24) -> List[Dict]:
        """Get recent incidents"""
        query = """
        query GetRecentIncidents($accountId: Int!, $timeWindow: DateTimeRangeInput!) {
          actor {
            account(id: $accountId) {
              alerts {
                incidentsSearch(searchCriteria: {
                  timeWindow: $timeWindow
                }) {
                  incidents {
                    id
                    title
                    state
                    severity
                    createdAt
                    updatedAt
                    policyName
                    conditionName
                  }
                }
              }
            }
          }
        }
        """
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        variables = {
            "accountId": account_id,
            "timeWindow": {
                "begin": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z"
            }
        }
        
        result = self.execute_query(query, variables)
        return result.get("data", {}).get("actor", {}).get("account", {}).get("alerts", {}).get("incidentsSearch", {}).get("incidents", [])
