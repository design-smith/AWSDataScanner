# AWS Data Scanner

A serverless PII (Personally Identifiable Information) detection system that scans S3 files for sensitive data using AWS Lambda, ECS Fargate, and RDS PostgreSQL.

## Demo Video

[![AWS Data Scanner Demo](https://img.youtube.com/vi/Q5tZH1NQfcI/maxresdefault.jpg)](https://youtu.be/Q5tZH1NQfcI)

**Watch the full demo:** [https://youtu.be/Q5tZH1NQfcI](https://youtu.be/Q5tZH1NQfcI)

## Overview

AWS Data Scanner automatically detects sensitive information in text files stored in S3, including:
- **Social Security Numbers (SSNs)**
- **Credit Card Numbers**
- **AWS Access Keys & Secret Keys**
- **Email Addresses**
- **US Phone Numbers**

The system processes files asynchronously using a distributed scanning architecture with SQS queues and ECS Fargate workers.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   S3 Files  │────▶│  API Gateway │────▶│   Lambda    │
│  (test-data)│     │   /scan      │     │  (scan.py)  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                 │
                    ┌────────────────────────────┘
                    │
                    ▼
            ┌───────────────┐
            │   SQS Queue   │
            │  (scan-jobs)  │
            └───────┬───────┘
                    │
            ┌───────┴────────┐
            ▼                ▼
    ┌──────────────┐  ┌──────────────┐
    │ ECS Worker 1 │  │ ECS Worker N │
    │  (Fargate)   │  │  (Fargate)   │
    └──────┬───────┘  └──────┬───────┘
           │                 │
           └────────┬────────┘
                    ▼
            ┌───────────────┐
            │  RDS Postgres │
            │   (findings)  │
            └───────────────┘
```

## Components

### 1. API Gateway + Lambda Functions
- **POST /scan** - Creates a scan job, lists S3 objects, enqueues messages to SQS
- **GET /jobs/{job_id}** - Returns job status and progress
- **GET /results** - Retrieves findings with filtering and pagination

### 2. SQS Queues
- **Main Queue** - Distributes scan tasks to workers
- **Dead Letter Queue (DLQ)** - Captures failed messages for investigation

### 3. ECS Fargate Workers
- Polls SQS for scan jobs
- Downloads files from S3 (streaming for large files)
- Runs regex-based PII detectors
- Writes findings to RDS PostgreSQL

### 4. RDS PostgreSQL Database
**Tables:**
- `jobs` - Scan job metadata and status
- `job_objects` - Individual S3 files to scan
- `findings` - Detected PII with context and location

**Unique Constraint:** Deduplicates findings on `(object_id, finding_type, line_number, column_start, value_hash)`

### 5. Infrastructure (Terraform)
- VPC with public/private subnets
- NAT Gateways for private subnet internet access
- Security groups for Lambda, ECS, and RDS
- IAM roles with least-privilege permissions
- ECR repository for Docker images

## Detection Capabilities

The scanner uses regex patterns to detect:

| Type | Pattern | Example |
|------|---------|---------|
| SSN | `\d{3}-\d{2}-\d{4}` | 123-45-6789 |
| Credit Card | Luhn algorithm validation | 4532-1234-5678-9010 |
| AWS Access Key | `AKIA[0-9A-Z]{16}` | AKIAIOSFODNN7EXAMPLE |
| AWS Secret Key | 40-char base64 | wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY |
| Email | RFC 5322 compliant | user@example.com |
| US Phone | Various formats | (555) 123-4567 |

All sensitive values are **hashed (SHA-256)** before storage for security.

## Technology Stack

- **Languages:** Python 3.11
- **AWS Services:** Lambda, ECS Fargate, RDS PostgreSQL, S3, SQS, API Gateway, ECR
- **Infrastructure:** Terraform
- **Database:** PostgreSQL 15.8 with SQLAlchemy ORM
- **Containerization:** Docker (multi-stage builds)
- **Libraries:** boto3, psycopg2, regex

## Deployment

Infrastructure is provisioned using Terraform:

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Lambda functions and ECS workers are deployed via AWS CLI and Docker.

## Security Features

✅ **Private RDS** - Database in private subnets, not internet-accessible
✅ **VPC Security Groups** - Strict ingress/egress rules
✅ **Value Hashing** - PII values stored as SHA-256 hashes
✅ **IAM Least Privilege** - Scoped permissions for each component
✅ **No Secrets in Code** - Environment variables for credentials
✅ **DLQ Monitoring** - Failed messages captured for investigation

## Performance

- **Throughput:** 5 concurrent ECS workers (configurable)
- **Scalability:** Auto-scales with SQS queue depth
- **File Size Limit:** 500 MB (configurable)
- **Streaming:** Processes large files in 10 MB chunks

## API Usage

### Create Scan Job
```bash
curl -X POST "https://{api-gateway-url}/dev/scan" \
  -H "Content-Type: application/json" \
  -d '{"job_name": "My Scan", "s3_bucket": "my-bucket", "s3_prefix": "data/"}'
```

### Check Job Status
```bash
curl "https://{api-gateway-url}/dev/jobs/{job_id}"
```

### Get Results
```bash
curl "https://{api-gateway-url}/dev/results?job_id={job_id}&limit=100&finding_type=ssn"
```

## Monitoring

- **CloudWatch Logs:** Lambda and ECS worker logs
- **SQS Metrics:** Queue depth and DLQ messages
- **RDS Metrics:** Database performance and connections

## Project Structure

```
AWSDataScanner/
├── api-handler/          # Lambda function code
│   ├── src/             # Python source files
│   └── requirements.txt
├── scanner-worker/       # ECS worker code
│   ├── src/             # Scanner implementation
│   ├── Dockerfile       # Multi-stage build
│   └── requirements.txt
├── terraform/           # Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   └── modules/
├── database/            # SQL schemas
│   ├── schema.sql
│   └── indexes.sql
├── scripts/             # Utility scripts
│   └── generate_test_files.py
└── README.md
```
---

**Built with ❤️ using AWS serverless technologies**
