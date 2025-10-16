"""
Lambda function to initialize database schema
This will be deployed temporarily to initialize the DB
"""

import json
import psycopg2

def lambda_handler(event, context):
    """Initialize database with schema and indexes"""

    # Database connection
    DB_HOST = "aws-data-scanner-db-dev.covom8oag137.us-east-1.rds.amazonaws.com"
    DB_NAME = "datascanner"
    DB_USER = "dbadmin"
    DB_PASSWORD = "ChangeMe123!"

    # Schema SQL
    schema_sql = """
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
    """

    # Indexes SQL
    indexes_sql = """
    CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
    CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_job_objects_job_id ON job_objects(job_id);
    CREATE INDEX IF NOT EXISTS idx_job_objects_status ON job_objects(status);
    CREATE INDEX IF NOT EXISTS idx_findings_object_id ON findings(object_id);
    CREATE INDEX IF NOT EXISTS idx_findings_job_id ON findings(job_id);
    CREATE INDEX IF NOT EXISTS idx_findings_type ON findings(finding_type);
    CREATE INDEX IF NOT EXISTS idx_findings_detected_at ON findings(detected_at DESC);
    """

    try:
        # Connect
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Execute schema
        cur.execute(schema_sql)

        # Execute indexes
        cur.execute(indexes_sql)

        # Verify
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]

        cur.close()
        conn.close()

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Database initialized successfully!',
                'tables': tables
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
