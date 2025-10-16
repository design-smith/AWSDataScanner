# AWS Data Scanner - Quick Start Guide

## What Was Created

All Terraform modules for the AWS Data Scanner infrastructure have been successfully created:

### Module Structure

```
terraform/
├── main.tf                          # Root configuration with API Gateway
├── variables.tf                     # Root variables
├── outputs.tf                       # Root outputs
├── README.md                        # Detailed documentation
├── MODULES.md                       # Module documentation
├── QUICK_START.md                   # This file
├── validate.sh                      # Validation script
├── .gitignore                       # Git ignore rules
│
├── environments/
│   └── dev/
│       └── terraform.tfvars         # Development environment config
│
└── modules/
    ├── networking/                  # VPC, Subnets, NAT, IGW
    │   ├── main.tf                 # 2 public + 2 private subnets
    │   ├── variables.tf
    │   └── outputs.tf
    │
    ├── data/                        # RDS PostgreSQL + S3
    │   ├── main.tf                 # PostgreSQL 15.4 + encrypted S3
    │   ├── variables.tf
    │   └── outputs.tf
    │
    ├── messaging/                   # SQS Queues
    │   ├── main.tf                 # Main queue + DLQ with redrive
    │   ├── variables.tf
    │   └── outputs.tf
    │
    └── compute/                     # ECR, ECS, Lambda, Bastion
        ├── main.tf                 # Most complex module
        ├── variables.tf
        ├── outputs.tf
        └── lambda_placeholder.zip  # Temporary Lambda code
```

## Quick Start (5 Minutes)

### 1. Prerequisites Check

```bash
# Check Terraform version (>= 1.5.0)
terraform version

# Check AWS CLI
aws --version

# Verify AWS credentials
aws sts get-caller-identity
```

### 2. Create EC2 Key Pair

```bash
# Create new key pair for bastion host
aws ec2 create-key-pair \
    --key-name aws-scanner-bastion \
    --query 'KeyMaterial' \
    --output text > aws-scanner-bastion.pem

# Set proper permissions
chmod 400 aws-scanner-bastion.pem
```

### 3. Update Configuration

Edit `environments/dev/terraform.tfvars`:

```hcl
# REQUIRED: Change these values!
db_password       = "YourSecurePassword123!"  # Use a strong password
bastion_key_name  = "aws-scanner-bastion"     # Your key pair name

# Optional: Customize other values
project_name = "aws-data-scanner"
environment  = "dev"
aws_region   = "us-east-1"
```

### 4. Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Review the plan
terraform plan -var-file=environments/dev/terraform.tfvars

# Deploy (takes ~10-15 minutes)
terraform apply -var-file=environments/dev/terraform.tfvars
```

### 5. Post-Deployment Steps

```bash
# Get outputs
terraform output

# Note these values:
# - ecr_repository_url (for Docker push)
# - rds_endpoint (for database connection)
# - bastion_public_ip (for SSH access)
# - api_gateway_url (for API testing)
```

## What Gets Deployed

### Networking (Module 1)
- **VPC**: 10.0.0.0/16
- **Public Subnets**: 10.0.1.0/24, 10.0.2.0/24 (2 AZs)
- **Private Subnets**: 10.0.10.0/24, 10.0.11.0/24 (2 AZs)
- **Internet Gateway**: For public subnet internet access
- **NAT Gateway**: For private subnet internet access
- **Route Tables**: Configured for public/private routing

### Data Storage (Module 2)
- **RDS PostgreSQL 15.4**:
  - Instance: db.t3.micro
  - Storage: 20 GB (encrypted)
  - Location: Private subnets
  - Backup: 7-day retention
  - Multi-AZ: Disabled (dev mode)

- **S3 Bucket**:
  - Versioning enabled
  - Encryption: AES256
  - Public access: Blocked
  - Lifecycle: 30-day version expiration

### Message Queue (Module 3)
- **Main SQS Queue**:
  - Name: aws-data-scanner-scan-jobs-dev
  - Retention: 4 days
  - Long polling: Enabled

- **Dead Letter Queue**:
  - Name: aws-data-scanner-scan-jobs-dlq-dev
  - Retention: 14 days
  - Max receive: 3 attempts

### Compute Resources (Module 4)
- **ECR Repository**: For Docker images
- **ECS Fargate Cluster**: Scanner worker containers
  - CPU: 256 units (0.25 vCPU)
  - Memory: 512 MB
  - Auto-scaling: 0-5 tasks based on SQS depth

- **Lambda Functions** (3):
  - scan: Create scan jobs
  - jobs: Get job status
  - results: Fetch scan results

- **Bastion Host**:
  - Instance: t2.micro
  - AMI: Amazon Linux 2
  - PostgreSQL client pre-installed

- **Security Groups**:
  - ECS: Outbound only
  - Lambda: Outbound only
  - Bastion: SSH (22) inbound
  - RDS: PostgreSQL (5432) from ECS/Bastion/Lambda

### API Gateway
- **REST API**: Regional endpoint
- **Endpoints**:
  - POST /scan: Initiate scan
  - GET /jobs/{job_id}: Get job status
  - GET /results: List results

## Resource Access

### SSH to Bastion

```bash
# Get bastion IP
BASTION_IP=$(terraform output -raw bastion_public_ip)

# Connect
ssh -i aws-scanner-bastion.pem ec2-user@$BASTION_IP
```

### Connect to RDS from Bastion

```bash
# From bastion host
RDS_ENDPOINT=$(terraform output -raw rds_endpoint | cut -d':' -f1)
psql -h $RDS_ENDPOINT -U admin -d datascanner
# Password: (your db_password from tfvars)
```

### Push Docker Image to ECR

```bash
# Get ECR URL
ECR_URL=$(terraform output -raw ecr_repository_url)
AWS_REGION="us-east-1"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_URL

# Build and push
cd ../scanner-worker
docker build -t scanner-worker:latest .
docker tag scanner-worker:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

### Test API Gateway

```bash
# Get API URL
API_URL=$(terraform output -raw api_gateway_url)

# Test scan endpoint
curl -X POST $API_URL/dev/scan \
    -H "Content-Type: application/json" \
    -d '{
        "source_type": "s3",
        "source_path": "s3://bucket/data.csv",
        "target_database": "scanner_db"
    }'
```

## Cost Estimate

Monthly costs for dev environment (us-east-1):

| Service | Configuration | Cost/Month |
|---------|--------------|------------|
| RDS PostgreSQL | db.t3.micro, 20GB | ~$15 |
| NAT Gateway | Single gateway | ~$32 |
| Bastion EC2 | t2.micro | ~$8 |
| ECS Fargate | 0-5 tasks (minimal use) | ~$5-10 |
| Lambda | 256 MB, minimal use | ~$0 (free tier) |
| S3 | Minimal storage | ~$1 |
| CloudWatch Logs | 7-day retention | ~$2 |
| **Total** | | **~$63-68** |

**Cost Optimization Tips:**
- Stop bastion when not needed: `aws ec2 stop-instances --instance-ids <id>`
- ECS scales to 0 automatically when idle
- Delete unused S3 versions
- Reduce log retention to 1 day

## Security Checklist

### Before Production:

- [ ] Change default database password
- [ ] Use AWS Secrets Manager for credentials
- [ ] Restrict bastion SSH to specific IPs
- [ ] Add API Gateway authentication
- [ ] Enable Multi-AZ for RDS
- [ ] Add multiple NAT Gateways for HA
- [ ] Enable AWS WAF for API Gateway
- [ ] Set up CloudWatch alarms
- [ ] Configure backup retention
- [ ] Review IAM policies (least privilege)

## Troubleshooting

### Common Issues

**1. ECS Tasks Not Starting**
```bash
# Check if ECR has image
aws ecr describe-images --repository-name aws-data-scanner-scanner-worker-dev

# View ECS logs
aws logs tail /ecs/aws-data-scanner-scanner-worker-dev --follow
```

**2. Lambda Timeout Errors**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/aws-data-scanner-scan-dev --follow

# Verify VPC connectivity
# Ensure NAT Gateway is working
```

**3. Cannot Connect to RDS**
```bash
# From bastion, test connection
nc -zv <rds-endpoint> 5432

# Check security groups allow traffic
aws ec2 describe-security-groups --group-ids <sg-id>
```

**4. Terraform Apply Fails**
```bash
# Run validation script
./validate.sh

# Check AWS credentials
aws sts get-caller-identity

# Verify Terraform state
terraform state list
```

## Next Steps

After successful deployment:

1. **Initialize Database**: Run schema migration scripts
2. **Deploy Lambda Code**: Replace placeholder with actual handlers
3. **Build Scanner Worker**: Create and push Docker image
4. **Test Integration**: Send test scan job through API
5. **Monitor**: Set up CloudWatch dashboards
6. **Document**: Note API endpoints and usage

## Cleanup

To destroy all resources:

```bash
# WARNING: This deletes everything!
terraform destroy -var-file=environments/dev/terraform.tfvars

# Confirm when prompted
```

**Note**: Some resources may require manual deletion:
- S3 buckets with objects
- ECR images
- CloudWatch log groups (if retention policy prevents deletion)

## Additional Resources

- **Full Documentation**: See `README.md`
- **Module Details**: See `MODULES.md`
- **Terraform Docs**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- **AWS Best Practices**: https://aws.amazon.com/architecture/well-architected/

## Support

For issues or questions:
1. Check CloudWatch logs
2. Review Terraform output
3. Run `./validate.sh` to verify configuration
4. Check AWS service quotas
5. Review IAM permissions

---

**Generated**: Terraform modules for AWS Data Scanner
**Modules**: 4 (Networking, Data, Messaging, Compute)
**Total Resources**: ~60 AWS resources
**Lines of Code**: ~1,791 lines of Terraform
