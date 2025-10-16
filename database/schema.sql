CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


CREATE TABLE jobs (
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

CREATE TABLE job_objects (
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

CREATE TABLE findings (
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

CREATE OR REPLACE FUNCTION update_job_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        UPDATE jobs
        SET
            completed_objects = (
                SELECT COUNT(*) FROM job_objects
                WHERE job_id = NEW.job_id AND status = 'completed'
            ),
            failed_objects = (
                SELECT COUNT(*) FROM job_objects
                WHERE job_id = NEW.job_id AND status = 'failed'
            ),
            total_findings = (
                SELECT COUNT(*) FROM findings
                WHERE job_id = NEW.job_id
            ),
            status = CASE
                WHEN (SELECT COUNT(*) FROM job_objects WHERE job_id = NEW.job_id AND status IN ('pending', 'scanning')) = 0
                THEN 'completed'
                ELSE 'running'
            END,
            updated_at = CURRENT_TIMESTAMP,
            completed_at = CASE
                WHEN (SELECT COUNT(*) FROM job_objects WHERE job_id = NEW.job_id AND status IN ('pending', 'scanning')) = 0
                THEN CURRENT_TIMESTAMP
                ELSE completed_at
            END
        WHERE job_id = NEW.job_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_job_stats
AFTER INSERT OR UPDATE OF status ON job_objects
FOR EACH ROW
EXECUTE FUNCTION update_job_stats();

CREATE OR REPLACE FUNCTION update_object_findings_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE job_objects
        SET findings_count = findings_count + 1
        WHERE object_id = NEW.object_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE job_objects
        SET findings_count = findings_count - 1
        WHERE object_id = OLD.object_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_findings_count
AFTER INSERT OR DELETE ON findings
FOR EACH ROW
EXECUTE FUNCTION update_object_findings_count();