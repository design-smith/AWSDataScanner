CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX idx_jobs_bucket_prefix ON jobs(s3_bucket, s3_prefix);

CREATE INDEX idx_job_objects_job_id ON job_objects(job_id);
CREATE INDEX idx_job_objects_status ON job_objects(status);
CREATE INDEX idx_job_objects_job_status ON job_objects(job_id, status);
CREATE INDEX idx_job_objects_scanned_at ON job_objects(scanned_at DESC);

CREATE INDEX idx_findings_object_id ON findings(object_id);
CREATE INDEX idx_findings_job_id ON findings(job_id);
CREATE INDEX idx_findings_type ON findings(finding_type);
CREATE INDEX idx_findings_job_type ON findings(job_id, finding_type);
CREATE INDEX idx_findings_detected_at ON findings(detected_at DESC);

CREATE INDEX idx_findings_job_type_id ON findings(job_id, finding_type, finding_id DESC);

CREATE INDEX idx_findings_value_hash ON findings(value_hash);

CREATE INDEX idx_active_jobs ON jobs(job_id) WHERE status IN ('pending', 'running');
CREATE INDEX idx_pending_objects ON job_objects(object_id, job_id) WHERE status = 'pending';

CREATE INDEX idx_failed_objects ON job_objects(job_id, object_id) WHERE status = 'failed';