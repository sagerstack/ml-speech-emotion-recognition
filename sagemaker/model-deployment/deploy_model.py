#!/usr/bin/env python3
"""
SageMaker Model Deployment Script

This script deploys the speech emotion recognition model to AWS SageMaker serverless endpoint.
It handles model packaging, deployment configuration, and endpoint creation.
"""

import os
import sys
import json
import yaml
import logging
import time
import boto3
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import sagemaker
from sagemaker.huggingface import HuggingFaceModel
from sagemaker.serverless.serverless_inference_config import ServerlessInferenceConfig
from sagemaker.utils import name_from_base

# Load environment variables in standard order
# 1. Load .env (base configuration)
env_base = Path(__file__).parent / ".env"
if env_base.exists():
    load_dotenv(env_base)
    logger = logging.getLogger(__name__)
    logger.info(f"✅ Loaded base configuration from {env_base}")
else:
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️  Base configuration file not found: {env_base}")

# 2. Load .env.local (local overrides)
env_local = Path(__file__).parent / ".env.local"
if env_local.exists():
    load_dotenv(env_local, override=True)
    logger.info(f"✅ Loaded local overrides from {env_local}")
else:
    logger.warning(f"⚠️  Local configuration file not found: {env_local}")
    logger.warning("Please create .env.local with your AWS credentials")

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SageMakerDeployment:
    """Handles deployment of speech emotion recognition model to SageMaker."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the deployment manager."""
        self.config_path = config_path
        self.config = self._load_config()
        self._validate_credentials()
        self.session = self._initialize_sagemaker_session()
        self.role = self._get_or_create_execution_role()
        self.s3_client = self.session.boto_session.client('s3')

    def _load_config(self) -> Dict[str, Any]:
        """Load deployment configuration."""
        try:
            config_file = Path(__file__).parent / self.config_path
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ Configuration loaded from {config_file}")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            raise

    def _validate_credentials(self):
        """Validate AWS credentials are properly configured."""
        required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
        missing_vars = []

        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            logger.error("❌ Missing required AWS credentials:")
            for var in missing_vars:
                logger.error(f"   - {var}")
            logger.error("Please set your AWS credentials in .env.local:")
            logger.error("   AWS_ACCESS_KEY_ID=your_access_key")
            logger.error("   AWS_SECRET_ACCESS_KEY=your_secret_key")
            raise ValueError("Missing AWS credentials")

        logger.info("✅ AWS credentials validated")

    def _initialize_sagemaker_session(self) -> sagemaker.Session:
        """Initialize SageMaker session."""
        try:
            region = self.config['aws']['region']
            logger.info(f"Initializing SageMaker session in region: {region}")

            session = sagemaker.Session(
                boto_session=boto3.Session(
                    region_name=region,
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                )
            )

            logger.info(f"✅ SageMaker session initialized")
            logger.info(f"SageMaker bucket: {session.default_bucket()}")
            return session

        except Exception as e:
            logger.error(f"❌ Failed to initialize SageMaker session: {e}")
            raise

    def _get_or_create_execution_role(self) -> str:
        """Get or create SageMaker execution role."""
        try:
            role_name = self.config['aws']['role_name']
            logger.info(f"Looking for SageMaker execution role: {role_name}")

            # Try to get existing role
            iam = self.session.boto_session.client('iam')
            try:
                response = iam.get_role(RoleName=role_name)
                role_arn = response['Role']['Arn']
                logger.info(f"✅ Found existing role: {role_arn}")
                return role_arn
            except iam.exceptions.NoSuchEntityException:
                logger.info(f"Role {role_name} not found, creating new role...")
                return self._create_sagemaker_role(role_name)

        except Exception as e:
            logger.error(f"❌ Failed to get/create execution role: {e}")
            raise

    def _create_sagemaker_role(self, role_name: str) -> str:
        """Create SageMaker execution role with required policies."""
        try:
            iam = self.session.boto_session.client('iam')

            # Create trust policy
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "sagemaker.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }

            # Create role
            response = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="SageMaker execution role for speech emotion recognition"
            )
            role_arn = response['Role']['Arn']
            logger.info(f"✅ Created role: {role_arn}")

            # Attach policies
            policies = [
                'arn:aws:iam::aws:policy/AmazonSageMakerFullAccess',
                'arn:aws:iam::aws:policy/AmazonS3FullAccess',
                'arn:aws:iam::aws:policy/CloudWatchFullAccess'
            ]

            for policy_arn in policies:
                iam.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
                logger.info(f"✅ Attached policy: {policy_arn}")

            # Wait for role to be ready
            logger.info("Waiting for role to be ready...")
            time.sleep(10)

            return role_arn

        except Exception as e:
            logger.error(f"❌ Failed to create role: {e}")
            raise

    def _create_model_artifacts(self) -> str:
        """Create model artifacts and upload to S3."""
        try:
            logger.info("Creating model artifacts...")

            # Create model directory
            model_dir = Path("model_artifacts")
            model_dir.mkdir(exist_ok=True)

            # Copy inference script and requirements
            import shutil
            current_dir = Path(__file__).parent

            shutil.copy2(
                current_dir / "inference.py",
                model_dir / "inference.py"
            )
            shutil.copy2(
                current_dir / "requirements.txt",
                model_dir / "requirements.txt"
            )

            # Create model.tar.gz
            import tarfile
            tar_path = "model.tar.gz"
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(model_dir, arcname=".")

            # Upload to S3
            s3_path = self.session.upload_data(
                tar_path,
                bucket=self.session.default_bucket(),
                key_prefix=self.config['aws']['bucket_prefix']
            )

            logger.info(f"✅ Model artifacts uploaded to: {s3_path}")

            # Clean up local files
            os.remove(tar_path)
            shutil.rmtree(model_dir)

            return s3_path

        except Exception as e:
            logger.error(f"❌ Failed to create model artifacts: {e}")
            raise

    def _create_serverless_config(self) -> ServerlessInferenceConfig:
        """Create serverless inference configuration."""
        try:
            serverless_config = ServerlessInferenceConfig(
                memory_size_in_mb=self.config['serverless']['memory_size_in_mb'],
                max_concurrency=self.config['serverless']['max_concurrency']
            )

            logger.info("✅ Serverless configuration created:")
            logger.info(f"  Memory: {serverless_config.memory_size_in_mb}MB")
            logger.info(f"  Max Concurrency: {serverless_config.max_concurrency}")
            logger.info(f"  Timeout: {self.config['serverless']['timeout_in_seconds']}s (handled by model container)")

            return serverless_config

        except Exception as e:
            logger.error(f"❌ Failed to create serverless config: {e}")
            raise

    def _is_serverless_deployment(self) -> bool:
        """Check if deployment should be serverless based on config."""
        return 'serverless' in self.config

    def _get_deployment_config(self) -> Dict[str, Any]:
        """Get deployment configuration (serverless or provisioned)."""
        if self._is_serverless_deployment():
            return {
                'type': 'serverless',
                'initial_instance_count': None,
                'instance_type': None,
                'serverless_inference_config': self._create_serverless_config(),
                'memory_size': self.config['serverless']['memory_size_in_mb'],
                'max_concurrency': self.config['serverless']['max_concurrency'],
                'timeout': self.config['serverless']['timeout_in_seconds']
            }
        else:
            return {
                'type': 'provisioned',
                'initial_instance_count': 1,
                'instance_type': self.config['model']['instance_type'],
                'memory_size': None,  # Not applicable for provisioned
                'max_concurrency': None,  # Not applicable for provisioned
                'timeout': None  # Not applicable for provisioned
            }

    def deploy_model(self, endpoint_name: Optional[str] = None) -> Dict[str, Any]:
        """Deploy model to SageMaker endpoint (serverless or provisioned)."""
        try:
            logger.info("🚀 Starting model deployment to SageMaker...")
            logger.info("=" * 60)

            # Generate endpoint name if not provided
            if not endpoint_name:
                timestamp = int(time.time())
                endpoint_name = f"speech-emotion-{timestamp}"

            logger.info(f"Endpoint name: {endpoint_name}")

            # Get deployment configuration
            deploy_config = self._get_deployment_config()
            deployment_type = deploy_config['type']
            logger.info(f"Deployment type: {deployment_type}")

            # Step 1: Create model artifacts
            logger.info("Step 1/4: Creating model artifacts...")
            model_artifacts = self._create_model_artifacts()

            # Step 2: Create HuggingFace model
            logger.info("Step 2/4: Creating HuggingFace model...")
            model_config = self.config['model']

            huggingface_model = HuggingFaceModel(
                name=f"{endpoint_name}-model",
                model_data=model_artifacts,
                role=self.role,
                transformers_version='4.37.0',
                pytorch_version='2.1.0',
                py_version='py310',
                env={
                    'SAGEMAKER_PROGRAM': 'inference.py',
                    'SAGEMAKER_SUBMIT_DIRECTORY': '/opt/ml/model/code',
                    'SAGEMAKER_CONTAINER_LOG_LEVEL': '20',
                    'SAGEMAKER_REGION': self.config['aws']['region']
                }
            )

            logger.info("✅ HuggingFace model created")

            # Step 3: Create deployment configuration
            logger.info(f"Step 3/4: Creating {deployment_type} configuration...")

            if deployment_type == 'serverless':
                logger.info("✅ Serverless configuration created:")
                logger.info(f"  Memory: {deploy_config['memory_size']}MB")
                logger.info(f"  Max Concurrency: {deploy_config['max_concurrency']}")
                logger.info(f"  Timeout: {deploy_config['timeout']}s (handled by model container)")
            else:
                logger.info("✅ Provisioned configuration created:")
                logger.info(f"  Instance Type: {deploy_config['instance_type']}")
                logger.info(f"  Initial Instance Count: {deploy_config['initial_instance_count']}")

            # Step 4: Deploy model
            logger.info(f"Step 4/4: Deploying model to {deployment_type} endpoint...")
            if deployment_type == 'serverless':
                logger.info("This may take 10-15 minutes...")
            else:
                logger.info("This may take 5-10 minutes for GPU instance...")

            predictor = huggingface_model.deploy(
                initial_instance_count=deploy_config['initial_instance_count'],
                instance_type=deploy_config['instance_type'],
                serverless_inference_config=deploy_config.get('serverless_inference_config'),
                endpoint_name=endpoint_name,
                wait=True
            )

            logger.info("✅ Model deployed successfully!")

            # Get endpoint information
            endpoint_info = self._get_endpoint_info(endpoint_name)

            # Build deployment info based on deployment type
            deployment_info = {
                "endpoint_name": endpoint_name,
                "endpoint_arn": endpoint_info.get("EndpointArn"),
                "model_name": huggingface_model.name,
                "model_artifacts": model_artifacts,
                "instance_type": deployment_type,
                "memory_size": deploy_config['memory_size'],
                "max_concurrency": deploy_config['max_concurrency'],
                "timeout": deploy_config['timeout'],
                "status": endpoint_info.get("EndpointStatus"),
                "creation_time": endpoint_info.get("CreationTime"),
                "region": self.config['aws']['region']
            }

            logger.info("=" * 60)
            logger.info("🎉 Deployment completed successfully!")
            logger.info(f"Endpoint Name: {endpoint_name}")
            logger.info(f"Endpoint Status: {deployment_info['status']}")
            logger.info(f"Instance Type: {deployment_info['instance_type']}")

            if deployment_type == 'serverless':
                logger.info(f"Memory Size: {deployment_info['memory_size']}MB")
                logger.info(f"Max Concurrency: {deployment_info['max_concurrency']}")
                logger.info(f"Timeout: {deployment_info['timeout']}s")
            else:
                logger.info(f"Instance Type: {deploy_config['instance_type']}")
                logger.info("GPU acceleration enabled")

            return deployment_info

        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            raise

    def _get_endpoint_info(self, endpoint_name: str) -> Dict[str, Any]:
        """Get endpoint information."""
        try:
            sagemaker_client = self.session.boto_session.client('sagemaker')
            response = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
            return response
        except Exception as e:
            logger.warning(f"Could not get endpoint info: {e}")
            return {}

    def delete_endpoint(self, endpoint_name: str, delete_model: bool = True) -> bool:
        """Delete endpoint and optionally model."""
        try:
            logger.info(f"🗑️  Deleting endpoint: {endpoint_name}")
            sagemaker_client = self.session.boto_session.client('sagemaker')

            # Delete endpoint
            sagemaker_client.delete_endpoint(EndpointName=endpoint_name)
            logger.info(f"✅ Endpoint {endpoint_name} deleted")

            if delete_model:
                # Get endpoint config to find model name
                try:
                    endpoint_config = sagemaker_client.describe_endpoint_config(
                        EndpointConfigName=endpoint_name
                    )
                    model_name = endpoint_config['ProductionVariants'][0]['ModelName']

                    # Delete endpoint config
                    sagemaker_client.delete_endpoint_config(EndpointConfigName=endpoint_name)
                    logger.info(f"✅ Endpoint config {endpoint_name} deleted")

                    # Delete model
                    sagemaker_client.delete_model(ModelName=model_name)
                    logger.info(f"✅ Model {model_name} deleted")

                except Exception as e:
                    logger.warning(f"Could not delete model: {e}")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to delete endpoint: {e}")
            return False

    def list_endpoints(self) -> List[Dict[str, Any]]:
        """List all SageMaker endpoints."""
        try:
            sagemaker_client = self.session.boto_session.client('sagemaker')
            response = sagemaker_client.list_endpoints(
                SortBy='CreationTime',
                SortOrder='Descending'
            )
            return response['Endpoints']
        except Exception as e:
            logger.error(f"❌ Failed to list endpoints: {e}")
            return []

    def get_endpoint_metrics(self, endpoint_name: str) -> Dict[str, Any]:
        """Get CloudWatch metrics for endpoint."""
        try:
            cloudwatch = self.session.boto_session.client('cloudwatch')

            metrics = {}
            metric_names = ['Invocations', 'Invocation4XXErrors', 'Invocation5XXErrors', 'ModelLatency']

            for metric_name in metric_names:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/SageMaker',
                    MetricName=metric_name,
                    Dimensions=[
                        {
                            'Name': 'EndpointName',
                            'Value': endpoint_name
                        }
                    ],
                    StartTime=time.time() - 3600,  # Last hour
                    EndTime=time.time(),
                    Period=300,  # 5 minutes
                    Statistics=['Sum', 'Average']
                )

                if response['Datapoints']:
                    metrics[metric_name] = response['Datapoints'][-1]  # Latest datapoint

            return metrics

        except Exception as e:
            logger.warning(f"Could not get endpoint metrics: {e}")
            return {}

    def monitor_costs(self) -> Dict[str, Any]:
        """Get cost monitoring information."""
        try:
            # Get cost explorer data for the last month
            ce = self.session.boto_session.client('ce')
            end_date = time.strftime('%Y-%m-%d')
            start_date = time.strftime('%Y-%m-%d', time.localtime(time.time() - 30*24*60*60))

            response = ce.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'}
                ],
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': ['Amazon SageMaker']
                    }
                }
            )

            sage_costs = response['ResultsByTime'][0]['Groups'][0]['Amounts']['BlendedCost']
            cost_threshold = self.config['cost_optimization']['cost_alert_threshold']

            cost_info = {
                'current_month_cost': float(sage_costs),
                'alert_threshold': cost_threshold,
                'alert_triggered': float(sage_costs) > cost_threshold
            }

            if cost_info['alert_triggered']:
                logger.warning(f"⚠️  Cost alert: ${cost_info['current_month_cost']:.2f} exceeds threshold of ${cost_threshold:.2f}")

            return cost_info

        except Exception as e:
            logger.warning(f"Could not get cost information: {e}")
            return {}


def main():
    """Main deployment function."""
    import argparse

    parser = argparse.ArgumentParser(description="Deploy speech emotion recognition model to SageMaker")
    parser.add_argument("--deploy", action="store_true", help="Deploy model to SageMaker")
    parser.add_argument("--delete", type=str, help="Delete specified endpoint")
    parser.add_argument("--list", action="store_true", help="List all endpoints")
    parser.add_argument("--metrics", type=str, help="Get metrics for specified endpoint")
    parser.add_argument("--monitor", action="store_true", help="Monitor costs")
    parser.add_argument("--endpoint", type=str, help="Endpoint name for deployment")
    parser.add_argument("--config", type=str, default="config.yaml", help="Configuration file path")

    args = parser.parse_args()

    try:
        deployment = SageMakerDeployment(args.config)

        if args.deploy:
            result = deployment.deploy_model(args.endpoint)
            print(json.dumps(result, indent=2, default=str))

        elif args.delete:
            success = deployment.delete_endpoint(args.delete)
            if success:
                print(f"✅ Endpoint {args.delete} deleted successfully")
            else:
                print(f"❌ Failed to delete endpoint {args.delete}")

        elif args.list:
            endpoints = deployment.list_endpoints()
            print("SageMaker Endpoints:")
            for endpoint in endpoints:
                print(f"  - {endpoint['EndpointName']} ({endpoint['EndpointStatus']})")

        elif args.metrics:
            metrics = deployment.get_endpoint_metrics(args.metrics)
            print(f"Metrics for {args.metrics}:")
            for metric, data in metrics.items():
                print(f"  {metric}: {data}")

        elif args.monitor:
            costs = deployment.monitor_costs()
            print(f"Cost Monitoring:")
            print(f"  Current Month Cost: ${costs['current_month_cost']:.2f}")
            print(f"  Alert Threshold: ${costs['alert_threshold']:.2f}")
            print(f"  Alert Triggered: {costs['alert_triggered']}")

        else:
            parser.print_help()

    except Exception as e:
        logger.error(f"❌ Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()