"""
Pytest configuration and fixtures
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.app import app
from api.database import get_db, Base
from api.models import Application, Alert, Dashboard, User, APIKey

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client():
    """Create a test client"""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_application(db):
    """Create a sample application for testing"""
    app = Application(
        name="Test Application",
        environment="development",
        entity_id="test-entity-123",
        description="Test application for unit tests",
        team="test-team"
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@pytest.fixture
def sample_alert(db, sample_application):
    """Create a sample alert for testing"""
    alert = Alert(
        application_id=sample_application.id,
        name="Test CPU Alert",
        type="cpu_usage",
        nrql_query="SELECT average(cpuPercent) FROM SystemSample",
        thresholds={"critical": 80, "warning": 60},
        severity="warning"
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@pytest.fixture
def sample_dashboard(db, sample_application):
    """Create a sample dashboard for testing"""
    dashboard = Dashboard(
        application_id=sample_application.id,
        name="Test Dashboard",
        type="infrastructure",
        widgets=[
            {
                "title": "CPU Usage",
                "visualization": "line_chart",
                "nrql": "SELECT average(cpuPercent) FROM SystemSample"
            }
        ]
    )
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    return dashboard


@pytest.fixture
def sample_user(db):
    """Create a sample user for testing"""
    from api.auth import get_password_hash
    
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
        is_active=True,
        is_superuser=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_api_key(db, sample_user):
    """Create a sample API key for testing"""
    from api.auth import get_password_hash
    
    api_key = APIKey(
        name="Test API Key",
        key_hash=get_password_hash("test-api-key-123"),
        user_id=sample_user.id,
        is_active=True,
        permissions=["read", "write"]
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


@pytest.fixture
def auth_headers(sample_api_key):
    """Create authorization headers for testing"""
    return {"Authorization": "Bearer test-api-key-123"}


@pytest.fixture
def admin_headers():
    """Create admin authorization headers for testing"""
    return {"Authorization": "Bearer admin-test-key"}
