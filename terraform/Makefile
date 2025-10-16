# Makefile for AWS Data Scanner Terraform

.PHONY: help init validate plan apply destroy fmt clean test

# Variables
TFVARS_FILE := environments/dev/terraform.tfvars
AWS_REGION := us-east-1

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "AWS Data Scanner - Terraform Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

init: ## Initialize Terraform
	@echo "$(GREEN)Initializing Terraform...$(NC)"
	terraform init
	@echo "$(GREEN)Done!$(NC)"

validate: ## Validate Terraform configuration
	@echo "$(GREEN)Validating configuration...$(NC)"
	@./validate.sh || true
	terraform validate
	@echo "$(GREEN)Validation complete!$(NC)"

fmt: ## Format Terraform files
	@echo "$(GREEN)Formatting Terraform files...$(NC)"
	terraform fmt -recursive
	@echo "$(GREEN)Done!$(NC)"

plan: ## Show Terraform plan
	@echo "$(GREEN)Generating Terraform plan...$(NC)"
	terraform plan -var-file=$(TFVARS_FILE)

apply: ## Apply Terraform changes
	@echo "$(YELLOW)WARNING: This will create AWS resources that cost money!$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to cancel, or any key to continue...$(NC)"
	@read -n 1
	terraform apply -var-file=$(TFVARS_FILE)
	@echo "$(GREEN)Deployment complete!$(NC)"
	@echo ""
	@echo "Get outputs with: make outputs"

destroy: ## Destroy all Terraform resources
	@echo "$(YELLOW)WARNING: This will destroy all resources!$(NC)"
	@echo "$(YELLOW)Type 'yes' to confirm:$(NC)"
	@read confirm; [ "$$confirm" = "yes" ] || exit 1
	terraform destroy -var-file=$(TFVARS_FILE)
	@echo "$(GREEN)Resources destroyed!$(NC)"

outputs: ## Show Terraform outputs
	@echo "$(GREEN)Terraform Outputs:$(NC)"
	@terraform output

clean: ## Clean Terraform cache and state
	@echo "$(YELLOW)Cleaning Terraform files...$(NC)"
	rm -rf .terraform
	rm -f .terraform.lock.hcl
	@echo "$(GREEN)Done!$(NC)"

test: ## Run validation tests
	@echo "$(GREEN)Running validation script...$(NC)"
	@./validate.sh

check-aws: ## Check AWS credentials
	@echo "$(GREEN)Checking AWS credentials...$(NC)"
	@aws sts get-caller-identity || echo "$(YELLOW)Not authenticated$(NC)"

create-key: ## Create EC2 key pair for bastion
	@echo "$(GREEN)Creating EC2 key pair...$(NC)"
	aws ec2 create-key-pair \
		--key-name aws-scanner-bastion \
		--query 'KeyMaterial' \
		--output text > aws-scanner-bastion.pem
	chmod 400 aws-scanner-bastion.pem
	@echo "$(GREEN)Key pair created: aws-scanner-bastion.pem$(NC)"

ssh-bastion: ## SSH to bastion host
	@echo "$(GREEN)Connecting to bastion...$(NC)"
	@BASTION_IP=$$(terraform output -raw bastion_public_ip 2>/dev/null); \
	if [ -z "$$BASTION_IP" ]; then \
		echo "$(YELLOW)Cannot get bastion IP. Run 'make apply' first.$(NC)"; \
		exit 1; \
	fi; \
	ssh -i aws-scanner-bastion.pem ec2-user@$$BASTION_IP

ecr-login: ## Login to ECR
	@echo "$(GREEN)Logging in to ECR...$(NC)"
	@ECR_URL=$$(terraform output -raw ecr_repository_url 2>/dev/null | cut -d'/' -f1); \
	if [ -z "$$ECR_URL" ]; then \
		echo "$(YELLOW)Cannot get ECR URL. Run 'make apply' first.$(NC)"; \
		exit 1; \
	fi; \
	aws ecr get-login-password --region $(AWS_REGION) | \
		docker login --username AWS --password-stdin $$ECR_URL
	@echo "$(GREEN)Logged in to ECR!$(NC)"

push-image: ## Build and push scanner worker image
	@echo "$(GREEN)Building and pushing scanner worker...$(NC)"
	@ECR_URL=$$(terraform output -raw ecr_repository_url 2>/dev/null); \
	if [ -z "$$ECR_URL" ]; then \
		echo "$(YELLOW)Cannot get ECR URL. Run 'make apply' first.$(NC)"; \
		exit 1; \
	fi; \
	cd ../scanner-worker && \
	docker build -t scanner-worker:latest . && \
	docker tag scanner-worker:latest $$ECR_URL:latest && \
	docker push $$ECR_URL:latest
	@echo "$(GREEN)Image pushed successfully!$(NC)"

logs-ecs: ## View ECS logs
	@echo "$(GREEN)Fetching ECS logs...$(NC)"
	aws logs tail /ecs/aws-data-scanner-scanner-worker-dev --follow

logs-lambda-scan: ## View scan Lambda logs
	@echo "$(GREEN)Fetching scan Lambda logs...$(NC)"
	aws logs tail /aws/lambda/aws-data-scanner-scan-dev --follow

logs-lambda-jobs: ## View jobs Lambda logs
	@echo "$(GREEN)Fetching jobs Lambda logs...$(NC)"
	aws logs tail /aws/lambda/aws-data-scanner-jobs-dev --follow

test-api: ## Test API Gateway endpoint
	@echo "$(GREEN)Testing API Gateway...$(NC)"
	@API_URL=$$(terraform output -raw api_gateway_url 2>/dev/null); \
	if [ -z "$$API_URL" ]; then \
		echo "$(YELLOW)Cannot get API URL. Run 'make apply' first.$(NC)"; \
		exit 1; \
	fi; \
	echo "API URL: $$API_URL"; \
	curl -X POST $$API_URL/dev/scan \
		-H "Content-Type: application/json" \
		-d '{"source_type": "s3", "source_path": "s3://test/data.csv"}'

costs: ## Estimate monthly costs
	@echo "$(GREEN)Estimated Monthly Costs (Dev Environment):$(NC)"
	@echo ""
	@echo "RDS (db.t3.micro):        ~$$15/month"
	@echo "NAT Gateway:              ~$$32/month"
	@echo "Bastion (t2.micro):       ~$$8/month"
	@echo "ECS Fargate (minimal):    ~$$5-10/month"
	@echo "Lambda (free tier):       ~$$0/month"
	@echo "S3 (minimal):             ~$$1/month"
	@echo "CloudWatch Logs:          ~$$2/month"
	@echo "-----------------------------------"
	@echo "TOTAL:                    ~$$63-68/month"
	@echo ""
	@echo "$(YELLOW)Note: Actual costs may vary based on usage$(NC)"

status: ## Show deployment status
	@echo "$(GREEN)Deployment Status:$(NC)"
	@echo ""
	@terraform output 2>/dev/null || echo "$(YELLOW)No outputs found. Run 'make apply' first.$(NC)"

update-config: ## Edit configuration file
	@$${EDITOR:-nano} $(TFVARS_FILE)

quick-deploy: init validate apply ## Quick deployment (init + validate + apply)
	@echo "$(GREEN)Quick deployment complete!$(NC)"

full-deploy: create-key quick-deploy push-image ## Full deployment with all steps
	@echo "$(GREEN)Full deployment complete!$(NC)"
	@echo ""
	@echo "$(GREEN)Next steps:$(NC)"
	@echo "1. Initialize database schema"
	@echo "2. Deploy Lambda functions"
	@echo "3. Test API: make test-api"

# Default target
.DEFAULT_GOAL := help
