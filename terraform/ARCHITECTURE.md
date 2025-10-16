# AWS Data Scanner - Infrastructure Architecture

## Visual Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            AWS Cloud (us-east-1)                         │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    VPC (10.0.0.0/16)                             │   │
│  │                                                                   │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │              Public Subnets (2 AZs)                      │   │   │
│  │  │                                                           │   │   │
│  │  │  ┌──────────────────┐     ┌────────────────────┐        │   │   │
│  │  │  │   Bastion Host   │     │   NAT Gateway      │        │   │   │
│  │  │  │   (t2.micro)     │     │                    │        │   │   │
│  │  │  │   SSH Access     │     │   Elastic IP       │        │   │   │
│  │  │  └──────────────────┘     └────────────────────┘        │   │   │
│  │  │                                     │                     │   │   │
│  │  └─────────────────────────────────────┼─────────────────────┘   │   │
│  │                                        │                          │   │
│  │  ┌─────────────────────────────────────┼─────────────────────┐   │   │
│  │  │              Private Subnets (2 AZs)│                     │   │   │
│  │  │                                      ▼                     │   │   │
│  │  │  ┌──────────────────┐     ┌────────────────────┐         │   │   │
│  │  │  │   ECS Fargate    │     │   RDS PostgreSQL   │         │   │   │
│  │  │  │   Scanner Worker │     │   (db.t3.micro)    │         │   │   │
│  │  │  │   Auto Scaling   │────▶│   Private Only     │         │   │   │
│  │  │  │   (0-5 tasks)    │     │   Encrypted        │         │   │   │
│  │  │  └──────────────────┘     └────────────────────┘         │   │   │
│  │  │           │                                               │   │   │
│  │  │  ┌────────┴──────────┐                                   │   │   │
│  │  │  │   Lambda Functions │                                  │   │   │
│  │  │  │   - Scan           │                                  │   │   │
│  │  │  │   - Jobs           │                                  │   │   │
│  │  │  │   - Results        │                                  │   │   │
│  │  │  └────────────────────┘                                  │   │   │
│  │  │                                                           │   │   │
│  │  └───────────────────────────────────────────────────────────┘   │   │
│  │                                                                   │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌───────────────────────┐   ┌──────────────────┐   ┌────────────────┐ │
│  │   API Gateway         │   │   SQS Queue      │   │   S3 Bucket    │ │
│  │   REST API            │   │   Scan Jobs      │   │   Data Storage │ │
│  │   /scan, /jobs        │   │   + DLQ          │   │   Encrypted    │ │
│  │   /results            │   │                  │   │   Versioned    │ │
│  └───────────────────────┘   └──────────────────┘   └────────────────┘ │
│                                                                           │
│  ┌───────────────────────┐                                               │
│  │   ECR Repository      │                                               │
│  │   Docker Images       │                                               │
│  │   Scan on Push        │                                               │
│  └───────────────────────┘                                               │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘

                                      │
                                      │ Internet
                                      ▼
                              ┌───────────────┐
                              │   End Users   │
                              │   API Clients │
                              └───────────────┘
```

## Data Flow

### 1. Scan Request Flow

```
User/Client
    │
    ├─▶ POST /scan
    │
    ▼
API Gateway
    │
    ├─▶ Invoke Lambda (scan)
    │
    ▼
Lambda Function (scan)
    │
    ├─▶ Validate request
    ├─▶ Create job record in RDS
    ├─▶ Send message to SQS
    │
    ▼
SQS Queue (scan-jobs)
    │
    ├─▶ Message available
    │
    ▼
ECS Fargate (scanner-worker)
    │
    ├─▶ Poll SQS for messages
    ├─▶ Fetch data from S3
    ├─▶ Process/scan data
    ├─▶ Store results in RDS
    ├─▶ Delete message from SQS
    │
    ▼
Results stored in RDS
```

### 2. Job Status Check Flow

```
User/Client
    │
    ├─▶ GET /jobs/{job_id}
    │
    ▼
API Gateway
    │
    ├─▶ Invoke Lambda (jobs)
    │
    ▼
Lambda Function (jobs)
    │
    ├─▶ Query RDS for job status
    ├─▶ Return job details
    │
    ▼
Response to Client
```

### 3. Results Retrieval Flow

```
User/Client
    │
    ├─▶ GET /results?job_id=xxx
    │
    ▼
API Gateway
    │
    ├─▶ Invoke Lambda (results)
    │
    ▼
Lambda Function (results)
    │
    ├─▶ Query RDS for results
    ├─▶ Paginate results
    ├─▶ Return formatted data
    │
    ▼
Response to Client
```

## Network Architecture

### Public Subnets (10.0.1.0/24, 10.0.2.0/24)
- **Purpose**: Resources that need direct internet access
- **Components**:
  - Bastion Host (SSH gateway)
  - NAT Gateway (for private subnet internet)
- **Routing**: Internet Gateway → Public Subnets

### Private Subnets (10.0.10.0/24, 10.0.11.0/24)
- **Purpose**: Internal resources with no direct internet access
- **Components**:
  - RDS PostgreSQL (database)
  - ECS Tasks (scanner workers)
  - Lambda Functions (API handlers)
- **Routing**: NAT Gateway → Internet (outbound only)

## Security Architecture

### Security Groups

#### 1. RDS Security Group
```
Inbound:
  - PostgreSQL (5432) from ECS Security Group
  - PostgreSQL (5432) from Lambda Security Group
  - PostgreSQL (5432) from Bastion Security Group

Outbound:
  - All traffic allowed
```

#### 2. ECS Security Group
```
Inbound:
  - None (no inbound needed)

Outbound:
  - All traffic allowed (for RDS, S3, SQS, ECR access)
```

#### 3. Lambda Security Group
```
Inbound:
  - None (API Gateway invokes via AWS service network)

Outbound:
  - All traffic allowed (for RDS, S3, SQS access)
```

#### 4. Bastion Security Group
```
Inbound:
  - SSH (22) from 0.0.0.0/0 (restrict in production!)

Outbound:
  - All traffic allowed
```

## IAM Roles and Policies

### 1. ECS Task Execution Role
**Purpose**: Pull Docker images from ECR and write logs

**Permissions**:
- `ecr:GetAuthorizationToken`
- `ecr:BatchCheckLayerAvailability`
- `ecr:GetDownloadUrlForLayer`
- `ecr:BatchGetImage`
- `logs:CreateLogStream`
- `logs:PutLogEvents`

### 2. ECS Task Role
**Purpose**: Application-level permissions for scanner worker

**Permissions**:
- `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:ChangeMessageVisibility`
- `s3:GetObject`, `s3:PutObject`, `s3:ListBucket`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### 3. Lambda Execution Role
**Purpose**: Lambda function runtime permissions

**Permissions**:
- VPC networking permissions (ENI management)
- `sqs:SendMessage` (scan Lambda)
- `s3:GetObject`, `s3:PutObject`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

## Auto Scaling Configuration

### ECS Auto Scaling

**Trigger**: SQS Queue Depth

```
Target Metric: ApproximateNumberOfMessagesVisible
Target Value: 5 messages per task
Min Capacity: 0 tasks
Max Capacity: 5 tasks (dev), 10 tasks (configurable)

Scaling Behavior:
- Queue depth = 0       → 0 tasks (cost optimization)
- Queue depth = 1-5     → 1 task
- Queue depth = 6-10    → 2 tasks
- Queue depth = 11-15   → 3 tasks
- ...and so on up to max

Scale Out Cooldown: 60 seconds
Scale In Cooldown: 300 seconds (5 minutes)
```

## High Availability Considerations

### Current Setup (Dev)
- **Single AZ**: RDS in single availability zone
- **Single NAT**: One NAT Gateway
- **Cost**: ~$63-68/month
- **Downtime Risk**: Moderate

### Production Recommendations
- **Multi-AZ RDS**: Automatic failover
- **Multiple NAT Gateways**: One per AZ
- **Application Load Balancer**: For ECS if needed
- **Read Replicas**: For RDS if read-heavy
- **Cost**: ~$200-300/month

## Monitoring and Logging

### CloudWatch Log Groups

```
/ecs/aws-data-scanner-scanner-worker-dev
  ├─ Container logs from ECS tasks
  └─ Retention: 7 days

/aws/lambda/aws-data-scanner-scan-dev
  ├─ Scan Lambda execution logs
  └─ Retention: 7 days

/aws/lambda/aws-data-scanner-jobs-dev
  ├─ Jobs Lambda execution logs
  └─ Retention: 7 days

/aws/lambda/aws-data-scanner-results-dev
  ├─ Results Lambda execution logs
  └─ Retention: 7 days
```

### Metrics to Monitor

**ECS Metrics**:
- Task count (current running tasks)
- CPU utilization
- Memory utilization
- Task failures

**Lambda Metrics**:
- Invocations
- Duration
- Error count
- Throttles

**RDS Metrics**:
- CPU utilization
- Database connections
- Free storage space
- Read/Write latency

**SQS Metrics**:
- Messages visible
- Messages in flight
- Age of oldest message
- DLQ message count

## Disaster Recovery

### Backup Strategy

**RDS**:
- Automated backups: 7-day retention
- Backup window: 03:00-04:00 UTC
- Point-in-time recovery available
- Manual snapshots: Before major changes

**S3**:
- Versioning enabled (30-day retention)
- Cross-region replication (optional, production)
- Lifecycle policies for old data

**Infrastructure**:
- Terraform state in S3 (recommended)
- Infrastructure as Code in Git
- Tagged releases for rollback

### Recovery Procedures

**1. Database Failure**:
```bash
# Restore from automated backup
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier <source> \
  --target-db-instance-identifier <target> \
  --restore-time 2024-01-15T10:00:00Z
```

**2. Infrastructure Failure**:
```bash
# Redeploy from Terraform
cd terraform
terraform apply -var-file=environments/dev/terraform.tfvars
```

**3. Data Loss in S3**:
```bash
# Restore from version
aws s3api list-object-versions --bucket <bucket> --prefix <key>
aws s3api copy-object --bucket <bucket> --copy-source <bucket>/<key>?versionId=<id>
```

## Cost Breakdown by Service

### Monthly Costs (Dev Environment)

| Service | Quantity | Unit Cost | Monthly Cost | Notes |
|---------|----------|-----------|--------------|-------|
| **Compute** | | | |
| ECS Fargate (vCPU) | 0.25 vCPU × ~10 hrs | $0.04048/hr | ~$10 | With auto-scaling |
| ECS Fargate (Memory) | 0.5 GB × ~10 hrs | $0.004445/hr | ~$1 | With auto-scaling |
| Lambda Invocations | 1,000 requests | Free tier | $0 | First 1M free |
| Lambda Duration | 1,000 GB-seconds | Free tier | $0 | First 400K free |
| Bastion EC2 (t2.micro) | 730 hrs | $0.0116/hr | $8.47 | Always on |
| **Database** | | | |
| RDS (db.t3.micro) | 730 hrs | $0.017/hr | $12.41 | Always on |
| RDS Storage | 20 GB | $0.115/GB | $2.30 | gp3 storage |
| RDS Backup | 20 GB | First 20 GB free | $0 | Free tier |
| **Networking** | | | |
| NAT Gateway | 730 hrs | $0.045/hr | $32.85 | Always on |
| NAT Data Transfer | 10 GB | $0.045/GB | $0.45 | Estimated |
| **Storage** | | | |
| S3 Storage | 10 GB | $0.023/GB | $0.23 | Standard tier |
| S3 Requests | 1,000 requests | $0.0004/1K | $0.40 | PUT/GET |
| **Messaging** | | | |
| SQS Requests | 10,000 requests | First 1M free | $0 | Free tier |
| **Monitoring** | | | |
| CloudWatch Logs | 5 GB | $0.50/GB | $2.50 | Ingestion |
| CloudWatch Metrics | Custom metrics | Included | $0 | Basic monitoring |
| **Container Registry** | | | |
| ECR Storage | 1 GB | $0.10/GB | $0.10 | Docker images |
| **API Gateway** | | | |
| REST API Requests | 1,000 requests | First 1M free | $0 | Free tier |
| **TOTAL** | | | **~$70.71** | Light usage |

### Cost Optimization Tips

1. **Stop Bastion When Not Needed**:
   ```bash
   aws ec2 stop-instances --instance-ids <bastion-id>
   # Saves: ~$8/month when stopped
   ```

2. **Reduce ECS to Zero**:
   - Auto-scaling already does this
   - Saves money when no jobs running

3. **Reduce Log Retention**:
   ```hcl
   retention_in_days = 1  # instead of 7
   # Saves: ~$2/month
   ```

4. **Use Spot Instances** (Production):
   - ECS Fargate Spot: 70% discount
   - RDS Reserved Instances: 40-60% discount

5. **S3 Intelligent Tiering**:
   ```hcl
   storage_class = "INTELLIGENT_TIERING"
   # Automatic cost optimization
   ```

## Production Scaling

### Scaling to 1,000 scans/day

**Estimated Changes**:
- ECS: 10-20 tasks running during peak
- RDS: Upgrade to db.t3.small or db.m5.large
- Lambda: Still within free tier
- SQS: Still within free tier
- S3: Depends on data size

**Estimated Cost**: $200-300/month

### Scaling to 10,000 scans/day

**Estimated Changes**:
- ECS: 50-100 tasks during peak
- RDS: db.m5.xlarge with Multi-AZ
- Read Replicas: 2-3 replicas
- NAT Gateways: 2-3 for HA
- Application Load Balancer: For ECS if needed

**Estimated Cost**: $1,000-1,500/month
