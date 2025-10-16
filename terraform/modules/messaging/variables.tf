# Messaging Module Variables

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "visibility_timeout" {
  description = "SQS visibility timeout in seconds"
  type        = number
  default     = 300  # 5 minutes
}

variable "max_receive_count" {
  description = "Maximum number of receives before message goes to DLQ"
  type        = number
  default     = 3
}
