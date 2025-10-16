#!/bin/bash
# Terraform Validation Script for AWS Data Scanner

set -e

echo "=========================================="
echo "AWS Data Scanner - Terraform Validation"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Terraform is installed
echo -n "Checking Terraform installation... "
if command -v terraform &> /dev/null; then
    TERRAFORM_VERSION=$(terraform version -json | grep -o '"terraform_version":"[^"]*' | cut -d'"' -f4)
    echo -e "${GREEN}✓ Found Terraform v${TERRAFORM_VERSION}${NC}"
else
    echo -e "${RED}✗ Terraform not found${NC}"
    echo "Please install Terraform: https://www.terraform.io/downloads"
    exit 1
fi

# Check if AWS CLI is installed
echo -n "Checking AWS CLI installation... "
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1 | cut -d'/' -f2)
    echo -e "${GREEN}✓ Found AWS CLI v${AWS_VERSION}${NC}"
else
    echo -e "${YELLOW}⚠ AWS CLI not found (optional but recommended)${NC}"
fi

# Check AWS credentials
echo -n "Checking AWS credentials... "
if aws sts get-caller-identity &> /dev/null; then
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_USER=$(aws sts get-caller-identity --query Arn --output text | cut -d'/' -f2)
    echo -e "${GREEN}✓ Authenticated as ${AWS_USER} (Account: ${AWS_ACCOUNT})${NC}"
else
    echo -e "${YELLOW}⚠ Not authenticated (will use default credentials)${NC}"
fi

echo ""
echo "=========================================="
echo "Validating Terraform Configuration"
echo "=========================================="
echo ""

# Initialize Terraform
echo "1. Initializing Terraform..."
if terraform init -backend=false > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Terraform initialized successfully${NC}"
else
    echo -e "${RED}✗ Terraform initialization failed${NC}"
    exit 1
fi

# Validate syntax
echo "2. Validating syntax..."
if terraform validate > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Terraform configuration is valid${NC}"
else
    echo -e "${RED}✗ Terraform validation failed${NC}"
    terraform validate
    exit 1
fi

# Format check
echo "3. Checking formatting..."
if terraform fmt -check -recursive > /dev/null 2>&1; then
    echo -e "${GREEN}✓ All files are properly formatted${NC}"
else
    echo -e "${YELLOW}⚠ Some files need formatting${NC}"
    echo "Run 'terraform fmt -recursive' to fix"
fi

# Check for required files
echo "4. Checking required files..."
REQUIRED_FILES=(
    "main.tf"
    "variables.tf"
    "outputs.tf"
    "environments/dev/terraform.tfvars"
    "modules/networking/main.tf"
    "modules/data/main.tf"
    "modules/messaging/main.tf"
    "modules/compute/main.tf"
)

ALL_FILES_EXIST=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file (missing)"
        ALL_FILES_EXIST=false
    fi
done

if [ "$ALL_FILES_EXIST" = false ]; then
    echo -e "${RED}✗ Some required files are missing${NC}"
    exit 1
fi

# Check tfvars configuration
echo "5. Checking tfvars configuration..."
TFVARS_FILE="environments/dev/terraform.tfvars"

# Check for placeholder values
if grep -q "ChangeMe" "$TFVARS_FILE" 2>/dev/null; then
    echo -e "  ${YELLOW}⚠ Found placeholder password in $TFVARS_FILE${NC}"
    echo "    Please update 'db_password' before deployment"
fi

if grep -q "my-key-pair" "$TFVARS_FILE" 2>/dev/null; then
    echo -e "  ${YELLOW}⚠ Found placeholder key pair in $TFVARS_FILE${NC}"
    echo "    Please update 'bastion_key_name' before deployment"
fi

# Module validation
echo "6. Validating modules..."
MODULES=("networking" "data" "messaging" "compute")

for module in "${MODULES[@]}"; do
    if [ -f "modules/$module/main.tf" ] && [ -f "modules/$module/variables.tf" ] && [ -f "modules/$module/outputs.tf" ]; then
        echo -e "  ${GREEN}✓${NC} $module module"
    else
        echo -e "  ${RED}✗${NC} $module module (incomplete)"
        ALL_FILES_EXIST=false
    fi
done

echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo ""

if [ "$ALL_FILES_EXIST" = true ]; then
    echo -e "${GREEN}✓ All validation checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review and update: $TFVARS_FILE"
    echo "2. Create EC2 key pair for bastion host"
    echo "3. Run: terraform plan -var-file=$TFVARS_FILE"
    echo "4. Run: terraform apply -var-file=$TFVARS_FILE"
    exit 0
else
    echo -e "${RED}✗ Validation failed${NC}"
    echo "Please fix the issues above before proceeding"
    exit 1
fi
