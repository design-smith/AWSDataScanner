# Messaging Module - SQS Queues

# Dead Letter Queue (DLQ)
resource "aws_sqs_queue" "dlq" {
  name                       = "${var.project_name}-scan-jobs-dlq-${var.environment}"
  message_retention_seconds  = 1209600  # 14 days
  visibility_timeout_seconds = var.visibility_timeout

  tags = {
    Name = "${var.project_name}-scan-jobs-dlq-${var.environment}"
  }
}

# Main SQS Queue
resource "aws_sqs_queue" "main" {
  name                       = "${var.project_name}-scan-jobs-${var.environment}"
  message_retention_seconds  = 345600  # 4 days
  visibility_timeout_seconds = var.visibility_timeout
  delay_seconds              = 0
  receive_wait_time_seconds  = 20  # Enable long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = {
    Name = "${var.project_name}-scan-jobs-${var.environment}"
  }
}

# SQS Queue Policy for Lambda and ECS
resource "aws_sqs_queue_policy" "main" {
  queue_url = aws_sqs_queue.main.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowSendMessage"
        Effect = "Allow"
        Principal = {
          Service = [
            "lambda.amazonaws.com",
            "ecs-tasks.amazonaws.com"
          ]
        }
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.main.arn
      }
    ]
  })
}
