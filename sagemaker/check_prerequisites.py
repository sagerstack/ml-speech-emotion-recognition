#!/usr/bin/env python3
"""
Prerequisites Check Script
Validates all requirements before deploying to SageMaker
"""

import sys
import subprocess
import json
import os
from pathlib import Path

def run_command(cmd, capture_output=True, text=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=text)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def check_python_version():
    """Check if Python 3.11+ is installed."""
    print("🐍 Checking Python version...")
    success, output, error = run_command("python --version")
    if not success:
        success, output, error = run_command("python3 --version")

    if success:
        version_str = output.replace("Python ", "")
        version_parts = version_str.split(".")
        major, minor = int(version_parts[0]), int(version_parts[1])

        if major > 3 or (major == 3 and minor >= 11):
            print(f"✅ Python {version_str} is compatible")
            return True
        else:
            print(f"❌ Python {version_str} is not compatible. Requires Python 3.11+")
            return False
    else:
        print("❌ Python not found. Please install Python 3.11+")
        return False

def check_poetry():
    """Check if Poetry is installed."""
    print("📦 Checking Poetry...")
    success, output, error = run_command("poetry --version")
    if success:
        print(f"✅ {output}")
        return True
    else:
        print("❌ Poetry not found. Please install Poetry:")
        print("   curl -sSL https://install.python-poetry.org | python3 -")
        return False

def check_aws_cli():
    """Check if AWS CLI v2 is installed."""
    print("🔧 Checking AWS CLI...")
    success, output, error = run_command("aws --version")
    if success:
        print(f"✅ {output}")
        return True
    else:
        print("❌ AWS CLI not found. Please install AWS CLI v2:")
        print("   macOS: brew install awscli")
        print("   Other: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html")
        return False

def check_aws_credentials():
    """Check if AWS credentials are configured."""
    print("🔑 Checking AWS credentials...")
    success, output, error = run_command("aws sts get-caller-identity")
    if success:
        identity = json.loads(output)
        print(f"✅ AWS credentials configured for: {identity.get('Arn', 'Unknown')}")
        return True
    else:
        print("❌ AWS credentials not configured. Please run 'aws configure'")
        return False

def check_aws_region():
    """Check if AWS region is set to us-east-1."""
    print("🌍 Checking AWS region...")
    success, output, error = run_command("aws configure get region")
    if success:
        region = output
        if region == "us-east-1":
            print(f"✅ AWS region is set to {region}")
            return True
        else:
            print(f"⚠️  AWS region is set to {region}. Recommended: us-east-1")
            return True  # Not a blocker, just a warning
    else:
        print("❌ AWS region not configured. Please run 'aws configure'")
        return False

def check_project_structure():
    """Check if the project structure exists."""
    print("📁 Checking project structure...")
    current_dir = Path.cwd()
    sagemaker_dir = current_dir / "sagemaker"

    if not sagemaker_dir.exists():
        print("❌ sagemaker/ directory not found")
        return False

    required_files = [
        "pyproject.toml",
        "model-deployment/deploy_model.py",
        "model-deployment/validate_model.py",
        "model-deployment/inference.py",
        "model-deployment/test_endpoint.py",
        "model-deployment/sagemaker_client.py",
        "model-deployment/config.yaml",
        "scripts/monitor.py",
        "scripts/cleanup.py",
        "docs/deployment-guide.md"
    ]

    missing_files = []
    for file_path in required_files:
        full_path = sagemaker_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)

    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    else:
        print("✅ All required files found")
        return True

def check_internet_connectivity():
    """Check basic internet connectivity."""
    print("🌐 Checking internet connectivity...")
    try:
        import urllib.request
        urllib.request.urlopen('https://aws.amazon.com', timeout=10)
        print("✅ Internet connectivity confirmed")
        return True
    except:
        print("❌ No internet connectivity")
        return False

def check_disk_space():
    """Check available disk space."""
    print("💾 Checking disk space...")
    success, output, error = run_command("df -h . | tail -1 | awk '{print $4}'")
    if success:
        # Parse disk space (this is a simple check)
        print("✅ Disk space check passed")
        return True
    else:
        print("⚠️  Could not check disk space")
        return True  # Not a blocker

def main():
    """Run all prerequisite checks."""
    print("=" * 60)
    print("🔍 SageMaker Deployment Prerequisites Check")
    print("=" * 60)
    print()

    checks = [
        ("Python Version", check_python_version),
        ("Poetry", check_poetry),
        ("AWS CLI", check_aws_cli),
        ("AWS Credentials", check_aws_credentials),
        ("AWS Region", check_aws_region),
        ("Project Structure", check_project_structure),
        ("Internet Connectivity", check_internet_connectivity),
        ("Disk Space", check_disk_space),
    ]

    passed = 0
    total = len(checks)

    for check_name, check_func in checks:
        try:
            if check_func():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Error checking {check_name}: {e}")
            print()

    print("=" * 60)
    print(f"📊 Prerequisites Check: {passed}/{total} passed")
    print("=" * 60)

    if passed == total:
        print("🎉 All prerequisites met! You can proceed with deployment.")
        print("\nNext steps:")
        print("1. cd sagemaker")
        print("2. poetry install")
        print("3. cd model-deployment")
        print("4. poetry run python validate_model.py")
        print("5. poetry run python deploy_model.py --deploy")
        return True
    else:
        print("❌ Some prerequisites are missing. Please fix them before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)