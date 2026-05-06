"""
AI-Powered Observability and Predictive Monitoring
"""

import time
import uuid
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
import structlog
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import pandas as pd

from ...monitoring import (
    ANOMALY_DETECTION_EVENTS,
    ML_PREDICTION_ACCURACY,
    PATTERN_DETECTION_EVENTS,
    metrics_store
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/ai-observability", tags=["ai-observability"])


class PredictiveMetricEvent(BaseModel):
    metric_name: str
    current_value: float
    historical_values: List[float]
    prediction_horizon: int  # minutes ahead
    model_type: str = "auto"  # auto, linear, forest, lstm
    confidence_threshold: float = 0.8
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class AnomalyDetectionEvent(BaseModel):
    metric_name: str
    current_value: float
    baseline_value: float
    historical_values: List[float]
    detection_method: str = "isolation_forest"  # isolation_forest, statistical, lstm
    sensitivity: float = 0.1  # anomaly threshold
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class AIObservabilityEvent(BaseModel):
    service_name: str
    metric_type: str  # performance, error_rate, latency, throughput
    metrics: Dict[str, float]
    context: Dict[str, Any]
    analysis_type: str = "comprehensive"  # comprehensive, performance, security, cost
    prediction_window: int = 60  # minutes
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class CapacityPlanningEvent(BaseModel):
    resource_type: str  # cpu, memory, storage, network
    current_usage: float
    historical_usage: List[float]
    predicted_growth_rate: float
    time_horizon: int  # days
    service_name: str
    environment: str
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class IncidentPredictionEvent(BaseModel):
    incident_type: str  # outage, performance_degradation, security_breach
    risk_factors: Dict[str, float]
    current_metrics: Dict[str, float]
    historical_incidents: List[Dict[str, Any]]
    prediction_confidence: float
    time_to_incident: Optional[int] = None  # minutes
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class RootCauseAnalysisEvent(BaseModel):
    incident_id: str
    symptoms: Dict[str, Any]
    metrics_before_incident: Dict[str, List[float]]
    metrics_during_incident: Dict[str, List[float]]
    affected_services: List[str]
    analysis_depth: str = "deep"  # shallow, deep, comprehensive
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class AIInsightResponse(BaseModel):
    insights: Dict[str, Any]
    predictions: Dict[str, Any]
    anomalies: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    model_performance: Dict[str, Any]
    last_updated: datetime


class AIModelManager:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.model_performance = {}
        
    def get_or_create_model(self, model_type: str, metric_name: str):
        """Get existing model or create new one"""
        model_key = f"{model_type}:{metric_name}"
        
        if model_key not in self.models:
            if model_type == "isolation_forest":
                self.models[model_key] = IsolationForest(
                    contamination=0.1,
                    random_state=42,
                    n_estimators=100
                )
            elif model_type == "random_forest":
                self.models[model_key] = RandomForestRegressor(
                    n_estimators=100,
                    random_state=42,
                    n_jobs=-1
                )
            
            self.scalers[model_key] = StandardScaler()
            self.model_performance[model_key] = {
                "created_at": datetime.utcnow(),
                "last_trained": None,
                "accuracy": 0.0,
                "samples_trained": 0
            }
        
        return self.models[model_key], self.scalers[model_key]
    
    def train_anomaly_detection(self, metric_name: str, values: List[float]):
        """Train anomaly detection model"""
        if len(values) < 10:
            return False
        
        model, scaler = self.get_or_create_model("isolation_forest", metric_name)
        
        try:
            # Prepare data
            data = np.array(values).reshape(-1, 1)
            scaled_data = scaler.fit_transform(data)
            
            # Train model
            model.fit(scaled_data)
            
            # Update performance metrics
            model_key = f"isolation_forest:{metric_name}"
            self.model_performance[model_key].update({
                "last_trained": datetime.utcnow(),
                "samples_trained": len(values),
                "accuracy": model.score_samples(scaled_data).mean()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to train anomaly detection model for {metric_name}", error=str(e))
            return False
    
    def predict_anomaly(self, metric_name: str, current_value: float, historical_values: List[float]):
        """Predict if current value is anomalous"""
        model_key = f"isolation_forest:{metric_name}"
        
        if model_key not in self.models:
            return False, 0.0
        
        try:
            model, scaler = self.models[model_key]
            
            # Prepare data
            data = np.array(historical_values + [current_value]).reshape(-1, 1)
            scaled_data = scaler.transform(data)
            
            # Predict anomaly
            anomaly_score = model.decision_function(scaled_data[-1].reshape(1, -1))[0]
            is_anomaly = model.predict(scaled_data[-1].reshape(1, -1))[0] == -1
            
            return is_anomaly, float(anomaly_score)
            
        except Exception as e:
            logger.error(f"Failed to predict anomaly for {metric_name}", error=str(e))
            return False, 0.0
    
    def predict_future_values(self, metric_name: str, historical_values: List[float], horizon: int):
        """Predict future metric values"""
        if len(historical_values) < 20:
            return []
        
        model, scaler = self.get_or_create_model("random_forest", metric_name)
        
        try:
            # Prepare training data
            X = []
            y = []
            window_size = min(10, len(historical_values) // 2)
            
            for i in range(len(historical_values) - window_size):
                X.append(historical_values[i:i + window_size])
                y.append(historical_values[i + window_size])
            
            if len(X) < 5:
                return []
            
            X = np.array(X)
            y = np.array(y)
            
            # Train model
            model.fit(X, y)
            
            # Make predictions
            predictions = []
            current_window = historical_values[-window_size:]
            
            for _ in range(horizon):
                pred = model.predict([current_window])[0]
                predictions.append(float(pred))
                current_window = current_window[1:] + [pred]
            
            # Update performance metrics
            model_key = f"random_forest:{metric_name}"
            self.model_performance[model_key].update({
                "last_trained": datetime.utcnow(),
                "samples_trained": len(X)
            })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Failed to predict future values for {metric_name}", error=str(e))
            return []
    
    def analyze_patterns(self, metric_name: str, values: List[float]):
        """Analyze patterns in metric data"""
        if len(values) < 20:
            return {}
        
        try:
            df = pd.Series(values)
            
            # Statistical analysis
            analysis = {
                "trend": "increasing" if df.diff().mean() > 0 else "decreasing" if df.diff().mean() < 0 else "stable",
                "volatility": float(df.std()),
                "seasonality": self._detect_seasonality(values),
                "outliers": self._detect_outliers(values),
                "change_points": self._detect_change_points(values)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze patterns for {metric_name}", error=str(e))
            return {}
    
    def _detect_seasonality(self, values: List[float]) -> Dict[str, Any]:
        """Detect seasonal patterns"""
        if len(values) < 24:  # Need at least 24 data points
            return {"detected": False}
        
        try:
            df = pd.Series(values)
            
            # Simple seasonality detection using autocorrelation
            autocorr = [df.autocorr(lag=i) for i in range(1, min(24, len(values)//4))]
            max_corr = max(autocorr) if autocorr else 0
            best_lag = autocorr.index(max_corr) + 1 if autocorr else 0
            
            return {
                "detected": max_corr > 0.3,
                "period": best_lag,
                "strength": float(max_corr)
            }
            
        except Exception:
            return {"detected": False}
    
    def _detect_outliers(self, values: List[float]) -> Dict[str, Any]:
        """Detect outliers using IQR method"""
        try:
            df = pd.Series(values)
            Q1 = df.quantile(0.25)
            Q3 = df.quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = df[(df < lower_bound) | (df > upper_bound)]
            
            return {
                "count": len(outliers),
                "percentage": float(len(outliers) / len(values) * 100),
                "indices": outliers.index.tolist()
            }
            
        except Exception:
            return {"count": 0, "percentage": 0.0}
    
    def _detect_change_points(self, values: List[float]) -> List[int]:
        """Detect change points in time series"""
        if len(values) < 10:
            return []
        
        try:
            df = pd.Series(values)
            change_points = []
            
            # Simple change point detection using mean shift
            window_size = max(5, len(values) // 10)
            
            for i in range(window_size, len(values) - window_size):
                before_mean = df.iloc[i-window_size:i].mean()
                after_mean = df.iloc[i:i+window_size].mean()
                
                if abs(after_mean - before_mean) > df.std() * 2:
                    change_points.append(i)
            
            return change_points
            
        except Exception:
            return []


# Global model manager instance
model_manager = AIModelManager()


@router.post("/predictive-metrics")
async def track_predictive_metrics(event: PredictiveMetricEvent):
    """Track and predict future metric values"""
    try:
        # Train model if not exists
        if len(event.historical_values) >= 20:
            model_manager.train_anomaly_detection(event.metric_name, event.historical_values)
        
        # Make predictions
        predictions = model_manager.predict_future_values(
            event.metric_name,
            event.historical_values,
            event.prediction_horizon
        )
        
        # Analyze patterns
        patterns = model_manager.analyze_patterns(event.metric_name, event.historical_values)
        
        # Store in metrics store
        if 'predictive_metrics' not in metrics_store['analytics_metrics']:
            metrics_store['analytics_metrics']['predictive_metrics'] = {}
        
        key = f"{event.metric_name}:{event.model_type}"
        metrics_store['analytics_metrics']['predictive_metrics'][key] = {
            'metric_name': event.metric_name,
            'current_value': event.current_value,
            'predictions': predictions,
            'prediction_horizon': event.prediction_horizon,
            'patterns': patterns,
            'confidence_threshold': event.confidence_threshold,
            'model_type': event.model_type,
            'timestamp': event.timestamp or datetime.utcnow(),
            'metadata': event.metadata or {}
        }
        
        # Update Prometheus metrics
        if predictions:
            avg_prediction = sum(predictions) / len(predictions)
            ML_PREDICTION_ACCURACY.labels(
                model_name=event.model_type,
                prediction_type="forecast",
                time_period=f"{event.prediction_horizon}min"
            ).set(abs(avg_prediction - event.current_value) / max(event.current_value, 1) * 100)
        
        logger.info(
            "Predictive metrics tracked",
            metric_name=event.metric_name,
            prediction_count=len(predictions),
            model_type=event.model_type
        )
        
        return {
            "status": "success",
            "predictions": predictions,
            "patterns": patterns,
            "confidence": min(len(event.historical_values) / 100, 1.0)
        }
        
    except Exception as e:
        logger.error("Failed to track predictive metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track predictive metrics")


@router.post("/anomaly-detection")
async def detect_anomalies(event: AnomalyDetectionEvent):
    """Detect anomalies in metric data"""
    try:
        # Train model if enough data
        if len(event.historical_values) >= 10:
            model_manager.train_anomaly_detection(event.metric_name, event.historical_values)
        
        # Detect anomaly
        is_anomaly, anomaly_score = model_manager.predict_anomaly(
            event.metric_name,
            event.current_value,
            event.historical_values
        )
        
        # Calculate deviation
        baseline_mean = np.mean(event.historical_values)
        baseline_std = np.std(event.historical_values)
        deviation = abs(event.current_value - baseline_mean) / max(baseline_std, 1)
        
        # Store anomaly event
        if is_anomaly:
            ANOMALY_DETECTION_EVENTS.labels(
                anomaly_type="statistical",
                severity="high" if deviation > 3 else "medium",
                metric_name=event.metric_name,
                detection_method=event.detection_method
            ).inc()
            
            if 'anomalies' not in metrics_store['analytics_metrics']:
                metrics_store['analytics_metrics']['anomalies'] = []
            
            anomaly_data = {
                'anomaly_id': str(uuid.uuid4()),
                'metric_name': event.metric_name,
                'current_value': event.current_value,
                'baseline_value': event.baseline_value,
                'anomaly_score': anomaly_score,
                'deviation': deviation,
                'detection_method': event.detection_method,
                'sensitivity': event.sensitivity,
                'timestamp': event.timestamp or datetime.utcnow(),
                'metadata': event.metadata or {}
            }
            
            metrics_store['analytics_metrics']['anomalies'].append(anomaly_data)
        
        logger.info(
            "Anomaly detection completed",
            metric_name=event.metric_name,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            deviation=deviation
        )
        
        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "deviation": deviation,
            "baseline_mean": baseline_mean,
            "baseline_std": baseline_std,
            "severity": "high" if deviation > 3 else "medium" if deviation > 2 else "low"
        }
        
    except Exception as e:
        logger.error("Failed to detect anomalies", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to detect anomalies")


@router.post("/ai-observability")
async def track_ai_observability(event: AIObservabilityEvent):
    """Comprehensive AI-powered observability analysis"""
    try:
        insights = {}
        predictions = {}
        anomalies = []
        recommendations = []
        
        # Analyze each metric
        for metric_name, metric_value in event.metrics.items():
            # Get historical data (simplified - in real implementation, would fetch from time series DB)
            historical_key = f"{event.service_name}:{metric_name}"
            historical_values = metrics_store.get('analytics_metrics', {}).get('historical_data', {}).get(historical_key, [])
            
            if not historical_values:
                historical_values = [metric_value] * 10  # Fallback
            
            # Anomaly detection
            is_anomaly, anomaly_score = model_manager.predict_anomaly(
                metric_name,
                metric_value,
                historical_values
            )
            
            if is_anomaly:
                anomalies.append({
                    'metric_name': metric_name,
                    'current_value': metric_value,
                    'anomaly_score': anomaly_score,
                    'severity': 'high' if anomaly_score < -0.5 else 'medium'
                })
            
            # Predictive analysis
            future_predictions = model_manager.predict_future_values(
                metric_name,
                historical_values,
                event.prediction_window
            )
            
            if future_predictions:
                predictions[metric_name] = future_predictions
                
                # Generate recommendations based on predictions
                avg_prediction = sum(future_predictions) / len(future_predictions)
                if metric_name == 'error_rate' and avg_prediction > 0.05:
                    recommendations.append({
                        'type': 'performance',
                        'metric': metric_name,
                        'message': f'Predicted error rate increase to {avg_prediction:.2%}. Consider scaling resources.',
                        'priority': 'high'
                    })
                elif metric_name == 'response_time' and avg_prediction > 1000:
                    recommendations.append({
                        'type': 'performance',
                        'metric': metric_name,
                        'message': f'Predicted response time increase to {avg_prediction:.0f}ms. Optimize database queries.',
                        'priority': 'medium'
                    })
            
            # Pattern analysis
            patterns = model_manager.analyze_patterns(metric_name, historical_values)
            insights[metric_name] = patterns
        
        # Store comprehensive analysis
        if 'ai_observability' not in metrics_store['analytics_metrics']:
            metrics_store['analytics_metrics']['ai_observability'] = []
        
        analysis_data = {
            'analysis_id': str(uuid.uuid4()),
            'service_name': event.service_name,
            'metric_type': event.metric_type,
            'insights': insights,
            'predictions': predictions,
            'anomalies': anomalies,
            'recommendations': recommendations,
            'analysis_type': event.analysis_type,
            'prediction_window': event.prediction_window,
            'context': event.context,
            'timestamp': event.timestamp or datetime.utcnow(),
            'metadata': event.metadata or {}
        }
        
        metrics_store['analytics_metrics']['ai_observability'].append(analysis_data)
        
        logger.info(
            "AI observability analysis completed",
            service_name=event.service_name,
            metric_type=event.metric_type,
            anomalies_detected=len(anomalies),
            recommendations_generated=len(recommendations)
        )
        
        return {
            "status": "success",
            "analysis_id": analysis_data['analysis_id'],
            "insights": insights,
            "predictions": predictions,
            "anomalies": anomalies,
            "recommendations": recommendations,
            "confidence_scores": {
                metric: min(len(historical_values) / 50, 1.0)
                for metric in event.metrics.keys()
            }
        }
        
    except Exception as e:
        logger.error("Failed to perform AI observability analysis", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to perform AI observability analysis")


@router.post("/capacity-planning")
async def analyze_capacity_planning(event: CapacityPlanningEvent):
    """AI-powered capacity planning and resource optimization"""
    try:
        # Analyze usage patterns
        patterns = model_manager.analyze_patterns(
            f"{event.resource_type}:{event.service_name}",
            event.historical_usage
        )
        
        # Predict future usage
        future_predictions = model_manager.predict_future_values(
            f"{event.resource_type}:{event.service_name}",
            event.historical_usage,
            event.time_horizon * 24 * 60  # Convert days to minutes
        )
        
        # Calculate capacity recommendations
        current_peak = max(event.historical_usage)
        predicted_peak = max(future_predictions) if future_predictions else current_peak
        
        # Growth rate analysis
        if len(event.historical_usage) >= 2:
            actual_growth_rate = (event.historical_usage[-1] - event.historical_usage[0]) / event.historical_usage[0]
        else:
            actual_growth_rate = event.predicted_growth_rate
        
        # Resource recommendations
        recommendations = []
        
        if predicted_peak > current_peak * 1.2:
            recommendations.append({
                'type': 'scale_up',
                'message': f'Predicted {predicted_peak:.1f}% usage exceeds current capacity. Scale up recommended.',
                'priority': 'high',
                'suggested_capacity': predicted_peak * 1.3
            })
        elif predicted_peak < current_peak * 0.5:
            recommendations.append({
                'type': 'scale_down',
                'message': f'Predicted {predicted_peak:.1f}% usage is significantly below current capacity. Scale down possible.',
                'priority': 'medium',
                'suggested_capacity': predicted_peak * 1.2
            })
        
        # Cost optimization suggestions
        if actual_growth_rate < 0.05:  # Low growth
            recommendations.append({
                'type': 'cost_optimization',
                'message': 'Low growth rate detected. Consider reserved instances for cost savings.',
                'priority': 'low'
            })
        
        # Store capacity planning analysis
        if 'capacity_planning' not in metrics_store['analytics_metrics']:
            metrics_store['analytics_metrics']['capacity_planning'] = []
        
        capacity_data = {
            'analysis_id': str(uuid.uuid4()),
            'resource_type': event.resource_type,
            'service_name': event.service_name,
            'environment': event.environment,
            'current_usage': event.current_usage,
            'predicted_usage': future_predictions,
            'growth_rate': actual_growth_rate,
            'time_horizon': event.time_horizon,
            'recommendations': recommendations,
            'patterns': patterns,
            'timestamp': event.timestamp or datetime.utcnow(),
            'metadata': event.metadata or {}
        }
        
        metrics_store['analytics_metrics']['capacity_planning'].append(capacity_data)
        
        logger.info(
            "Capacity planning analysis completed",
            resource_type=event.resource_type,
            service_name=event.service_name,
            predicted_peak=predicted_peak,
            recommendations_count=len(recommendations)
        )
        
        return {
            "status": "success",
            "current_usage": event.current_usage,
            "predicted_peak": predicted_peak,
            "growth_rate": actual_growth_rate,
            "predictions": future_predictions,
            "patterns": patterns,
            "recommendations": recommendations,
            "cost_optimization_potential": max(0, (current_peak - predicted_peak) / current_peak * 100)
        }
        
    except Exception as e:
        logger.error("Failed to analyze capacity planning", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to analyze capacity planning")


@router.post("/incident-prediction")
async def predict_incidents(event: IncidentPredictionEvent):
    """AI-powered incident prediction and risk assessment"""
    try:
        # Calculate risk score
        risk_score = 0.0
        risk_factors = event.risk_factors
        
        # Weight different risk factors
        risk_weights = {
            'error_rate': 0.3,
            'response_time': 0.25,
            'cpu_usage': 0.2,
            'memory_usage': 0.15,
            'network_latency': 0.1
        }
        
        for factor, value in risk_factors.items():
            weight = risk_weights.get(factor, 0.1)
            risk_score += value * weight
        
        # Analyze historical incident patterns
        incident_patterns = {}
        if event.historical_incidents:
            incident_df = pd.DataFrame(event.historical_incidents)
            
            if 'time_to_incident' in incident_df.columns:
                incident_patterns['avg_time_to_incident'] = incident_df['time_to_incident'].mean()
                incident_patterns['incident_frequency'] = len(event.historical_incidents)
            
            if 'severity' in incident_df.columns:
                incident_patterns['severity_distribution'] = incident_df['severity'].value_counts().to_dict()
        
        # Predict time to incident
        time_to_incident = None
        if risk_score > 0.7:  # High risk
            if incident_patterns.get('avg_time_to_incident'):
                # Adjust based on current risk vs historical average
                time_to_incident = int(incident_patterns['avg_time_to_incident'] * (1 - risk_score))
            else:
                time_to_incident = int(60 * (1 - risk_score))  # Default: within 60 minutes
        
        # Generate recommendations
        recommendations = []
        
        if risk_score > 0.8:
            recommendations.append({
                'type': 'immediate_action',
                'message': 'Critical risk detected. Immediate investigation required.',
                'priority': 'critical'
            })
        elif risk_score > 0.6:
            recommendations.append({
                'type': 'preventive_action',
                'message': 'High risk detected. Consider scaling resources or investigating bottlenecks.',
                'priority': 'high'
            })
        
        # Store incident prediction
        if 'incident_predictions' not in metrics_store['analytics_metrics']:
            metrics_store['analytics_metrics']['incident_predictions'] = []
        
        prediction_data = {
            'prediction_id': str(uuid.uuid4()),
            'incident_type': event.incident_type,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'current_metrics': event.current_metrics,
            'time_to_incident': time_to_incident,
            'prediction_confidence': event.prediction_confidence,
            'incident_patterns': incident_patterns,
            'recommendations': recommendations,
            'timestamp': event.timestamp or datetime.utcnow(),
            'metadata': event.metadata or {}
        }
        
        metrics_store['analytics_metrics']['incident_predictions'].append(prediction_data)
        
        logger.info(
            "Incident prediction completed",
            incident_type=event.incident_type,
            risk_score=risk_score,
            time_to_incident=time_to_incident,
            confidence=event.prediction_confidence
        )
        
        return {
            "status": "success",
            "risk_score": risk_score,
            "risk_level": "critical" if risk_score > 0.8 else "high" if risk_score > 0.6 else "medium" if risk_score > 0.4 else "low",
            "time_to_incident": time_to_incident,
            "incident_patterns": incident_patterns,
            "recommendations": recommendations,
            "confidence": event.prediction_confidence
        }
        
    except Exception as e:
        logger.error("Failed to predict incidents", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to predict incidents")


@router.post("/root-cause-analysis")
async def perform_root_cause_analysis(event: RootCauseAnalysisEvent):
    """AI-powered root cause analysis for incidents"""
    try:
        # Analyze metric changes before and during incident
        analysis_results = {}
        
        for metric_name, before_values in event.metrics_before_incident.items():
            during_values = event.metrics_during_incident.get(metric_name, [])
            
            if before_values and during_values:
                before_mean = np.mean(before_values)
                during_mean = np.mean(during_values)
                before_std = np.std(before_values)
                
                # Calculate change significance
                change_magnitude = abs(during_mean - before_mean)
                change_significance = change_magnitude / max(before_std, 1)
                
                # Determine correlation with incident
                correlation_strength = "high" if change_significance > 3 else "medium" if change_significance > 2 else "low"
                
                analysis_results[metric_name] = {
                    'before_mean': before_mean,
                    'during_mean': during_mean,
                    'change_magnitude': change_magnitude,
                    'change_significance': change_significance,
                    'correlation_strength': correlation_strength,
                    'direction': 'increased' if during_mean > before_mean else 'decreased'
                }
        
        # Identify potential root causes
        potential_causes = []
        
        # Sort metrics by change significance
        sorted_metrics = sorted(
            analysis_results.items(),
            key=lambda x: x[1]['change_significance'],
            reverse=True
        )
        
        for metric_name, analysis in sorted_metrics[:5]:  # Top 5 potential causes
            if analysis['correlation_strength'] == 'high':
                cause_type = 'performance' if 'latency' in metric_name or 'response_time' in metric_name else \
                           'resource' if 'cpu' in metric_name or 'memory' in metric_name else \
                           'error' if 'error' in metric_name or 'failure' in metric_name else 'other'
                
                potential_causes.append({
                    'metric': metric_name,
                    'cause_type': cause_type,
                    'confidence': min(analysis['change_significance'] / 5, 1.0),
                    'description': f"{metric_name} {analysis['direction']} by {analysis['change_magnitude']:.2f} (significance: {analysis['change_significance']:.2f})",
                    'impact_level': 'high' if analysis['change_significance'] > 4 else 'medium' if analysis['change_significance'] > 2 else 'low'
                })
        
        # Generate recommendations based on root causes
        recommendations = []
        
        for cause in potential_causes:
            if cause['cause_type'] == 'performance':
                recommendations.append({
                    'type': 'optimization',
                    'message': f"Optimize {cause['metric']} through code optimization or infrastructure scaling.",
                    'priority': 'high' if cause['impact_level'] == 'high' else 'medium'
                })
            elif cause['cause_type'] == 'resource':
                recommendations.append({
                    'type': 'scaling',
                    'message': f"Scale resources to address {cause['metric']} constraints.",
                    'priority': 'high' if cause['impact_level'] == 'high' else 'medium'
                })
            elif cause['cause_type'] == 'error':
                recommendations.append({
                    'type': 'debugging',
                    'message': f"Investigate and fix {cause['metric']} issues.",
                    'priority': 'critical' if cause['impact_level'] == 'high' else 'high'
                })
        
        # Store root cause analysis
        if 'root_cause_analysis' not in metrics_store['analytics_metrics']:
            metrics_store['analytics_metrics']['root_cause_analysis'] = []
        
        rca_data = {
            'incident_id': event.incident_id,
            'analysis_results': analysis_results,
            'potential_causes': potential_causes,
            'recommendations': recommendations,
            'affected_services': event.affected_services,
            'analysis_depth': event.analysis_depth,
            'timestamp': event.timestamp or datetime.utcnow(),
            'metadata': event.metadata or {}
        }
        
        metrics_store['analytics_metrics']['root_cause_analysis'].append(rca_data)
        
        logger.info(
            "Root cause analysis completed",
            incident_id=event.incident_id,
            potential_causes=len(potential_causes),
            recommendations=len(recommendations)
        )
        
        return {
            "status": "success",
            "incident_id": event.incident_id,
            "analysis_results": analysis_results,
            "potential_causes": potential_causes,
            "recommendations": recommendations,
            "confidence_score": sum(cause['confidence'] for cause in potential_causes) / len(potential_causes) if potential_causes else 0.0
        }
        
    except Exception as e:
        logger.error("Failed to perform root cause analysis", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to perform root cause analysis")


@router.get("/ai-insights", response_model=AIInsightResponse)
async def get_ai_insights(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    hours: int = Query(24, description="Hours of data to analyze")
):
    """Get comprehensive AI-powered insights"""
    try:
        analytics_data = metrics_store.get('analytics_metrics', {})
        
        # Collect insights from different AI analyses
        insights = {}
        predictions = {}
        anomalies = []
        recommendations = []
        confidence_scores = {}
        model_performance = {}
        
        # Predictive metrics insights
        predictive_metrics = analytics_data.get('predictive_metrics', {})
        for key, data in predictive_metrics.items():
            if service_name and service_name not in key:
                continue
            
            metric_name = data.get('metric_name', 'unknown')
            insights[metric_name] = data.get('patterns', {})
            predictions[metric_name] = data.get('predictions', [])
            
            # Calculate confidence based on data quality
            confidence = min(len(data.get('predictions', [])) / 10, 1.0)
            confidence_scores[metric_name] = confidence
        
        # Anomalies
        anomalies_list = analytics_data.get('anomalies', [])
        for anomaly in anomalies_list[-50:]:  # Last 50 anomalies
            if service_name and service_name not in anomaly.get('metric_name', ''):
                continue
            anomalies.append(anomaly)
        
        # AI observability insights
        ai_observability = analytics_data.get('ai_observability', [])
        for analysis in ai_observability[-20:]:  # Last 20 analyses
            if service_name and service_name != analysis.get('service_name'):
                continue
            
            # Merge insights
            for metric, insight in analysis.get('insights', {}).items():
                if metric not in insights:
                    insights[metric] = insight
            
            # Merge predictions
            for metric, prediction in analysis.get('predictions', {}).items():
                if metric not in predictions:
                    predictions[metric] = prediction
            
            # Collect recommendations
            recommendations.extend(analysis.get('recommendations', []))
        
        # Model performance
        for model_key, performance in model_manager.model_performance.items():
            model_performance[model_key] = {
                'last_trained': performance.get('last_trained'),
                'samples_trained': performance.get('samples_trained', 0),
                'accuracy': performance.get('accuracy', 0.0)
            }
        
        return AIInsightResponse(
            insights=insights,
            predictions=predictions,
            anomalies=anomalies,
            recommendations=recommendations,
            confidence_scores=confidence_scores,
            model_performance=model_performance,
            last_updated=metrics_store['last_updated']
        )
        
    except Exception as e:
        logger.error("Failed to get AI insights", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve AI insights")
