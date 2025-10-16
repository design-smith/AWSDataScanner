#!/bin/bash
# Database Initialization Script for AWS CloudShell
# This script runs in CloudShell which has psql pre-installed and VPC access

set -e

DB_HOST="aws-data-scanner-db-dev.covom8oag137.us-east-1.rds.amazonaws.com"
DB_PORT="5432"
DB_NAME="datascanner"
DB_USER="dbadmin"
DB_PASSWORD="ChangeMe123!"

echo "=== Initializing AWS Data Scanner Database ==="
echo "Host: $DB_HOST"
echo "Database: $DB_NAME"
echo ""

# Test connection
echo "Testing database connection..."
export PGPASSWORD="$DB_PASSWORD"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" || {
    echo "❌ Connection failed. Ensure CloudShell is in the same VPC or has network access."
    exit 1
}

echo "✅ Connection successful!"
echo ""

# Create schema
echo "Creating database schema..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_name VARCHAR(255) NOT NULL,
    s3_bucket VARCHAR(255) NOT NULL,
    s3_prefix VARCHAR(1024),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    total_objects INTEGER DEFAULT 0,
    completed_objects INTEGER DEFAULT 0,
    failed_objects INTEGER DEFAULT 0,
    total_findings INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);

-- Job objects table
CREATE TABLE IF NOT EXISTS job_objects (
    object_id BIGSERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    s3_key VARCHAR(1024) NOT NULL,
    file_size_bytes BIGINT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    findings_count INTEGER DEFAULT 0,
    error_message TEXT,
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    scanned_at TIMESTAMP,
    CONSTRAINT valid_object_status CHECK (status IN ('pending', 'scanning', 'completed', 'failed', 'skipped')),
    CONSTRAINT unique_job_object UNIQUE(job_id, s3_key)
);

-- Findings table
CREATE TABLE IF NOT EXISTS findings (
    finding_id BIGSERIAL PRIMARY KEY,
    object_id BIGINT NOT NULL REFERENCES job_objects(object_id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    finding_type VARCHAR(50) NOT NULL,
    value_hash VARCHAR(64) NOT NULL,
    line_number INTEGER,
    column_start INTEGER,
    column_end INTEGER,
    context TEXT,
    confidence VARCHAR(20) DEFAULT 'high',
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_finding_type CHECK (finding_type IN ('ssn', 'credit_card', 'aws_access_key', 'aws_secret_key', 'email', 'phone_us', 'phone_intl')),
    CONSTRAINT valid_confidence CHECK (confidence IN ('low', 'medium', 'high')),
    CONSTRAINT unique_finding UNIQUE(object_id, finding_type, line_number, column_start, value_hash)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_objects_job_id ON job_objects(job_id);
CREATE INDEX IF NOT EXISTS idx_job_objects_status ON job_objects(status);
CREATE INDEX IF NOT EXISTS idx_findings_object_id ON findings(object_id);
CREATE INDEX IF NOT EXISTS idx_findings_job_id ON findings(job_id);
CREATE INDEX IF NOT EXISTS idx_findings_type ON findings(finding_type);

-- Trigger function to update job timestamps
CREATE OR REPLACE FUNCTION update_job_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update job timestamps
DROP TRIGGER IF EXISTS trigger_update_job_timestamp ON jobs;
CREATE TRIGGER trigger_update_job_timestamp
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_job_timestamp();

-- Trigger function to update job statistics
CREATE OR REPLACE FUNCTION update_job_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        UPDATE jobs
        SET
            completed_objects = (
                SELECT COUNT(*)
                FROM job_objects
                WHERE job_id = NEW.job_id AND status = 'completed'
            ),
            failed_objects = (
                SELECT COUNT(*)
                FROM job_objects
                WHERE job_id = NEW.job_id AND status = 'failed'
            ),
            total_findings = (
                SELECT COUNT(*)
                FROM findings
                WHERE job_id = NEW.job_id
            )
        WHERE job_id = NEW.job_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update job stats when objects change
DROP TRIGGER IF EXISTS trigger_update_job_stats_on_object ON job_objects;
CREATE TRIGGER trigger_update_job_stats_on_object
    AFTER INSERT OR UPDATE ON job_objects
    FOR EACH ROW
    EXECUTE FUNCTION update_job_stats();

-- Trigger to auto-update job stats when findings change
DROP TRIGGER IF EXISTS trigger_update_job_stats_on_finding ON findings;
CREATE TRIGGER trigger_update_job_stats_on_finding
    AFTER INSERT OR DELETE ON findings
    FOR EACH ROW
    EXECUTE FUNCTION update_job_stats();
EOF

echo "✅ Schema created successfully!"
echo ""

# Verify tables
echo "Verifying tables..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt"

echo ""
echo "=== Database Initialization Complete ==="
echo "You can now proceed with building the Docker image and deploying Lambda functions."
