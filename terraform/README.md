# AWS Data Scanner - Terraform Infrastructure

This directory contains the Terraform configuration for deploying the AWS Data Scanner infrastructure.

## Architecture Overview

The infrastructure consists of:

- **Networking Module**: VPC, subnets (public/private), NAT Gateway, Internet Gateway
- **Data Module**: RDS PostgreSQL database, S3 bucket for data storage
- **Messaging Module**: SQS queues for job processing (main queue + DLQ)
- **Compute Module**:
  - ECR repository for Docker images
  - ECS Fargate cluster and service for scanner workers
  - Lambda functions for API handlers (scan, jobs, results)
  - Bastion host for database access
- **API Gateway**: REST API endpoints

## Prerequisites

1. **AWS Account**: Active AWS account with appropriate permissions
2. **Terraform**: Version >= 1.5.0
3. **AWS CLI**: Configured with credentials
4. **EC2 Key Pair**: Create a key pair in your AWS region for the bastion host

```bash
aws ec2 create-key-pair --key-name aws-scanner-bastion --query 'KeyMaterial' --output text > aws-scanner-bastion.pem
chmod 400 aws-scanner-bastion.pem
```

## Deployment Steps

### 1. Configure Variables

Edit `environments/dev/terraform.tfvars` and update:

```hcl
# Required changes:
db_password       = "YourSecurePassword123!"  # Use a strong password
bastion_key_name  = "aws-scanner-bastion"     # Your EC2 key pair name
```

### 2. Initialize Terraform

```bash
cd terraform
terraform init
```

### 3. Plan Deployment

```bash
terraform plan -var-file=environments/dev/terraform.tfvars
```

### 4. Deploy Infrastructure

```bash
terraform apply -var-file=environments/dev/terraform.tfvars
```

### 5. Build and Push Docker Image

After infrastructure is deployed:

```bash
# Get ECR login credentials
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag the scanner worker image
cd ../scanner-worker
docker build -t aws-data-scanner-scanner-worker-dev:latest .

# Tag and push to ECR
docker tag aws-data-scanner-scanner-worker-dev:latest <ecr-repository-url>:latest
docker push <ecr-repository-url>:latest
```

### 6. Deploy Lambda Functions

The Lambda functions need to be packaged and deployed separately:

```bash
cd ../api-handler

# Create deployment packages for each Lambda
cd src/handlers
zip -r ../../scan_lambda.zip scan.py ../utils/*
zip -r ../../jobs_lambda.zip jobs.py ../utils/*
zip -r ../../results_lambda.zip results.py ../utils/*

# Update Lambda functions
aws lambda update-function-code --function-name aws-data-scanner-scan-dev --zip-file fileb://../../scan_lambda.zip
aws lambda update-function-code --function-name aws-data-scanner-jobs-dev --zip-file fileb://../../jobs_lambda.zip
aws lambda update-function-code --function-name aws-data-scanner-results-dev --zip-file fileb://../../results_lambda.zip
```

## Accessing Resources

### Bastion Host

Connect to the bastion host to access the RDS database:

```bash
# Get bastion IP from Terraform outputs
terraform output bastion_public_ip

# SSH to bastion
ssh -i aws-scanner-bastion.pem ec2-user@<bastion-ip>

# Connect to RDS from bastion
psql -h <rds-endpoint> -U admin -d datascanner
```

### API Gateway

```bash
# Get API Gateway URL
terraform output api_gateway_url

# Test the API
curl -X POST <api-gateway-url>/dev/scan \
  -H "Content-Type: application/json" \
  -d '{"source_type": "s3", "source_path": "s3://bucket/data.csv"}'
```

## Module Structure

```
terraform/
├── main.tf                      # Root module configuration
├── variables.tf                 # Root variables
├── outputs.tf                   # Root outputs
├── environments/
│   └── dev/
│       └── terraform.tfvars     # Dev environment variables
└── modules/
    ├── networking/              # VPC, subnets, gateways
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    ├── data/                    # RDS, S3
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    ├── messaging/               # SQS queues
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    └── compute/                 # ECR, ECS, Lambda, Bastion
        ├── main.tf
        ├── variables.tf
        └── outputs.tf
```

## Cost Optimization

The dev environment is configured for cost optimization:

- **RDS**: db.t3.micro instance (single AZ)
- **ECS**: Scales to 0 when no jobs, max 5 tasks
- **Bastion**: t2.micro instance
- **Lambda**: 256 MB memory, 30s timeout
- **NAT Gateway**: Single NAT for cost savings (not HA)

**Estimated Monthly Cost**: $30-50 USD (assuming minimal usage)

## Security Considerations

**IMPORTANT**: The default configuration is for development only!

For production:

1. **Database Password**: Use AWS Secrets Manager instead of plain text
2. **Bastion SSH**: Restrict security group to specific IP ranges
3. **API Gateway**: Add authentication (Cognito, API Keys, or IAM)
4. **RDS**: Enable Multi-AZ and automated backups
5. **VPC**: Add multiple NAT Gateways for high availability
6. **Encryption**: Enable KMS encryption for S3 and RDS

## Cleanup

To destroy all resources:

```bash
terraform destroy -var-file=environments/dev/terraform.tfvars
```

## Troubleshooting

### ECS Tasks Not Starting

1. Check ECR repository has an image
2. Verify ECS task execution role has ECR permissions
3. Check CloudWatch logs: `/ecs/aws-data-scanner-scanner-worker-dev`

### Lambda Function Errors

1. Check Lambda is in VPC subnets with NAT Gateway
2. Verify security group allows outbound traffic
3. Check CloudWatch logs: `/aws/lambda/aws-data-scanner-<function>-dev`

### RDS Connection Issues

1. Verify RDS security group allows traffic from ECS/Lambda security groups
2. Check RDS is in private subnets
3. Use bastion host to test connectivity

## Outputs

Key outputs from Terraform:

```bash
terraform output
```

- `api_gateway_url`: API Gateway endpoint URL
- `rds_endpoint`: RDS database endpoint
- `ecr_repository_url`: ECR repository URL
- `bastion_public_ip`: Bastion host IP address
- `sqs_queue_url`: SQS queue URL
