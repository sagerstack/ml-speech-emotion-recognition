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

**IMPORTANT**: Do not run `terraform destroy` directly. Use the provided cleanup script instead.

### Why Use the Cleanup Script?

The AWS Load Balancer Controller creates AWS resources (Load Balancers, Security Groups, Target Groups) dynamically when you deploy Kubernetes services. These resources are created **outside of Terraform** and must be cleaned up **before** destroying the infrastructure, otherwise they'll be orphaned and block Terraform destroy.

### Proper Cleanup Process

Use the automated cleanup script:
```bash
cd deployment/terraform
./destroy.sh
```

**Important**: The script uses `AWS_PROFILE=ml-ser-deploy` by default. It will display the configuration before proceeding.

The script will:
1. ✅ Display AWS profile, region, and cluster configuration
2. ✅ Delete Kubernetes namespace and all services (triggers AWS Load Balancer Controller cleanup)
3. ✅ Wait for AWS resources to be removed (60 seconds)
4. ✅ Check for and delete any orphaned load balancers/security groups
5. ✅ Run `terraform destroy` with the correct AWS profile and confirmation prompt

### Environment Variables

The script uses these defaults (can be overridden by setting environment variables):
- `AWS_PROFILE=ml-ser-deploy` (⚠️ **REQUIRED** - must have permissions for EKS, EC2, VPC, and ELB)
- `AWS_REGION=us-east-1`
- `EKS_CLUSTER_NAME=ml-speech-emotion-prod-eks`
- `K8S_NAMESPACE=ml-speech-emotion`

Example with custom values:
```bash
# Override with different profile and region
AWS_PROFILE=my-profile AWS_REGION=us-west-2 ./destroy.sh

# Or explicitly set the default profile (for clarity)
AWS_PROFILE=ml-ser-deploy ./destroy.sh
```

### Manual Cleanup (Not Recommended)

If you must clean up manually:
```bash
# 1. Delete Kubernetes resources first
kubectl delete namespace ml-speech-emotion
sleep 60

# 2. Then run terraform destroy
AWS_PROFILE=ml-ser-deploy terraform destroy
```

## Notes
- State currently uses the default local backend; migrate to S3/DynamoDB before team-wide use.
- The GitHub OIDC trust restricts role assumption to the specified repo and branch (default `main`). Update `github_main_branch` if needed.
- For multi-environment setups, invoke this module per environment (e.g., `environment = "staging"`).
