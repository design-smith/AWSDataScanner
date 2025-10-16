# Compute Module Outputs

# ECR Outputs
output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.scanner.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN"
  value       = aws_ecr_repository.scanner.arn
}

# ECS Outputs
output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.main.arn
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.scanner.name
}

output "ecs_task_definition_arn" {
  description = "ECS task definition ARN"
  value       = aws_ecs_task_definition.scanner.arn
}

# Lambda Outputs
output "scan_lambda_arn" {
  description = "Scan Lambda function ARN"
  value       = aws_lambda_function.scan.arn
}

output "scan_lambda_name" {
  description = "Scan Lambda function name"
  value       = aws_lambda_function.scan.function_name
}

output "scan_lambda_invoke_arn" {
  description = "Scan Lambda function invoke ARN"
  value       = aws_lambda_function.scan.invoke_arn
}

output "jobs_lambda_arn" {
  description = "Jobs Lambda function ARN"
  value       = aws_lambda_function.jobs.arn
}

output "jobs_lambda_name" {
  description = "Jobs Lambda function name"
  value       = aws_lambda_function.jobs.function_name
}

output "jobs_lambda_invoke_arn" {
  description = "Jobs Lambda function invoke ARN"
  value       = aws_lambda_function.jobs.invoke_arn
}

output "results_lambda_arn" {
  description = "Results Lambda function ARN"
  value       = aws_lambda_function.results.arn
}

output "results_lambda_name" {
  description = "Results Lambda function name"
  value       = aws_lambda_function.results.function_name
}

output "results_lambda_invoke_arn" {
  description = "Results Lambda function invoke ARN"
  value       = aws_lambda_function.results.invoke_arn
}

# Bastion Outputs
output "bastion_public_ip" {
  description = "Bastion host public IP"
  value       = length(aws_instance.bastion) > 0 ? aws_instance.bastion[0].public_ip : "N/A - Bastion disabled"
}

output "bastion_instance_id" {
  description = "Bastion host instance ID"
  value       = length(aws_instance.bastion) > 0 ? aws_instance.bastion[0].id : "N/A - Bastion disabled"
}

# Security Group Outputs
output "ecs_security_group_id" {
  description = "ECS security group ID"
  value       = aws_security_group.ecs.id
}

output "lambda_security_group_id" {
  description = "Lambda security group ID"
  value       = aws_security_group.lambda.id
}

output "bastion_security_group_id" {
  description = "Bastion security group ID"
  value       = aws_security_group.bastion.id
}
