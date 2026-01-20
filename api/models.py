"""
Database models for the observability API
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, Float, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from .database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=lambda: f"app-{uuid.uuid4().hex[:8]}")
    name = Column(String(100), nullable=False, index=True)
    environment = Column(String(20), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False)
    description = Column(Text)
    team = Column(String(100))
    status = Column(String(20), default="active", index=True)
    coverage_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    alerts = relationship("Alert", back_populates="application", cascade="all, delete-orphan")
    dashboards = relationship("Dashboard", back_populates="application", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="application", cascade="all, delete-orphan")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: f"alert-{uuid.uuid4().hex[:8]}")
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False, index=True)
    enabled = Column(Boolean, default=True)
    nrql_query = Column(Text, nullable=False)
    thresholds = Column(JSON, nullable=False)
    severity = Column(String(20), default="warning")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="alerts")


class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(String, primary_key=True, default=lambda: f"dashboard-{uuid.uuid4().hex[:8]}")
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False, index=True)
    description = Column(Text)
    widgets = Column(JSON, nullable=False)
    widgets_count = Column(Integer, default=0)
    dashboard_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="dashboards")


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(String, primary_key=True, default=lambda: f"deploy-{uuid.uuid4().hex[:8]}")
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    status = Column(String(20), nullable=False, index=True)
    components_deployed = Column(JSON)
    deployment_type = Column(String(20), default="full")
    dry_run = Column(Boolean, default=False)
    error_message = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    estimated_completion = Column(DateTime)

    # Relationships
    application = relationship("Application", back_populates="deployments")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: f"user-{uuid.uuid4().hex[:8]}")
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    api_key = Column(String(255), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: f"key-{uuid.uuid4().hex[:8]}")
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    last_used = Column(DateTime)
    permissions = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")


class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id = Column(String, primary_key=True, default=lambda: f"report-{uuid.uuid4().hex[:8]}")
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    standard = Column(String(50), nullable=False, index=True)
    overall_score = Column(Float)
    compliant = Column(Boolean, default=False)
    violations = Column(JSON)
    requirements = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("Application")
