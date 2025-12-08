variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment (prod, staging, dev)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "model_version" {
  description = "Model version to deploy (e.g., v5). Leave empty to skip initial deployment."
  type        = string
  default     = ""
}

variable "instance_type" {
  description = "SageMaker endpoint instance type"
  type        = string
  default     = "ml.t3.medium"
}

variable "min_capacity" {
  description = "Minimum number of instances for auto-scaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of instances for auto-scaling"
  type        = number
  default     = 3
}

variable "autoscaling_target_invocations" {
  description = "Target invocations per instance for auto-scaling"
  type        = number
  default     = 100
}
