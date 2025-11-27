# Implementation Plan Artifact

## 1. Metadata
| Field | Value |
| --- | --- |
| Implementation Plan ID | **US-004-IMPL-PLAN** |
| Title | **AWS EKS Deployment Automation for Streamlit & Backend** |
| User Story ID | US-004 |
| Tech Research ID | _Pending_ (`US-004-TECH-RESEARCH` placeholder) |
| Prepared By | Codex (GPT-5) |
| Created On | 2025-11-26 16:36:42 |
| Last Updated | 2025-11-26 16:36:42 |
| Status | Draft |
| Delivery Complexity | Medium-High |
| Key Dependencies | AWS account with admin access, Terraform 1.6+, Docker, GitHub Actions runners, Poetry-enabled codebase |

## 2. Quick Reference
- **Tech Stack:** Terraform, AWS (EKS, ECR, IAM, VPC, ALB), Docker, Poetry, Kubernetes, GitHub Actions.
- **Architecture Pattern:** Containerized microservices (FastAPI backend + Streamlit UI) deployed onto managed Kubernetes (EKS) with IaC + CI/CD.
- **Related Docs:** _Tech research doc pending (US-004-TECH-RESEARCH)_; existing specs under `specs/002-streamlit-app` and backend API specs.

## 3. Requirements Coverage Validation

| Requirement ID | Description | Unit Tests | Integration Tests | E2E Tests | Live Verification |
| --- | --- | --- | --- | --- | --- |
| **FR-1** | Provision AWS networking + EKS + IAM via Terraform with reproducible apply/destroy. | Terraform module unit tests via `terraform validate` + lint (tflint). | Terraform plan in CI with mocked AWS. | N/A | `terraform apply` in sandbox AWS account, `kubectl get nodes`. |
| **FR-2** | Build backend & Streamlit Docker images with Poetry dependencies and publish to ECR. | Dockerfile lint + `poetry check`. | CI build job building containers, running `pytest` & `streamlit` smoke. | Deploy to test namespace via CI pipeline. | Images pulled by EKS nodes without auth errors. |
| **FR-3** | Deploy Kubernetes manifests referencing ECR images to EKS via GitHub Actions. | K8s manifest lint (`kubeval`). | CI job runs `kubectl apply --dry-run=client`. | Automated E2E hitting `/health` & Streamlit flow. | Production EKS cluster accessible via ALB/ingress. |
| **FR-4** | Provide operational scripts/runbooks for local testing, deployment, and teardown. | Script unit tests via shellcheck. | Integration test by running script in staging env. | E2E run of script from clean state. | Verified manual walkthrough by operator. |
| **TR-1** | Enforce security best practices (Poetry-based images, IAM roles, secret management). | Static scan for Dockerfiles (hadolint). | IAM policy integration tests using terraform-compliance. | Security E2E: CI pipeline assumes role via OIDC and deploys. | AWS Config / IAM Access Analyzer verification. |
| **TR-2** | CI/CD automation with GitHub Actions + OIDC to AWS (no long-lived keys). | Workflow unit tests via actionlint. | CI stage assuming role in sandbox AWS. | Full pipeline run on merge to main. | Observed production deployment triggered by release tag. |
| **TR-3** | Monitoring/logging hooks ready for Prometheus/Grafana stack (optional). | Helm/k8s manifests lint. | Deploy monitoring namespace in test cluster. | Synthetic checks hitting metrics endpoints. | Grafana dashboards live in prod cluster. |
| **AC-1** | `terraform apply` creates environment; `terraform destroy` cleans all resources. | Terraform validate. | `terraform plan` diff zero after apply. | Spin-up/down rehearsal in staging. | Ops sign-off after destroy leaves zero chargeable resources. |
| **AC-2** | GitHub Actions workflow publishes images + deploys to EKS automatically on `main`. | actionlint + workflow unit tests. | Dry-run pipeline on feature branch. | Release candidate E2E hitting app endpoints. | Production smoke tests succeed post-deploy. |

## 4. Task-Based Implementation Plan

### 4.1 Manual Prerequisites
- [ ] **[0.1] Validate AWS access**
  - Confirm IAM user/role with admin privileges exists.
  - Enable AWS CLI credentials locally for bootstrap.
- [ ] **[0.2] Tooling readiness**
  - Install Terraform ≥1.6, Docker, Poetry, kubectl, AWS CLI v2.
  - Configure GitHub repository secrets vault (Actions).

### 4.2 Environment & Setup
- [ ] **[1.0][FR-1] Bootstrap Terraform project**
  - [ ] [1.1] Create `deployment/terraform/main.tf` with AWS provider + backend (local state initial).
  - [ ] [1.2] Define input variables (region, environment, CIDR ranges, node sizes) + defaults.
  - [ ] [1.3] Add lint/test tooling (`tflint`, `terraform fmt` in CI).
- [ ] **[1.4][FR-1] Networking module**
  - [ ] [1.4.1] Provision VPC (CIDR /16) with 3 public + 3 private subnets across AZs.
  - [ ] [1.4.2] Attach IGW/NAT gateways, route tables, security groups for worker nodes.
- [ ] **[1.5][FR-1] EKS cluster**
  - [ ] [1.5.1] Create cluster via `aws_eks_cluster` referencing private subnets & control plane logs.
  - [ ] [1.5.2] Provision managed node group (Spot + On-demand mix) with autoscaling and taints for monitoring pods.
- [ ] **[1.6][TR-1] IAM roles & OIDC**
  - [ ] [1.6.1] Node IAM role attachments (EKS worker, CNI, ECR read-only).
  - [ ] [1.6.2] Provision AWS IAM OIDC provider for GitHub.
  - [ ] [1.6.3] Create deploy role with trust policy limited to repo + branch; policy includes `ecr:*`, `eks:*`, `iam:PassRole`.
- [ ] **[1.7][FR-1] ECR repositories**
  - [ ] [1.7.1] Create `ml-speech-backend` & `ml-speech-streamlit` repos with image scanning + lifecycle policy.
  - [ ] [1.7.2] Output repo URIs for CI consumption.

### 4.3 Application Build & Release
- [ ] **[2.0][FR-2] Align Dockerfiles for ECR**
  - [ ] [2.0.1] Ensure backend + Streamlit Dockerfiles parameterize build args (env, poetry install) for reproducibility.
  - [ ] [2.0.2] Add hadolint + docker build validation to CI.
- [ ] **[2.1][FR-2] Local verification**
  - [ ] [2.1.1] Build/push images to ECR manually using AWS CLI to confirm credentials + repo permissions.
  - [ ] [2.1.2] Update `deployment/k8s/prod/*` manifests to reference ECR URIs + placeholders for tags.

### 4.4 Deployment Automation
- [ ] **[3.0][FR-3] Kubernetes manifests/overlays**
  - [ ] [3.0.1] Introduce kustomize overlay for prod injecting namespace `ml-speech-emotion` and image tags.
  - [ ] [3.0.2] Ensure ConfigMaps/Secrets pull env vars for backend + Streamlit behavior (backend URL, fonts, etc.).
- [ ] **[3.1][TR-2] GitHub Actions CI pipeline**
  - [ ] [3.1.1] Workflow `ci.yaml`: checkout → setup-python → install dependencies → run `pytest`, `ruff`, `streamlit` smoke.
  - [ ] [3.1.2] Cache Poetry + pip to minimize runtime.
  - [ ] [3.1.3] Run `docker build --target test` to validate Dockerfiles compile.
- [ ] **[3.2][TR-2/FR-2/FR-3] GitHub Actions CD pipeline**
  - [ ] [3.2.1] Trigger on `main` or tags.
  - [ ] [3.2.1a] Configure repo Actions policies to restrict workflow execution to collaborators only (disable automatic runs from forks; require approvals for external contributors).
  - [ ] [3.2.2] Build backend & Streamlit images, tag with `${{ github.sha }}` and semantic tag if release.
  - [ ] [3.2.3] `aws-actions/configure-aws-credentials` to assume Terraform-created role via OIDC.
  - [ ] [3.2.3a] Ensure IAM role trust policy restricts `sub` claim to `repo:<org>/<repo>:ref:refs/heads/main` so only `main` branch workflows obtain AWS credentials.
  - [ ] [3.2.4] `aws-actions/amazon-ecr-login` then `docker push`.
  - [ ] [3.2.5] Update kustomize image tags (`kustomize edit set image backend=<uri>:${{ github.sha }}`).
  - [ ] [3.2.6] `aws eks update-kubeconfig` and `kubectl apply -k deployment/k8s/prod`.
  - [ ] [3.2.7] Run rollout status + `kubectl port-forward` smoke test hitting `/health` and Streamlit UI via requests.
  - [ ] [3.2.8] Notify via Slack/Teams on success/failure (optional stretch).

### 4.5 Acceptance & Validation Tasks
- [ ] **[4.0][AC-1] Terraform lifecycle rehearsal**
  - [ ] [4.0.1] Run `terraform apply` in staging AWS account, capture outputs.
  - [ ] [4.0.2] Validate `kubectl get nodes` + `aws eks list-clusters`.
  - [ ] [4.0.3] Execute `terraform destroy` to ensure zero orphaned resources, capture time & cost notes.
- [ ] **[4.1][AC-2] Production pipeline test**
  - [ ] [4.1.1] Trigger CI/CD pipeline from feature branch against staging cluster.
  - [ ] [4.1.2] Execute automated E2E hitting backend `/health`, `/docs`, Streamlit navigation steps.
  - [ ] [4.1.3] Capture evidence (screenshots/logs) for release readiness review.

### 4.6 Documentation & Runbooks
- [ ] **[5.0] Operational docs**
  - [ ] [5.0.1] Author `docs/ops/eks-runbook.md` covering provisioning, deployment, rollback, teardown.
  - [ ] [5.0.2] Update `README` with instructions for `deployment/k8s/local/deploy-local.sh` vs EKS pipeline.
  - [ ] [5.0.3] Document GitHub Actions secrets + IAM roles in `docs/infrastructure/iam-matrix.md`.

## 5. Changelog
| Timestamp | Author | Change | Sections | Reason |
| --- | --- | --- | --- | --- |
| 2025-11-26 16:36:42 | Codex | Initial draft of US-004 implementation plan (EKS + ECR + CI/CD) | All | Capture deployment strategy agreed with user |
| 2025-11-26 17:05:00 | Codex | Added workflow access-control tasks (collaborators-only, main-branch trust) | §4.4 | Ensure AWS deploys only from trusted sources |
