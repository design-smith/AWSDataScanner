# Main Terraform configuration

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(var.tags, {
      Environment = var.environment
    })
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

# Networking Module
module "networking" {
  source = "./modules/networking"

  project_name          = var.project_name
  environment           = var.environment
  vpc_cidr              = var.vpc_cidr
  public_subnet_cidrs   = var.public_subnet_cidrs
  private_subnet_cidrs  = var.private_subnet_cidrs
  availability_zones    = slice(data.aws_availability_zones.available.names, 0, 2)
}

# Messaging Module (SQS)
module "messaging" {
  source = "./modules/messaging"

  project_name            = var.project_name
  environment             = var.environment
  visibility_timeout      = var.sqs_visibility_timeout
  max_receive_count       = var.sqs_max_receive_count
}

# Data Module (RDS, S3)
module "data" {
  source = "./modules/data"

  project_name            = var.project_name
  environment             = var.environment
  vpc_id                  = module.networking.vpc_id
  private_subnet_ids      = module.networking.private_subnet_ids
  db_name                 = var.db_name
  db_username             = var.db_username
  db_password             = var.db_password
  db_instance_class       = var.db_instance_class
  allowed_security_groups = [module.compute.ecs_security_group_id, module.compute.bastion_security_group_id]
}

# Compute Module (ECS, Lambda, Bastion)
module "compute" {
  source = "./modules/compute"

  project_name                   = var.project_name
  environment                    = var.environment
  vpc_id                         = module.networking.vpc_id
  public_subnet_ids              = module.networking.public_subnet_ids
  private_subnet_ids             = module.networking.private_subnet_ids
  sqs_queue_url                  = module.messaging.sqs_queue_url
  sqs_queue_arn                  = module.messaging.sqs_queue_arn
  db_host                        = module.data.rds_endpoint
  db_port                        = 5432
  db_name                        = var.db_name
  db_username                    = var.db_username
  db_password                    = var.db_password
  s3_bucket_name                 = module.data.s3_bucket_name
  ecs_task_cpu                   = var.ecs_task_cpu
  ecs_task_memory                = var.ecs_task_memory
  ecs_min_tasks                  = var.ecs_min_tasks
  ecs_max_tasks                  = var.ecs_max_tasks
  ecs_desired_tasks              = var.ecs_desired_tasks
  autoscaling_target_queue_depth = var.autoscaling_target_queue_depth
  bastion_instance_type          = var.bastion_instance_type
  bastion_key_name               = var.bastion_key_name
}

# API Gateway
resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.project_name}-api-${var.environment}"
  description = "API for AWS Data Scanner"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# API Gateway Resources

# /scan resource
resource "aws_api_gateway_resource" "scan" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "scan"
}

# POST /scan method
resource "aws_api_gateway_method" "scan_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.scan.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "scan_post" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.scan.id
  http_method             = aws_api_gateway_method.scan_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.compute.scan_lambda_invoke_arn
}

# /jobs resource
resource "aws_api_gateway_resource" "jobs" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "jobs"
}

# /jobs/{job_id} resource
resource "aws_api_gateway_resource" "job_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.jobs.id
  path_part   = "{job_id}"
}

# GET /jobs/{job_id} method
resource "aws_api_gateway_method" "job_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.job_id.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "job_get" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.job_id.id
  http_method             = aws_api_gateway_method.job_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.compute.jobs_lambda_invoke_arn
}

# /results resource
resource "aws_api_gateway_resource" "results" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "results"
}

# GET /results method
resource "aws_api_gateway_method" "results_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.results.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "results_get" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.results.id
  http_method             = aws_api_gateway_method.results_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.compute.results_lambda_invoke_arn
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.scan.id,
      aws_api_gateway_method.scan_post.id,
      aws_api_gateway_integration.scan_post.id,
      aws_api_gateway_resource.jobs.id,
      aws_api_gateway_resource.job_id.id,
      aws_api_gateway_method.job_get.id,
      aws_api_gateway_integration.job_get.id,
      aws_api_gateway_resource.results.id,
      aws_api_gateway_method.results_get.id,
      aws_api_gateway_integration.results_get.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "scan_api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.compute.scan_lambda_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "jobs_api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.compute.jobs_lambda_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "results_api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.compute.results_lambda_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}
