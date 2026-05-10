-- Neomnix Database Initialization Script
-- Creates initial schema and roles for multi-tenant compliance platform

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS audit;

-- Tenant table
CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    logo_url VARCHAR(255),
    billing_email VARCHAR(255) NOT NULL,
    tier VARCHAR(50) DEFAULT 'starter',
    stripe_customer_id VARCHAR(255) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_stripe_customer_id ON tenants(stripe_customer_id);

-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_product_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'inactive',
    tier VARCHAR(50) DEFAULT 'starter',
    price_per_month NUMERIC(10,2),
    seats_limit INTEGER DEFAULT 5,
    started_at TIMESTAMP,
    ends_at TIMESTAMP,
    trial_ends_at TIMESTAMP,
    auto_renew BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_subscriptions_tenant_id ON subscriptions(tenant_id);
CREATE INDEX idx_subscriptions_stripe_subscription_id ON subscriptions(stripe_subscription_id);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'analyst',
    is_active BOOLEAN DEFAULT TRUE,
    force_password_change BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, email)
);

CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);

-- Scan jobs table
CREATE TABLE IF NOT EXISTS scan_jobs (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    target VARCHAR(255) NOT NULL,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    initiated_by VARCHAR(255),
    findings JSONB DEFAULT '[]',
    compliance_report JSONB,
    final_intensity INTEGER,
    confidence_score NUMERIC(5,2)
);

CREATE INDEX idx_scan_jobs_tenant_id ON scan_jobs(tenant_id);
CREATE INDEX idx_scan_jobs_target ON scan_jobs(target);
CREATE INDEX idx_scan_jobs_status ON scan_jobs(status);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_email VARCHAR(255) NOT NULL,
    action VARCHAR(255),
    resource_id VARCHAR(255),
    details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

CREATE INDEX idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_user_email ON audit_logs(user_email);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);

-- Unified controls table
CREATE TABLE IF NOT EXISTS unified_controls (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    priority_level VARCHAR(50) DEFAULT 'medium',
    overlap_score INTEGER DEFAULT 0,
    required_evidence JSONB DEFAULT '[]',
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_unified_controls_category ON unified_controls(category);

-- Control citations table
CREATE TABLE IF NOT EXISTS control_citations (
    id SERIAL PRIMARY KEY,
    control_id VARCHAR(36) NOT NULL REFERENCES unified_controls(id) ON DELETE CASCADE,
    framework VARCHAR(100) NOT NULL,
    citation VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_control_citations_control_id ON control_citations(control_id);
CREATE INDEX idx_control_citations_framework ON control_citations(framework);

-- Control mappings table
CREATE TABLE IF NOT EXISTS control_mappings (
    id SERIAL PRIMARY KEY,
    source_framework VARCHAR(100) NOT NULL,
    source_control_id VARCHAR(36) NOT NULL REFERENCES unified_controls(id) ON DELETE CASCADE,
    target_framework VARCHAR(100) NOT NULL,
    target_control_id VARCHAR(36) NOT NULL REFERENCES unified_controls(id) ON DELETE CASCADE,
    confidence_score NUMERIC(5,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_control_mappings_source ON control_mappings(source_control_id);
CREATE INDEX idx_control_mappings_target ON control_mappings(target_control_id);

-- Create audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_func() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_logs (tenant_id, user_email, action, resource_id, details, ip_address)
    VALUES (
        COALESCE(NEW.tenant_id, OLD.tenant_id),
        CURRENT_USER,
        TG_ARGV[0],
        NEW.id::text,
        jsonb_build_object('old', to_jsonb(OLD), 'new', to_jsonb(NEW)),
        inet_client_addr()::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA audit FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA audit FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA audit FROM PUBLIC;

DO $$
BEGIN
    RAISE NOTICE 'Neomnix database initialized successfully';
END
$$;
