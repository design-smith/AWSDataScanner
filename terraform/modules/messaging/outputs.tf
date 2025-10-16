# Messaging Module Outputs

output "sqs_queue_url" {
  description = "URL of the main SQS queue"
  value       = aws_sqs_queue.main.url
}

output "sqs_queue_arn" {
  description = "ARN of the main SQS queue"
  value       = aws_sqs_queue.main.arn
}

output "sqs_queue_name" {
  description = "Name of the main SQS queue"
  value       = aws_sqs_queue.main.name
}

output "sqs_dlq_url" {
  description = "URL of the DLQ"
  value       = aws_sqs_queue.dlq.url
}

output "sqs_dlq_arn" {
  description = "ARN of the DLQ"
  value       = aws_sqs_queue.dlq.arn
}

output "sqs_dlq_name" {
  description = "Name of the DLQ"
  value       = aws_sqs_queue.dlq.name
}
