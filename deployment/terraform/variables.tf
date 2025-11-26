variable "project_name" {
  description = "Base name used for tagging and resource naming."
  type        = string
  default     = "ml-speech-emotion"
}

variable "environment" {
  description = "Deployment environment identifier (prod, staging, etc.)."
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.50.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to use."
  type        = number
  default     = 3
}

variable "kubernetes_version" {
  description = "Desired EKS control plane version."
  type        = string
  default     = "1.29"
}

variable "node_group_min_size" {
  description = "Minimum node count in the default managed node group."
  type        = number
  default     = 1
}

variable "node_group_max_size" {
  description = "Maximum node count in the default managed node group."
  type        = number
  default     = 4
}

variable "node_group_desired_size" {
  description = "Desired node count in the default managed node group."
  type        = number
  default     = 2
}

variable "node_instance_types" {
  description = "List of EC2 instance types for managed node groups."
  type        = list(string)
  default     = ["t3a.large"]
}

variable "node_capacity_type" {
  description = "Capacity type for managed node groups (ON_DEMAND or SPOT)."
  type        = string
  default     = "ON_DEMAND"
}

variable "github_org" {
  description = "GitHub organization or user that owns the repository."
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name (without org)."
  type        = string
}

variable "github_main_branch" {
  description = "Branch allowed to assume the deploy role."
  type        = string
  default     = "main"
}
