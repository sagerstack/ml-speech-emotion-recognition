# EBS CSI Driver Terraform Guide

## Will Terraform Create EBS CSI Driver After Destroy?

**YES**, but you need to understand the creation flow and handle a potential one-time manual step.

## How It Works

### Clean Install (After terraform destroy)

When you run `terraform apply` on a clean slate:

1. **Terraform creates EKS cluster** with IRSA enabled
2. **Terraform creates IAM role** via `ebs_csi_driver_irsa` module with trust policy for `kube-system:ebs-csi-controller-sa`
3. **Terraform installs EBS CSI addon** with the IAM role ARN
4. **EKS creates the service account** `ebs-csi-controller-sa` and annotates it with the IAM role ARN
5. **EBS CSI driver pods start** and assume the IAM role automatically

### Current State (Addon Already Exists)

Since the addon already exists WITHOUT the IAM role:

1. You must **import** the addon first: 
   ```bash
   terraform import 'module.eks.aws_eks_addon.this["aws-ebs-csi-driver"]' ml-speech-emotion-prod-eks:aws-ebs-csi-driver
   ```
2. Then `terraform apply` will **UPDATE** the addon to include the IAM role

## Recommended Terraform Workflow

### Option 1: Current Setup (Requires Import on Existing Clusters)

**Pros:**
- Single terraform apply creates everything
- IAM role automatically attached to addon

**Cons:**
- Requires manual import if addon already exists
- Requires two applies if you change the IAM role configuration

**Commands:**
```bash
# First time on existing cluster
terraform import 'module.eks.aws_eks_addon.this["aws-ebs-csi-driver"]' ml-speech-emotion-prod-eks:aws-ebs-csi-driver

# Then apply
terraform apply

# After destroy, just:
terraform apply
```

### Option 2: Separate IAM Role Annotation (Alternative)

You could remove `service_account_role_arn` from the addon config and manually annotate:

```terraform
# In main.tf cluster_addons
aws-ebs-csi-driver = {
  most_recent = true
  # Remove: service_account_role_arn
}
```

Then add a separate kubectl annotation:
```bash
kubectl annotate serviceaccount ebs-csi-controller-sa \
  -n kube-system \
  eks.amazonaws.com/role-arn=${IAM_ROLE_ARN} \
  --overwrite
```

**Not recommended** - better to use terraform for everything.

## What Happens on Fresh Install

### Sequence of Events:

```
1. terraform apply
   ↓
2. Creates VPC, subnets, security groups
   ↓
3. Creates EKS cluster with IRSA OIDC provider
   ↓
4. Creates IAM role for EBS CSI driver
   - Trust policy allows kube-system:ebs-csi-controller-sa
   - Attaches AmazonEBSCSIDriverPolicy
   ↓
5. Installs EBS CSI addon with service_account_role_arn
   ↓
6. EKS automatically:
   - Creates ebs-csi-controller-sa service account
   - Annotates it with IAM role ARN
   - Mounts OIDC token to pod
   ↓
7. EBS CSI driver pods start
   - Assume IAM role via OIDC token
   - Can now call EC2 APIs (DescribeAvailabilityZones, CreateVolume, etc.)
   ↓
8. Monitoring PVCs can be provisioned
```

## Verification After Fresh Install

```bash
# 1. Check IAM role exists
aws iam get-role --role-name ml-speech-emotion-ebs-csi-XXXXXXXX

# 2. Check addon installed with IAM role
aws eks describe-addon \
  --cluster-name ml-speech-emotion-prod-eks \
  --addon-name aws-ebs-csi-driver \
  --query 'addon.serviceAccountRoleArn'

# 3. Check service account has annotation
kubectl get sa ebs-csi-controller-sa -n kube-system -o yaml | grep eks.amazonaws.com/role-arn

# Should show:
# eks.amazonaws.com/role-arn: arn:aws:iam::303440520181:role/ml-speech-emotion-ebs-csi-XXXXX

# 4. Check EBS CSI controller pods running
kubectl get pods -n kube-system | grep ebs-csi-controller

# Should show:
# ebs-csi-controller-xxx   6/6   Running

# 5. Test PVC provisioning
kubectl apply -f - <<YAML
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: gp2
  resources:
    requests:
      storage: 1Gi
YAML

# Check if it binds
kubectl get pvc test-pvc
# Should show: Bound

# Clean up test
kubectl delete pvc test-pvc
```

## Common Issues

### Issue 1: "Addon already exists"
**Symptom:** `ResourceInUseException: Addon already exists`  
**Solution:** Import the addon first (see commands above)

### Issue 2: EBS CSI controller CrashLoopBackOff after fresh install
**Symptom:** Pods crash with "unauthorized to perform ec2:DescribeAvailabilityZones"  
**Root Cause:** IAM role not properly attached or trust policy incorrect  
**Solution:** 
```bash
# Check service account annotation
kubectl describe sa ebs-csi-controller-sa -n kube-system

# If missing annotation, restart addon
aws eks update-addon \
  --cluster-name ml-speech-emotion-prod-eks \
  --addon-name aws-ebs-csi-driver \
  --resolve-conflicts OVERWRITE
```

### Issue 3: PVCs stuck in Pending after fresh install
**Symptom:** PVCs don't bind, events show "waiting for volume to be created"  
**Root Cause:** EBS CSI driver not running or misconfigured  
**Solution:**
```bash
# Check controller logs
kubectl logs -n kube-system -l app=ebs-csi-controller -c csi-provisioner --tail=50

# Look for authorization errors or connection issues
```

## Terraform State After Destroy

When you run `terraform destroy`:
- All AWS resources deleted (EKS cluster, IAM roles, VPC, etc.)
- Terraform state file updated to remove all resources
- Next `terraform apply` will create everything fresh

**No import needed** on fresh install after destroy.

## Summary

✅ **Yes**, terraform will automatically create the EBS CSI driver with IAM role after destroy  
✅ The terraform-aws-modules/eks module handles the proper creation order  
✅ **Only need to import** if the addon already exists from previous manual installation  
⚠️ After fresh install, verify the service account has the IAM role annotation  
⚠️ If issues occur, check EBS CSI controller pod logs for authorization errors  

## Files Involved

- `deployment/terraform/main.tf` - EKS cluster and addon configuration
- `deployment/terraform/import-addons.sh` - One-time import script (only for existing clusters)
- `MONITORING_FIX_SUMMARY.md` - Manual fix steps if needed
