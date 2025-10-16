# Terraform Modules Documentation

## Module Overview

### 1. Networking Module (`modules/networking/`)

Creates the VPC infrastructure with public and private subnets across multiple availability zones.

**Resources Created:**
- VPC with DNS support enabled
- 2 Public subnets (for bastion, NAT Gateway)
- 2 Private subnets (for RDS, ECS, Lambda)
- Internet Gateway for public subnet internet access
- NAT Gateway for private subnet internet access
- Route tables for public and private subnets
- Subnet route table associations

**Outputs:**
- `vpc_id`: VPC identifier
- `public_subnet_ids`: List of public subnet IDs
- `private_subnet_ids`: List of private subnet IDs
- `nat_gateway_id`: NAT Gateway identifier
- `internet_gateway_id`: Internet Gateway identifier

---

### 2. Data Module (`modules/data/`)

Manages data storage resources including PostgreSQL database and S3 bucket.

**Resources Created:**

**RDS PostgreSQL:**
- PostgreSQL 15.4 engine
- Deployed in private subnets only
- Storage encrypted with AES256
- Security group allowing access from ECS and bastion
- DB subnet group spanning multiple AZs
- 7-day backup retention
- Single-AZ deployment (dev mode)
- CloudWatch logs enabled

**S3 Bucket:**
- Versioning enabled
- Server-side encryption (AES256)
- Public access blocked
- Lifecycle policy to expire old versions after 30 days
- Bucket naming includes account ID for uniqueness

**Outputs:**
- `rds_endpoint`: Full RDS endpoint (host:port)
- `rds_address`: RDS hostname only
- `rds_port`: RDS port (5432)
- `s3_bucket_name`: S3 bucket name
- `s3_bucket_arn`: S3 bucket ARN
- `db_security_group_id`: RDS security group ID

---

### 3. Messaging Module (`modules/messaging/`)

Implements SQS-based message queuing for scan job processing.

**Resources Created:**

**Main SQS Queue:**
- 4-day message retention
- Long polling enabled (20s)
- Redrive policy to DLQ after 3 failed attempts
- Configurable visibility timeout

**Dead Letter Queue (DLQ):**
- 14-day message retention
- Receives failed messages from main queue

**Queue Policy:**
- Allows Lambda and ECS to send/receive/delete messages
- Restricted to specific queue ARN

**Outputs:**
- `sqs_queue_url`: Main queue URL
- `sqs_queue_arn`: Main queue ARN
- `sqs_queue_name`: Main queue name
- `sqs_dlq_url`: DLQ URL
- `sqs_dlq_arn`: DLQ ARN
- `sqs_dlq_name`: DLQ name

---

### 4. Compute Module (`modules/compute/`)

The most complex module handling container orchestration, serverless functions, and bastion access.

**Resources Created:**

**ECR Repository:**
- Private Docker image registry
- Image scanning on push enabled
- Lifecycle policy:
  - Keep last 10 tagged images
  - Expire untagged images after 7 days
- AES256 encryption

**ECS Fargate Cluster & Service:**
- Fargate cluster with Container Insights
- Task definition for scanner worker:
  - Configurable CPU (default 256 units)
  - Configurable memory (default 512 MB)
  - Environment variables for DB, SQS, S3
  - CloudWatch logs integration
- ECS service in private subnets
- Auto-scaling based on SQS queue depth:
  - Scales up when queue has messages
  - Scales down to 0 when queue is empty
  - Target tracking scaling policy

**Lambda Functions (3):**
1. **Scan Lambda**: Initiates new scan jobs
2. **Jobs Lambda**: Retrieves job status
3. **Results Lambda**: Fetches scan results

All Lambda functions:
- Python 3.11 runtime
- 256 MB memory
- 30s timeout
- Deployed in VPC for RDS access
- Environment variables for DB connection
- Placeholder code (to be replaced)

**Bastion Host:**
- Amazon Linux 2 AMI
- t2.micro instance
- Deployed in public subnet
- PostgreSQL 15 client pre-installed
- SSH access via key pair

**Security Groups:**
- ECS Security Group: Allows all outbound
- Lambda Security Group: Allows all outbound
- Bastion Security Group: SSH (port 22) inbound, all outbound

**IAM Roles:**
- ECS Task Execution Role: Pull images from ECR
- ECS Task Role: Access SQS, S3, CloudWatch
- Lambda Execution Role: VPC access, SQS, S3, CloudWatch

**Outputs:**
- `ecr_repository_url`: ECR repository URL for Docker push
- `ecs_cluster_name`: ECS cluster name
- `ecs_service_name`: ECS service name
- `scan_lambda_arn`, `scan_lambda_name`, `scan_lambda_invoke_arn`
- `jobs_lambda_arn`, `jobs_lambda_name`, `jobs_lambda_invoke_arn`
- `results_lambda_arn`, `results_lambda_name`, `results_lambda_invoke_arn`
- `bastion_public_ip`: Bastion host public IP
- `ecs_security_group_id`: ECS security group ID
- `lambda_security_group_id`: Lambda security group ID
- `bastion_security_group_id`: Bastion security group ID

---

## Module Dependencies

```
networking (no dependencies)
    ↓
    ├─→ data (depends on: networking)
    ├─→ messaging (no dependencies)
    └─→ compute (depends on: networking, messaging, data)
```

## Security Features

### Network Security
- RDS in private subnets only (no public access)
- ECS tasks in private subnets
- Lambda functions in private subnets
- Security groups with least-privilege access
- NAT Gateway for private subnet internet access

### Data Security
- RDS encryption at rest
- S3 bucket encryption (AES256)
- S3 bucket versioning enabled
- Public access blocked on S3
- Sensitive variables marked as sensitive

### Access Control
- IAM roles follow least-privilege principle
- Service-specific IAM policies
- SQS queue policy restricts access
- Bastion host as single entry point for DB access

## Cost Optimization Features

### Development Environment
- db.t3.micro for RDS (~$15/month)
- ECS scales to 0 when idle (~$0/month when not running)
- t2.micro bastion (~$8/month)
- Single NAT Gateway (~$32/month)
- Lambda free tier eligible (256 MB)

### Total Dev Cost: ~$30-50/month

### Production Recommendations
- Multi-AZ RDS for high availability
- Multiple NAT Gateways for HA
- Larger instance types based on load
- Reserved instances for predictable workloads
- S3 lifecycle policies for cold storage

## Monitoring and Logging

All modules include:
- CloudWatch log groups with 7-day retention
- ECS Container Insights enabled
- Lambda CloudWatch integration
- RDS CloudWatch logs for PostgreSQL

## Scaling Configuration

### ECS Auto-Scaling
- **Metric**: SQS ApproximateNumberOfMessagesVisible
- **Target**: 5 messages per task (configurable)
- **Scale Out**: 60s cooldown
- **Scale In**: 300s cooldown
- **Min Tasks**: 0 (can scale to zero)
- **Max Tasks**: 5 (dev), 10 (configurable)

### Lambda Scaling
- Automatic scaling up to account limits
- Concurrent executions throttled by AWS
- No manual configuration needed

## High Availability Considerations

**Current Setup (Dev):**
- Single AZ for RDS
- Single NAT Gateway
- Limited HA

**Production Recommendations:**
- Multi-AZ RDS deployment
- NAT Gateway in each AZ
- Application Load Balancer for ECS (if needed)
- Route53 health checks
- Cross-region backup for S3
