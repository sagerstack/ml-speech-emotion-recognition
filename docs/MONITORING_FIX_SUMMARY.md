# Monitoring Stack Fix Summary

## Problem: EBS CSI Driver Missing IAM Permissions

### Root Cause
The EBS CSI driver addon was installed but is **CrashLoopBackOff** because it lacks IAM permissions:

```
Error: User: arn:aws:sts::303440520181:assumed-role/default-eks-node-group.../i-09ce23f187aa8fdb3 
is not authorized to perform: ec2:DescribeAvailabilityZones
```

### Why PVCs Are Stuck in Pending
- EBS CSI controller pods are crashing (1/6 Running, CrashLoopBackOff)
- Cannot provision EBS volumes for Prometheus, Grafana, Loki PVCs
- All 3 monitoring PVCs remain in "Pending" state

## Solution: Add IRSA (IAM Role for Service Accounts)

### Changes Made to Terraform

**1. Added EBS CSI Driver IAM Role Module** (lines 143-162):
```terraform
module "ebs_csi_driver_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name_prefix = "${local.project_name}-ebs-csi-"
  attach_ebs_csi_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }

  tags = local.tags
}
```

**2. Updated EBS CSI Addon to Use IAM Role** (lines 83-86):
```terraform
cluster_addons = {
  aws-ebs-csi-driver = {
    most_recent              = true
    service_account_role_arn = module.ebs_csi_driver_irsa.iam_role_arn  # ADDED
  }
  # ... other addons
}
```

## Deployment Steps

### Step 1: Import Existing Addon (REQUIRED)
The addon already exists, so you must import it before applying:

```bash
cd deployment/terraform

# Import the existing addon into terraform state
terraform import 'module.eks.aws_eks_addon.this["aws-ebs-csi-driver"]' ml-speech-emotion-prod-eks:aws-ebs-csi-driver
```

### Step 2: Apply Terraform Changes
```bash
terraform plan -out=tfplan
terraform apply tfplan
```

### Step 3: Verify EBS CSI Driver
After apply, the EBS CSI driver will have IAM permissions:

```bash
# Check if controller pods are now running
kubectl get pods -n kube-system | grep ebs

# Should show:
# ebs-csi-controller-xxx   6/6   Running   ...
# ebs-csi-node-xxx         3/3   Running   ...
```

### Step 4: Monitoring Stack Should Auto-Provision
Once EBS CSI driver is healthy, PVCs will automatically provision:

```bash
# Check PVC status
kubectl get pvc -n monitoring

# Should change from Pending to Bound:
# NAME             STATUS   VOLUME                                     CAPACITY
# prometheus-pvc   Bound    pvc-xxx   20Gi
# loki-pvc         Bound    pvc-yyy   20Gi
# grafana-pvc      Bound    pvc-zzz   10Gi
```

### Step 5: Verify Monitoring Pods
```bash
# Check monitoring stack pods
kubectl get pods -n monitoring

# Should all be Running:
# prometheus-xxx   1/1   Running
# loki-xxx         1/1   Running
# grafana-xxx      1/1   Running
```

## What This Fixes

✅ EBS CSI driver controller pods will run successfully  
✅ Service account `ebs-csi-controller-sa` will have IAM role annotation  
✅ EBS volumes can be dynamically provisioned  
✅ Monitoring PVCs will be bound to EBS volumes  
✅ Prometheus, Grafana, Loki pods will start successfully  

## IAM Permissions Created

The terraform module creates an IAM role with AWS managed policy for EBS CSI driver:
- **Policy**: `arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy`
- **Actions Allowed**:
  - `ec2:CreateVolume`, `ec2:DeleteVolume`, `ec2:AttachVolume`, `ec2:DetachVolume`
  - `ec2:CreateSnapshot`, `ec2:DeleteSnapshot`
  - `ec2:DescribeAvailabilityZones`, `ec2:DescribeInstances`, `ec2:DescribeVolumes`
  - And more EC2 operations needed for EBS volume management

## Alternative: Manual IAM Role Setup

If you prefer not to use terraform for this, you can manually create the IAM role:

```bash
# Create IAM role and policy
eksctl create iamserviceaccount \
  --name ebs-csi-controller-sa \
  --namespace kube-system \
  --cluster ml-speech-emotion-prod-eks \
  --role-name ml-speech-emotion-ebs-csi-driver \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
  --approve \
  --region us-east-1
```

Then update the addon to use the role:
```bash
aws eks update-addon \
  --cluster-name ml-speech-emotion-prod-eks \
  --addon-name aws-ebs-csi-driver \
  --service-account-role-arn arn:aws:iam::303440520181:role/ml-speech-emotion-ebs-csi-driver \
  --region us-east-1
```

## Files Modified

- `deployment/terraform/main.tf` - Added IRSA module and updated addon configuration
- `deployment/terraform/import-addons.sh` - Import script for existing addon (created)

## Next Steps After Fix

Once monitoring stack is running:

1. Access Grafana dashboard:
   ```bash
   kubectl port-forward -n monitoring svc/grafana 3000:3000
   # Visit http://localhost:3000 (admin/admin)
   ```

2. Access Prometheus:
   ```bash
   kubectl port-forward -n monitoring svc/prometheus 9090:9090
   # Visit http://localhost:9090
   ```

3. Configure Grafana dashboards for backend metrics scraping
