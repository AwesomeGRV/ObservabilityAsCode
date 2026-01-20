"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create applications table
    op.create_table('applications',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('environment', sa.String(length=20), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('team', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('coverage_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_applications_environment'), 'applications', ['environment'], unique=False)
    op.create_index(op.f('ix_applications_id'), 'applications', ['id'], unique=False)
    op.create_index(op.f('ix_applications_name'), 'applications', ['name'], unique=False)
    op.create_index(op.f('ix_applications_status'), 'applications', ['status'], unique=False)

    # Create alerts table
    op.create_table('alerts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('application_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('nrql_query', sa.Text(), nullable=False),
        sa.Column('thresholds', sa.JSON(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alerts_application_id'), 'alerts', ['application_id'], unique=False)
    op.create_index(op.f('ix_alerts_id'), 'alerts', ['id'], unique=False)
    op.create_index(op.f('ix_alerts_type'), 'alerts', ['type'], unique=False)

    # Create dashboards table
    op.create_table('dashboards',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('application_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('widgets', sa.JSON(), nullable=False),
        sa.Column('widgets_count', sa.Integer(), nullable=True),
        sa.Column('dashboard_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dashboards_application_id'), 'dashboards', ['application_id'], unique=False)
    op.create_index(op.f('ix_dashboards_id'), 'dashboards', ['id'], unique=False)
    op.create_index(op.f('ix_dashboards_type'), 'dashboards', ['type'], unique=False)

    # Create deployments table
    op.create_table('deployments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('application_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('components_deployed', sa.JSON(), nullable=True),
        sa.Column('deployment_type', sa.String(length=20), nullable=True),
        sa.Column('dry_run', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('estimated_completion', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deployments_application_id'), 'deployments', ['application_id'], unique=False)
    op.create_index(op.f('ix_deployments_id'), 'deployments', ['id'], unique=False)
    op.create_index(op.f('ix_deployments_status'), 'deployments', ['status'], unique=False)

    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.Column('api_key', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'], unique=False)
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)

    # Create compliance_reports table
    op.create_table('compliance_reports',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('application_id', sa.String(), nullable=False),
        sa.Column('standard', sa.String(length=50), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('compliant', sa.Boolean(), nullable=True),
        sa.Column('violations', sa.JSON(), nullable=True),
        sa.Column('requirements', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_compliance_reports_application_id'), 'compliance_reports', ['application_id'], unique=False)
    op.create_index(op.f('ix_compliance_reports_id'), 'compliance_reports', ['id'], unique=False)
    op.create_index(op.f('ix_compliance_reports_standard'), 'compliance_reports', ['standard'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_compliance_reports_standard'), table_name='compliance_reports')
    op.drop_index(op.f('ix_compliance_reports_id'), table_name='compliance_reports')
    op.drop_index(op.f('ix_compliance_reports_application_id'), table_name='compliance_reports')
    op.drop_table('compliance_reports')
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_id'), table_name='api_keys')
    op.drop_table('api_keys')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_deployments_status'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_id'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_application_id'), table_name='deployments')
    op.drop_table('deployments')
    op.drop_index(op.f('ix_dashboards_type'), table_name='dashboards')
    op.drop_index(op.f('ix_dashboards_id'), table_name='dashboards')
    op.drop_index(op.f('ix_dashboards_application_id'), table_name='dashboards')
    op.drop_table('dashboards')
    op.drop_index(op.f('ix_alerts_type'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_id'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_application_id'), table_name='alerts')
    op.drop_table('alerts')
    op.drop_index(op.f('ix_applications_status'), table_name='applications')
    op.drop_index(op.f('ix_applications_name'), table_name='applications')
    op.drop_index(op.f('ix_applications_id'), table_name='applications')
    op.drop_index(op.f('ix_applications_environment'), table_name='applications')
    op.drop_table('applications')
