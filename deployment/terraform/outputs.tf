output "aws_region" {
  description = "Region where resources were provisioned."
  value       = var.aws_region
}

output "cluster_name" {
  description = "EKS cluster name."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint for kubectl."
  value       = data.aws_eks_cluster.this.endpoint
}

output "cluster_certificate_authority" {
  description = "Base64 encoded certificate data for kubectl."
  value       = data.aws_eks_cluster.this.certificate_authority[0].data
}

output "backend_ecr_repository_url" {
  description = "ECR repository URL for backend image."
  value       = aws_ecr_repository.backend.repository_url
}

output "streamlit_ecr_repository_url" {
  description = "ECR repository URL for Streamlit image."
  value       = aws_ecr_repository.streamlit.repository_url
}

output "github_actions_role_arn" {
  description = "IAM role ARN assumed by GitHub Actions."
  value       = aws_iam_role.github_actions.arn
}

output "kubeconfig_update_command" {
  description = "Helper command for updating local kubeconfig."
  value       = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.aws_region}"
}

output "vpc_id" {
  description = "VPC ID for cleanup script."
  value       = module.vpc.vpc_id
}

# EBS CSI Driver IAM Role ARN
output "ebs_csi_driver_role_arn" {
  description = "IAM role ARN for EBS CSI driver service account"
  value       = module.ebs_csi_driver_irsa.iam_role_arn
}

# EBS CSI Driver Addon Info
output "ebs_csi_driver_addon_info" {
  description = "EBS CSI driver addon information"
  value = {
    id      = aws_eks_addon.ebs_csi_driver.id
    version = aws_eks_addon.ebs_csi_driver.addon_version
    arn     = aws_eks_addon.ebs_csi_driver.arn
  }
}
