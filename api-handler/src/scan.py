import json
import logging
import psycopg2

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def lambda_handler(event, context):
    # Initialize database if needed
    try:
        conn = psycopg2.connect(
            host='aws-data-scanner-db-dev.covom8oag137.us-east-1.rds.amazonaws.com',
            port=5432,
            database='datascanner',
            user='dbadmin',
            password='ChangeMe123!',
            connect_timeout=10
        )
        cur = conn.cursor()
        
        # Create tables
        cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        cur.execute('''CREATE TABLE IF NOT EXISTS jobs (
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
            completed_at TIMESTAMP
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS job_objects (
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
            CONSTRAINT unique_job_object UNIQUE(job_id, s3_key)
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS findings (
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
            detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.commit()
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'success': True, 'message': 'Database initialized', 'tables': tables})
        }
    except Exception as e:
        logger.error(f"Database init error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }

