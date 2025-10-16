# Next Steps to Complete Testing

## Current Status

✅ **Completed:**
- Terraform infrastructure deployed (66 resources)
- Lambda API handler code deployed to all 3 functions
- 500 test files with PII generated and uploaded to S3
- Database initialization attempted via EC2

❌ **Blockers:**
1. **Database tables not confirmed** - Lambda returns 500 errors (likely DB connection issues)
2. **Scanner worker Docker image not built** - Docker Desktop not running

## Immediate Actions Required

### Option 1: Start Docker Desktop and Build Scanner Worker (Recommended - 10 minutes)

1. **Start Docker Desktop**
   - Open Docker Desktop application
   - Wait for it to fully start

2. **Build and push scanner worker image:**
   ```bash
   cd c:/Users/zwzek/OneDrive/Desktop/AWSDataScanner/scanner-worker

   # Login to ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 580165054001.dkr.ecr.us-east-1.amazonaws.com

   # Build image
   docker build -t aws-data-scanner-scanner-worker-dev .

   # Tag image
   docker tag aws-data-scanner-scanner-worker-dev:latest 580165054001.dkr.ecr.us-east-1.amazonaws.com/aws-data-scanner-scanner-worker-dev:latest

   # Push to ECR
   docker push 580165054001.dkr.ecr.us-east-1.amazonaws.com/aws-data-scanner-scanner-worker-dev:latest
   ```

3. **Verify database manually through AWS Console:**
   - Go to RDS Console
   - Click on `aws-data-scanner-db-dev`
   - Try Query Editor (if available) or use temporary bastion approach
   - Run: `SELECT tablename FROM pg_tables WHERE schemaname='public';`
   - Should see: `findings`, `job_objects`, `jobs`

4. **If database tables don't exist, create them:**

   **Option A - Via temporary EC2 in VPC:**
   ```bash
   # Launch temp EC2 (already done once, can retry)
   # SSH or use Systems Manager Session Manager to connect
   # Run the SQL from database/schema.sql
   ```

   **Option B - Make RDS temporarily public:**
   ```bash
   # Temporarily enable public access
   aws rds modify-db-instance \
     --db-instance-identifier aws-data-scanner-db-dev \
     --publicly-accessible \
     --apply-immediately

   # Wait 60 seconds
   sleep 60

   # Initialize database
   python scripts/init_database.py

   # Make private again
   aws rds modify-db-instance \
     --db-instance-identifier aws-data-scanner-db-dev \
     --no-publicly-accessible \
     --apply-immediately
   ```

5. **Test the full workflow:**
   ```bash
   # Trigger scan
   curl -X POST https://a0fhwoouck.execute-api.us-east-1.amazonaws.com/dev/scan \
     -H "Content-Type: application/json" \
     -d '{
       "job_name": "Full Test Scan",
       "s3_bucket": "aws-data-scanner-data-dev-580165054001",
       "s3_prefix": "test-data/"
     }'

   # Capture job_id from response, then check status
   JOB_ID="<paste-job-id-here>"
   curl https://a0fhwoouck.execute-api.us-east-1.amazonaws.com/dev/jobs/$JOB_ID

   # Wait for completion, then get results
   curl "https://a0fhwoouck.execute-api.us-east-1.amazonaws.com/dev/results?job_id=$JOB_ID&limit=50"

   # Check SQS metrics
   aws cloudwatch get-metric-statistics \
     --namespace AWS/SQS \
     --metric-name ApproximateNumberOfMessagesVisible \
     --dimensions Name=QueueName,Value=aws-data-scanner-scan-jobs-dev \
     --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Average
   ```

### Option 2: Simplified Verification Without Docker (15 minutes)

If you can't run Docker right now, you can still verify most components:

1. **Fix database initialization** using Option B above (temporarily public RDS)

2. **Test API endpoints without scanner worker:**
   ```bash
   # Test that scan endpoint creates job
   curl -X POST https://a0fhwoouck.execute-api.us-east-1.amazonaws.com/dev/scan \
     -H "Content-Type: application/json" \
     -d '{
       "job_name": "API Test",
       "s3_bucket": "aws-data-scanner-data-dev-580165054001",
       "s3_prefix": "test-data/"
     }'

   # Should return job_id and status="pending"
   ```

3. **Verify SQS messages were created:**
   ```bash
   aws sqs get-queue-attributes \
     --queue-url https://sqs.us-east-1.amazonaws.com/580165054001/aws-data-scanner-scan-jobs-dev \
     --attribute-names ApproximateNumberOfMessages

   # Should show ~500 messages
   ```

4. **Build Docker worker later** when Docker Desktop is available

## Key Files Reference

- **Database Schema:** `database/schema.sql`, `database/indexes.sql`
- **Scanner Worker:** `scanner-worker/` (needs Docker to build)
- **API Handlers:** `api-handler/src/` (already deployed)
- **Test Files:** `test-data/` (already uploaded to S3)
- **Terraform Outputs:**
  - API URL: https://a0fhwoouck.execute-api.us-east-1.amazonaws.com/dev
  - S3 Bucket: aws-data-scanner-data-dev-580165054001
  - SQS Queue: https://sqs.us-east-1.amazonaws.com/580165054001/aws-data-scanner-scan-jobs-dev
  - RDS Host: aws-data-scanner-db-dev.covom8oag137.us-east-1.rds.amazonaws.com:5432

## Troubleshooting

**Lambda returns 500 error:**
- Check CloudWatch Logs: `/aws/lambda/aws-data-scanner-scan-dev`
- Most likely cause: Database connection failure or missing tables

**SQS messages not processing:**
- Scanner worker not running (ECS tasks = 0)
- Caused by: No Docker image in ECR

**Database connection timeout:**
- RDS is in private subnet
- Solutions: EC2 bastion, temporary public access, or Lambda-based init

## Expected Test Results

When fully working:
- POST /scan returns job_id
- SQS receives 500 messages
- ECS auto-scales to process queue (0→10 tasks)
- GET /jobs/{job_id} shows progress
- After ~5-10 minutes, status="completed"
- GET /results returns findings:
  - SSNs: ~hundreds
  - Credit cards: ~hundreds
  - Emails: ~thousands
  - AWS keys: ~hundreds
  - Phone numbers: ~hundreds
