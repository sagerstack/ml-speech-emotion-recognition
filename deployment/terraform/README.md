# Terraform Infrastructure — AWS EKS + ECR

This module provisions the networking, EKS cluster, IAM/OIDC role for GitHub Actions, and ECR repositories required to run the Speech Emotion Recognition stack in AWS.

## Prerequisites
1. AWS CLI v2 authenticated with an IAM user/role that can create VPC, EKS, IAM, and ECR resources in **us-east-1** (or override `aws_region`).
2. Terraform ≥ 1.6.0 installed locally.
3. Docker + Poetry already configured locally (needed later for image builds, not for `terraform apply`).
4. GitHub repository details for OIDC (organization/user name and repo name).

## Usage
```bash
cd deployment/terraform

# Initialize providers/modules
terraform init

# Provide required variables (github_org/repo). Example using tfvars:
cat <<'EOF' > terraform.tfvars
github_org = "sagerstack"
github_repo = "ml-speech-emotion-recognition"
environment = "prod"
project_name = "ml-speech-emotion"
EOF

# Review plan
terraform plan

# Apply
terraform apply
```

Outputs include:
- `cluster_name`, `aws_region`, `kubeconfig_update_command`
- ECR repository URLs (`backend_ecr_repository_url`, `streamlit_ecr_repository_url`)
- `github_actions_role_arn` for CI/CD configuration

## Cleanup
To delete all provisioned resources when finished:
```bash
terraform destroy
```

## Notes
- State currently uses the default local backend; migrate to S3/DynamoDB before team-wide use.
- The GitHub OIDC trust restricts role assumption to the specified repo and branch (default `main`). Update `github_main_branch` if needed.
- For multi-environment setups, invoke this module per environment (e.g., `environment = "staging"`).
