# Compute Module Variables

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where resources will be created"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

# SQS Configuration
variable "sqs_queue_url" {
  description = "SQS queue URL"
  type        = string
}

variable "sqs_queue_arn" {
  description = "SQS queue ARN"
  type        = string
}

# Database Configuration
variable "db_host" {
  description = "Database host endpoint"
  type        = string
}

variable "db_port" {
  description = "Database port"
  type        = number
  default     = 5432
}

variable "db_name" {
  description = "Database name"
  type        = string
}

variable "db_username" {
  description = "Database username"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# S3 Configuration
variable "s3_bucket_name" {
  description = "S3 bucket name for data"
  type        = string
}

# ECS Configuration
variable "ecs_task_cpu" {
  description = "ECS task CPU units"
  type        = string
  default     = "256"
}

variable "ecs_task_memory" {
  description = "ECS task memory in MB"
  type        = string
  default     = "512"
}

variable "ecs_min_tasks" {
  description = "Minimum number of ECS tasks"
  type        = number
  default     = 1
}

variable "ecs_max_tasks" {
  description = "Maximum number of ECS tasks"
  type        = number
  default     = 10
}

variable "ecs_desired_tasks" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

# Auto Scaling Configuration
variable "autoscaling_target_queue_depth" {
  description = "Target queue depth for auto scaling"
  type        = number
  default     = 5
}

# Bastion Configuration
variable "bastion_instance_type" {
  description = "Bastion host instance type"
  type        = string
  default     = "t2.micro"
}

variable "bastion_key_name" {
  description = "EC2 key pair name for bastion host"
  type        = string
}
