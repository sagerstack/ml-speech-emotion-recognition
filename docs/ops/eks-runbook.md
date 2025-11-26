# EKS Deployment Runbook

## Overview
This runbook covers the end-to-end workflow for provisioning AWS infrastructure with Terraform, building/pushing images to Amazon ECR, deploying to EKS, and validating the Streamlit + backend services.

## 1. Provision Infrastructure
1. Configure AWS CLI profile (see `docs/ops/aws-access-and-oidc-setup.md`).
2. Change to the Terraform directory:
   ```bash
   cd deployment/terraform
   terraform init
   terraform plan -var="github_org=<org>" -var="github_repo=<repo>"
   terraform apply -auto-approve
   ```
3. Record outputs:
   - `backend_ecr_repository_url`
   - `streamlit_ecr_repository_url`
   - `github_actions_role_arn`
   - `kubeconfig_update_command`

## 2. Configure GitHub
1. Add repository secret `AWS_DEPLOY_ROLE_ARN` with the ARN from Terraform.
2. Restrict Actions to collaborators only (Settings → Actions → General).
3. Optionally create an `production` environment that requires approval before running the deployment workflow.

## 3. Build & Push Images Manually (optional smoke)
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-east-1

docker build -f deployment/docker/backend/Dockerfile -t $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ml-speech-emotion-backend:manual .
docker build -f deployment/docker/streamlit/Dockerfile -t $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ml-speech-emotion-streamlit:manual .

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
docker push $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ml-speech-emotion-backend:manual
docker push $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ml-speech-emotion-streamlit:manual
```

## 4. Deploy via GitHub Actions
1. Push to `main` (or trigger **Deploy to EKS** workflow manually).
2. Workflow stages:
   - Build & push Docker images (tagged with `GITHUB_SHA` and `latest`)
   - Update kustomization images with the new tags
   - `kubectl apply -k deployment/k8s/prod`
   - Rollout verification for backend + Streamlit
3. Check Actions logs for image digests and service endpoints.

## 5. Manual Validation
1. Update kubeconfig locally with `aws eks update-kubeconfig --name ml-speech-emotion-prod-eks --region us-east-1`.
2. Verify pods:
   ```bash
   kubectl get pods -n ml-speech-emotion
   kubectl logs deploy/backend -n ml-speech-emotion
   kubectl logs deploy/streamlit -n ml-speech-emotion
   ```
3. Port-forward for local testing:
   ```bash
   kubectl port-forward svc/backend -n ml-speech-emotion 8000:8000
   kubectl port-forward svc/streamlit -n ml-speech-emotion 8501:8501
   ```
4. Validate health endpoints (`curl http://localhost:8000/health`).

## 6. Teardown
1. Scale deployments to zero if doing maintenance:
   ```bash
   kubectl scale deploy/backend deploy/streamlit -n ml-speech-emotion --replicas=0
   ```
2. Destroy infrastructure when finished:
   ```bash
   cd deployment/terraform
   terraform destroy
   ```
3. Double-check AWS console for lingering load balancers, ECR images, or EBS volumes.

## 7. Troubleshooting Tips
- **OIDC failures**: confirm GitHub Actions run is on `main` and repo matches trust policy.
- **ECR push denied**: ensure AWS role has `ecr:*` permissions and repository exists (Terraform output).
- **Ingress not resolving**: ALB takes several minutes; verify `kubectl get ingress -n ml-speech-emotion` for hostname, update DNS accordingly.
- **Streamlit unable to reach backend**: confirm `backend` service endpoints exist (`kubectl get endpoints backend -n ml-speech-emotion`).
