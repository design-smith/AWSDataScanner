# Terraform outputs

output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = "${aws_api_gateway_stage.main.invoke_url}"
}

output "sqs_queue_url" {
  description = "SQS queue URL"
  value       = module.messaging.sqs_queue_url
}

output "sqs_dlq_url" {
  description = "SQS dead-letter queue URL"
  value       = module.messaging.sqs_dlq_url
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.data.rds_endpoint
}

output "s3_bucket_name" {
  description = "S3 bucket name for test data"
  value       = module.data.s3_bucket_name
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = module.compute.ecr_repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.compute.ecs_cluster_name
}

output "bastion_public_ip" {
  description = "Bastion host public IP"
  value       = module.compute.bastion_public_ip
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "database_connection_string" {
  description = "Database connection string (without password)"
  value       = "postgresql://${var.db_username}@${module.data.rds_endpoint}/${var.db_name}"
  sensitive   = false
}
