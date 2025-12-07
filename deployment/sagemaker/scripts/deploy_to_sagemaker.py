#!/usr/bin/env python3
"""
SageMaker Model Deployment Orchestration Script

This script orchestrates the deployment of ML models to AWS SageMaker endpoints.
It handles creating/updating SageMaker models, endpoint configurations, and endpoints.

Usage:
    python deploy_to_sagemaker.py \\
        --model-version v5 \\
        --endpoint-name ml-emotion-prod \\
        --instance-type ml.t3.medium \\
        --s3-uri s3://bucket/sagemaker-models/v5/model.tar.gz \\
        --region us-east-1
"""

import argparse
import sys
import time
import os
import logging
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SageMakerDeployer:
    """Handles deployment of models to SageMaker endpoints."""

    # Custom container with sklearn 1.7.2 + numpy 2.1.0 + Python 3.10
    # Built from deployment/sagemaker/container/
    SKLEARN_CONTAINER_IMAGES = {
        'us-east-1': '303440520181.dkr.ecr.us-east-1.amazonaws.com/ml-speech-emotion-sklearn:1.7.2-py310',
        'us-west-2': '303440520181.dkr.ecr.us-east-1.amazonaws.com/ml-speech-emotion-sklearn:1.7.2-py310',
        'eu-west-1': '303440520181.dkr.ecr.us-east-1.amazonaws.com/ml-speech-emotion-sklearn:1.7.2-py310',
    }

    def __init__(self, region: str, execution_role_name: str = None, execution_role_arn: str = None):
        """
        Initialize SageMaker deployer.

        Args:
            region: AWS region
            execution_role_name: Name of SageMaker execution role (will be auto-detected if not provided)
            execution_role_arn: ARN of SageMaker execution role (takes precedence over execution_role_name)
        """
        self.region = region
        self.sagemaker_client = boto3.client('sagemaker', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)

        # Get container image for region
        self.container_image = self.SKLEARN_CONTAINER_IMAGES.get(
            region,
            self.SKLEARN_CONTAINER_IMAGES['us-east-1']  # Fallback to us-east-1
        )

        # Get or discover execution role
        if execution_role_arn:
            # Use ARN directly (no IAM API call needed)
            self.execution_role_arn = execution_role_arn
        elif execution_role_name:
            self.execution_role_arn = self._get_role_arn(execution_role_name)
        else:
            self.execution_role_arn = self._discover_sagemaker_role()

        logger.info(f"Initialized SageMakerDeployer for region: {region}")
        logger.info(f"Container image: {self.container_image}")
        logger.info(f"Execution role: {self.execution_role_arn}")

    def _get_role_arn(self, role_name: str) -> str:
        """Get ARN for IAM role by name."""
        try:
            response = self.iam_client.get_role(RoleName=role_name)
            return response['Role']['Arn']
        except ClientError as e:
            logger.error(f"Failed to get role ARN: {e}")
            raise

    def _discover_sagemaker_role(self) -> str:
        """Auto-discover SageMaker execution role."""
        try:
            # Look for role with "sagemaker" in the name
            response = self.iam_client.list_roles()
            for role in response['Roles']:
                if 'sagemaker' in role['RoleName'].lower() and 'execution' in role['RoleName'].lower():
                    logger.info(f"Discovered SageMaker role: {role['RoleName']}")
                    return role['Arn']

            raise ValueError("Could not find SageMaker execution role. Please specify --execution-role")

        except ClientError as e:
            logger.error(f"Failed to discover SageMaker role: {e}")
            raise

    def create_model(
        self,
        model_name: str,
        model_data_url: str,
        model_version: str
    ) -> str:
        """
        Create SageMaker model.

        Args:
            model_name: Name for the SageMaker model
            model_data_url: S3 URI of model.tar.gz
            model_version: Model version (e.g., v5)

        Returns:
            Model ARN
        """
        logger.info(f"Creating SageMaker model: {model_name}")

        try:
            response = self.sagemaker_client.create_model(
                ModelName=model_name,
                PrimaryContainer={
                    'Image': self.container_image,
                    'ModelDataUrl': model_data_url,
                    'Environment': {
                        'SAGEMAKER_PROGRAM': 'inference.py',
                        'SAGEMAKER_SUBMIT_DIRECTORY': '/opt/ml/model/code',
                        'MODEL_VERSION': model_version,
                    }
                },
                ExecutionRoleArn=self.execution_role_arn,
                Tags=[
                    {'Key': 'model_version', 'Value': model_version},
                    {'Key': 'git_commit', 'Value': os.getenv('GITHUB_SHA', 'unknown')},
                    {'Key': 'deployed_by', 'Value': 'github-actions'},
                ]
            )

            model_arn = response['ModelArn']
            logger.info(f"✓ Model created: {model_arn}")
            return model_arn

        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException' and ('already exists' in str(e) or 'already existing' in str(e)):
                logger.warning(f"Model {model_name} already exists, skipping creation")
                # Get existing model ARN
                response = self.sagemaker_client.describe_model(ModelName=model_name)
                return response['ModelArn']
            else:
                logger.error(f"Failed to create model: {e}")
                raise

    def create_endpoint_config(
        self,
        config_name: str,
        model_name: str,
        instance_type: str,
        initial_instance_count: int = 1
    ) -> str:
        """
        Create SageMaker endpoint configuration.

        Args:
            config_name: Name for the endpoint configuration
            model_name: Name of the SageMaker model
            instance_type: EC2 instance type (e.g., ml.t3.medium)
            initial_instance_count: Number of instances to launch initially

        Returns:
            Endpoint config ARN
        """
        logger.info(f"Creating endpoint configuration: {config_name}")

        try:
            response = self.sagemaker_client.create_endpoint_config(
                EndpointConfigName=config_name,
                ProductionVariants=[
                    {
                        'VariantName': 'AllTraffic',
                        'ModelName': model_name,
                        'InstanceType': instance_type,
                        'InitialInstanceCount': initial_instance_count,
                        'InitialVariantWeight': 1.0,
                    }
                ]
            )

            config_arn = response['EndpointConfigArn']
            logger.info(f"✓ Endpoint config created: {config_arn}")
            return config_arn

        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException' and ('already exists' in str(e) or 'already existing' in str(e)):
                logger.warning(f"Endpoint config {config_name} already exists, skipping creation")
                response = self.sagemaker_client.describe_endpoint_config(EndpointConfigName=config_name)
                return response['EndpointConfigArn']
            else:
                logger.error(f"Failed to create endpoint config: {e}")
                raise

    def create_or_update_endpoint(
        self,
        endpoint_name: str,
        config_name: str,
        timeout_seconds: int = 900
    ) -> Dict:
        """
        Create or update SageMaker endpoint.

        Args:
            endpoint_name: Name for the endpoint
            config_name: Name of the endpoint configuration
            timeout_seconds: Maximum time to wait for endpoint (default: 15 minutes)

        Returns:
            Endpoint details
        """
        try:
            # Check if endpoint already exists
            try:
                self.sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
                endpoint_exists = True
                logger.info(f"Endpoint {endpoint_name} exists, will update")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ValidationException':
                    endpoint_exists = False
                    logger.info(f"Endpoint {endpoint_name} does not exist, will create")
                else:
                    raise

            # Create or update endpoint
            if endpoint_exists:
                logger.info(f"Updating endpoint: {endpoint_name}")
                self.sagemaker_client.update_endpoint(
                    EndpointName=endpoint_name,
                    EndpointConfigName=config_name
                )
            else:
                logger.info(f"Creating endpoint: {endpoint_name}")
                self.sagemaker_client.create_endpoint(
                    EndpointName=endpoint_name,
                    EndpointConfigName=config_name
                )

            # Wait for endpoint to be InService
            logger.info(f"Waiting for endpoint to be InService (timeout: {timeout_seconds}s)...")
            return self._wait_for_endpoint(endpoint_name, timeout_seconds)

        except Exception as e:
            logger.error(f"Failed to create/update endpoint: {e}")
            raise

    def _wait_for_endpoint(self, endpoint_name: str, timeout_seconds: int) -> Dict:
        """
        Wait for endpoint to reach InService status.

        Args:
            endpoint_name: Name of the endpoint
            timeout_seconds: Maximum time to wait

        Returns:
            Endpoint details

        Raises:
            TimeoutError: If endpoint doesn't reach InService within timeout
            RuntimeError: If endpoint fails
        """
        start_time = time.time()
        poll_interval = 10  # Start with 10 seconds

        while True:
            elapsed = time.time() - start_time

            if elapsed > timeout_seconds:
                raise TimeoutError(
                    f"Endpoint {endpoint_name} did not reach InService status within {timeout_seconds}s"
                )

            try:
                response = self.sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
                status = response['EndpointStatus']

                logger.info(f"Endpoint status: {status} (elapsed: {int(elapsed)}s)")

                if status == 'InService':
                    logger.info(f"✓ Endpoint {endpoint_name} is InService")
                    return response

                elif status in ['Failed', 'RollingBack']:
                    failure_reason = response.get('FailureReason', 'Unknown')
                    raise RuntimeError(f"Endpoint {endpoint_name} failed: {failure_reason}")

                # Exponential backoff (10s → 20s → 30s)
                poll_interval = min(30, poll_interval + 10)
                time.sleep(poll_interval)

            except ClientError as e:
                logger.error(f"Error checking endpoint status: {e}")
                raise

    def delete_old_resources(self, model_name: str, config_name: str):
        """
        Delete old model and endpoint config (cleanup).

        Args:
            model_name: Name of model to delete
            config_name: Name of endpoint config to delete
        """
        try:
            # Delete model
            try:
                self.sagemaker_client.delete_model(ModelName=model_name)
                logger.info(f"✓ Deleted old model: {model_name}")
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFound':
                    logger.warning(f"Failed to delete model {model_name}: {e}")

            # Delete endpoint config
            try:
                self.sagemaker_client.delete_endpoint_config(EndpointConfigName=config_name)
                logger.info(f"✓ Deleted old endpoint config: {config_name}")
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFound':
                    logger.warning(f"Failed to delete endpoint config {config_name}: {e}")

        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")


def main():
    """Main entry point for deployment script."""
    parser = argparse.ArgumentParser(description='Deploy ML model to SageMaker endpoint')
    parser.add_argument('--model-version', required=True, help='Model version (e.g., v5)')
    parser.add_argument('--endpoint-name', required=True, help='SageMaker endpoint name')
    parser.add_argument('--instance-type', default='ml.t3.medium', help='Instance type')
    parser.add_argument('--s3-uri', required=True, help='S3 URI of model.tar.gz')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--execution-role', help='SageMaker execution role name (auto-discovered if not provided)')
    parser.add_argument('--execution-role-arn', help='SageMaker execution role ARN (takes precedence over --execution-role)')
    parser.add_argument('--timeout', type=int, default=900, help='Deployment timeout in seconds')

    args = parser.parse_args()

    try:
        # Initialize deployer
        deployer = SageMakerDeployer(
            region=args.region,
            execution_role_name=args.execution_role,
            execution_role_arn=args.execution_role_arn
        )

        # Generate resource names
        model_name = f"ml-emotion-{args.model_version}"
        config_name = f"ml-emotion-{args.model_version}-config"

        # Deploy model
        logger.info("=" * 60)
        logger.info(f"Starting deployment of model {args.model_version}")
        logger.info("=" * 60)

        # Step 1: Create model
        deployer.create_model(
            model_name=model_name,
            model_data_url=args.s3_uri,
            model_version=args.model_version
        )

        # Step 2: Create endpoint configuration
        deployer.create_endpoint_config(
            config_name=config_name,
            model_name=model_name,
            instance_type=args.instance_type,
            initial_instance_count=1
        )

        # Step 3: Create or update endpoint
        endpoint_details = deployer.create_or_update_endpoint(
            endpoint_name=args.endpoint_name,
            config_name=config_name,
            timeout_seconds=args.timeout
        )

        # Success!
        logger.info("=" * 60)
        logger.info("✅ Deployment completed successfully!")
        logger.info("=" * 60)
        logger.info(f"Endpoint name: {args.endpoint_name}")
        logger.info(f"Endpoint ARN: {endpoint_details['EndpointArn']}")
        logger.info(f"Model version: {args.model_version}")
        logger.info(f"Instance type: {args.instance_type}")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ Deployment failed: {e}")
        logger.error("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
