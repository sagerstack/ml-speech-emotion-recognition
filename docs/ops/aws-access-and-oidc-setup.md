# AWS Access & GitHub OIDC Setup Guide

This checklist walks through the manual prerequisites that must be completed before running the Terraform + GitHub Actions deployment pipeline.

## 1. AWS Access Verification
1. Sign in to the AWS Console with an account that may create VPC, IAM, ECR, and EKS resources in **us-east-1**.
2. Create (or reuse) an IAM user/role with administrator privileges. Attach either `AdministratorAccess` or a custom policy covering:
   - `ec2:*`, `iam:*`, `eks:*`, `ecr:*`, `logs:*`, `cloudformation:*`
3. Generate AWS CLI credentials for that identity and configure them locally:
   ```bash
   aws configure --profile ml-ser-deploy
   aws sts get-caller-identity --profile ml-ser-deploy
   ```
4. Export the profile when using Terraform:
   ```bash
   export AWS_PROFILE=ml-ser-deploy
   ```

## 2. GitHub Actions Access Restrictions
1. Open the GitHub repository → **Settings → Actions → General**.
2. Under “Actions permissions”, select **Allow GitHub Actions to run** but restrict to **Only select repositories** (if organization-level) or ensure the repo is private.
3. Under “Workflow permissions”, choose **Read and write** and **Require approval for first-time contributors** to block forks from deploying.
4. (Optional) Configure environments (e.g., `production`) that require manual approvals before the deployment job runs.

## 3. Configure GitHub OIDC Role (Terraform Output)
Terraform provisions:
- GitHub OIDC identity provider (`token.actions.githubusercontent.com`)
- Deploy role with trust restricted to `repo:<org>/<repo>:ref:refs/heads/<main>`

> **Note:** Run `terraform init/plan/apply` locally before this step. The deploy role (and its ARN) only exists after Terraform creates the infrastructure.

After `terraform apply`, note the output `github_actions_role_arn`. Use it inside the GitHub Actions workflow:
```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
    aws-region: us-east-1
```
Create a repository secret named `AWS_DEPLOY_ROLE_ARN` and set it to the value Terraform outputs. (The ARN itself is not sensitive, but keeping it in Secrets simplifies future rotations.)

### 3.1 tfvars Convenience File
`deployment/terraform/terraform.tfvars` provides default values:
```hcl
github_org  = "sagerstack"
github_repo = "ml-speech-emotion-recognition"
environment = "prod"
project_name = "ml-speech-emotion"
```
Edit this file (or override with `-var`) before running plan/apply if your organization or environment names differ.

## 4. Terraform Execution Guardrails
- Always run `terraform plan` before `apply`.
- Maintain one person running Terraform at a time (local state is used).
- After testing or when shutting down the environment, run `terraform destroy` to avoid ongoing AWS charges.
