#!/usr/bin/env python3
"""
SageMaker Endpoint Disabler

This script safely disables a SageMaker endpoint by updating its configuration
to use 0 instances, effectively stopping it while preserving the endpoint
for later re-enabling.

Usage:
    python disable_endpoint.py --endpoint-name speech-emotion-1763484306
    python disable_endpoint.py --endpoint-name speech-emotion-1763484306 --confirm
"""

import argparse
import json
import logging
import sys
import time
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SageMakerEndpointDisabler:
    """Utility class for safely disabling SageMaker endpoints."""

    def __init__(self, region: str = "us-east-1"):
        """Initialize the disabler with AWS SageMaker client."""
        self.region = region
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        logger.info(f"✅ SageMaker client initialized for region: {region}")

    def get_endpoint_info(self, endpoint_name: str) -> Dict[str, Any]:
        """Get current endpoint information."""
        try:
            response = self.sagemaker.describe_endpoint(EndpointName=endpoint_name)
            return {
                "EndpointName": response.get("EndpointName"),
                "EndpointArn": response.get("EndpointArn"),
                "EndpointStatus": response.get("EndpointStatus"),
                "EndpointConfigName": response.get("EndpointConfigName"),
                "CreationTime": response.get("CreationTime"),
                "LastModifiedTime": response.get("LastModifiedTime"),
                "ProductionVariants": response.get("ProductionVariants", [])
            }
        except ClientError as e:
            logger.error(f"❌ Failed to get endpoint info: {e}")
            raise

    def get_endpoint_config(self, config_name: str) -> Dict[str, Any]:
        """Get endpoint configuration details."""
        try:
            response = self.sagemaker.describe_endpoint_config(EndpointConfigName=config_name)
            return {
                "EndpointConfigName": response.get("EndpointConfigName"),
                "EndpointConfigArn": response.get("EndpointConfigArn"),
                "ProductionVariants": response.get("ProductionVariants", []),
                "CreationTime": response.get("CreationTime")
            }
        except ClientError as e:
            logger.error(f"❌ Failed to get endpoint config: {e}")
            raise

    def create_disabled_config(
        self,
        endpoint_name: str,
        original_config_name: str,
        original_variants: list
    ) -> str:
        """Create a disabled endpoint configuration using serverless mode."""
        disabled_config_name = f"{endpoint_name}-disabled-config"

        try:
            # For disabling, we'll create a serverless configuration with minimal resources
            # Serverless endpoints have much lower costs when idle
            serverless_config = {
                "MemorySizeInMB": 1024,  # Minimal memory
                "MaxConcurrency": 1      # Minimal concurrency
            }

            disabled_variants = []
            for variant in original_variants:
                disabled_variant = {
                    "VariantName": variant["VariantName"],
                    "ModelName": variant["ModelName"],
                    "ServerlessConfig": serverless_config
                }

                disabled_variants.append(disabled_variant)

            # Create the disabled serverless configuration
            self.sagemaker.create_endpoint_config(
                EndpointConfigName=disabled_config_name,
                ProductionVariants=disabled_variants
            )

            logger.info(f"✅ Created disabled serverless config: {disabled_config_name}")
            return disabled_config_name

        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException' and 'already exists' in str(e):
                logger.warning(f"⚠️  Disabled config already exists: {disabled_config_name}")
                return disabled_config_name
            else:
                logger.error(f"❌ Failed to create disabled config: {e}")
                raise

    def update_endpoint_to_disabled(
        self,
        endpoint_name: str,
        disabled_config_name: str
    ) -> Dict[str, Any]:
        """Update endpoint to use disabled configuration."""
        try:
            response = self.sagemaker.update_endpoint(
                EndpointName=endpoint_name,
                EndpointConfigName=disabled_config_name
            )

            logger.info(f"✅ Update initiated for endpoint: {endpoint_name}")
            return response

        except ClientError as e:
            logger.error(f"❌ Failed to update endpoint: {e}")
            raise

    def wait_for_endpoint_update(
        self,
        endpoint_name: str,
        target_status: str = "InService",
        timeout: int = 600
    ) -> bool:
        """Wait for endpoint to reach target status."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = self.sagemaker.describe_endpoint(EndpointName=endpoint_name)
                current_status = response.get("EndpointStatus")

                logger.info(f"⏳ Endpoint status: {current_status}")

                if current_status == target_status:
                    logger.info(f"✅ Endpoint reached target status: {target_status}")
                    return True

                if current_status in ["Failed", "DeleteFailed"]:
                    logger.error(f"❌ Endpoint failed with status: {current_status}")
                    return False

                time.sleep(30)  # Wait 30 seconds before checking again

            except ClientError as e:
                logger.error(f"❌ Error checking endpoint status: {e}")
                return False

        logger.error(f"❌ Timeout waiting for endpoint to reach status: {target_status}")
        return False

    def wait_for_endpoint_deletion(
        self,
        endpoint_name: str,
        timeout: int = 300
    ) -> bool:
        """Wait for endpoint to be completely deleted."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Try to describe the endpoint - if it's deleted, this will fail
                response = self.sagemaker.describe_endpoint(EndpointName=endpoint_name)
                current_status = response.get("EndpointStatus")

                if current_status == "Deleting":
                    logger.info(f"⏳ Endpoint status: {current_status}")
                elif current_status in ["Failed", "DeleteFailed"]:
                    logger.error(f"❌ Endpoint deletion failed with status: {current_status}")
                    return False

                time.sleep(15)  # Wait 15 seconds before checking again

            except ClientError as e:
                if e.response['Error']['Code'] == 'ValidationError':
                    # Endpoint doesn't exist anymore - deletion complete
                    logger.info("✅ Endpoint no longer exists - deletion complete")
                    return True
                else:
                    logger.error(f"❌ Error checking endpoint deletion: {e}")
                    return False

        logger.error(f"❌ Timeout waiting for endpoint deletion")
        return False

    def disable_endpoint(self, endpoint_name: str, wait_for_completion: bool = True) -> Dict[str, Any]:
        """
        Disable endpoint by deleting it but preserving configuration for recreation.

        Args:
            endpoint_name: Name of the endpoint to disable
            wait_for_completion: Whether to wait for the deletion to complete

        Returns:
            Dictionary with disable operation details
        """
        logger.info(f"🔄 Starting disable process for endpoint: {endpoint_name}")
        logger.info("   Note: Deleting endpoint but preserving config for easy recreation")

        try:
            # Step 1: Get current endpoint information before deletion
            logger.info("📋 Getting current endpoint information...")
            endpoint_info = self.get_endpoint_info(endpoint_name)
            original_config_name = endpoint_info["EndpointConfigName"]
            current_status = endpoint_info["EndpointStatus"]

            # Get configuration variants
            config_info = self.get_endpoint_config(original_config_name)
            original_variants = config_info["ProductionVariants"]

            logger.info(f"   Current config: {original_config_name}")
            logger.info(f"   Current status: {current_status}")
            logger.info(f"   Current variants: {len(original_variants)}")

            # Save complete recreation information
            disable_info = {
                "endpoint_name": endpoint_name,
                "original_config_name": original_config_name,
                "original_variants": original_variants,
                "disable_timestamp": time.time(),
                "disable_reason": "cost_savings_delete",
                "previous_status": current_status
            }

            # Save disable info to file for re-enabling
            disable_info_file = f"{endpoint_name}_disable_info.json"
            with open(disable_info_file, 'w') as f:
                json.dump(disable_info, f, indent=2, default=str)
            logger.info(f"💾 Saved recreation info to: {disable_info_file}")

            # Step 2: Delete the endpoint (this stops billing)
            logger.info("🗑️  Deleting endpoint to stop billing...")
            self.sagemaker.delete_endpoint(EndpointName=endpoint_name)
            logger.info(f"✅ Endpoint {endpoint_name} deletion initiated")

            if wait_for_completion:
                # Step 3: Wait for endpoint deletion to complete
                logger.info("⏳ Waiting for endpoint deletion to complete...")
                success = self.wait_for_endpoint_deletion(endpoint_name)

                if not success:
                    logger.warning("⚠️  Endpoint deletion may still be in progress")
                    disable_info["disable_status"] = "deletion_in_progress"
                else:
                    logger.info("✅ Endpoint successfully deleted")
                    disable_info["disable_status"] = "deleted"
                    disable_info["total_savings"] = "Full endpoint cost saved"
            else:
                logger.info("✅ Endpoint deletion initiated")
                disable_info["disable_status"] = "deletion_initiated"

            return disable_info

        except Exception as e:
            logger.error(f"❌ Failed to disable endpoint: {e}")
            raise

    def list_endpoints(self, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """List all SageMaker endpoints with optional status filter."""
        try:
            endpoints = []
            paginator = self.sagemaker.get_paginator('list_endpoints')

            for page in paginator.paginate():
                for endpoint in page.get('Endpoints', []):
                    if status_filter is None or endpoint.get('EndpointStatus') == status_filter:
                        endpoints.append(endpoint)

            return {"endpoints": endpoints, "count": len(endpoints)}

        except ClientError as e:
            logger.error(f"❌ Failed to list endpoints: {e}")
            raise


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(
        description="Safely disable a SageMaker endpoint by setting instance count to 0"
    )
    parser.add_argument(
        "--endpoint-name",
        required=True,
        help="Name of the SageMaker endpoint to disable"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for the update to complete"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all endpoints instead of disabling"
    )
    parser.add_argument(
        "--status-filter",
        help="Filter endpoints by status when using --list"
    )

    args = parser.parse_args()

    try:
        # Initialize disabler
        disabler = SageMakerEndpointDisabler(region=args.region)

        if args.list:
            # List endpoints
            logger.info("📋 Listing SageMaker endpoints...")
            endpoints_data = disabler.list_endpoints(args.status_filter)

            print(f"\nFound {endpoints_data['count']} endpoints:")
            print("-" * 80)

            for endpoint in endpoints_data['endpoints']:
                print(f"Name: {endpoint.get('EndpointName')}")
                print(f"Status: {endpoint.get('EndpointStatus')}")
                print(f"Created: {endpoint.get('CreationTime')}")
                print("-" * 40)

            return

        # Disable endpoint
        endpoint_name = args.endpoint_name

        # Get current endpoint info for confirmation
        try:
            endpoint_info = disabler.get_endpoint_info(endpoint_name)
            current_status = endpoint_info["EndpointStatus"]

            if current_status != "InService":
                logger.warning(f"⚠️  Endpoint is not InService (current: {current_status})")

                if not args.confirm:
                    response = input(f"Continue disabling endpoint '{endpoint_name}'? (y/N): ")
                    if response.lower() != 'y':
                        logger.info("❌ Operation cancelled")
                        return
            else:
                # Show current configuration
                config_info = disabler.get_endpoint_config(endpoint_info["EndpointConfigName"])
                total_instances = sum(
                    variant["InitialInstanceCount"] for variant in config_info["ProductionVariants"]
                )

                print(f"\nEndpoint Information:")
                print(f"  Name: {endpoint_name}")
                print(f"  Status: {current_status}")
                print(f"  Current Instances: {total_instances}")
                print(f"  Config: {endpoint_info['EndpointConfigName']}")

                if not args.confirm:
                    response = input(f"\nDisable endpoint '{endpoint_name}'? (y/N): ")
                    if response.lower() != 'y':
                        logger.info("❌ Operation cancelled")
                        return

        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationError':
                logger.error(f"❌ Endpoint '{endpoint_name}' not found")
                sys.exit(1)
            else:
                raise

        # Perform disable operation
        logger.info(f"🔄 Disabling endpoint: {endpoint_name}")
        disable_result = disabler.disable_endpoint(
            endpoint_name,
            wait_for_completion=not args.no_wait
        )

        print(f"\n✅ Endpoint disable operation completed!")
        print(f"   Status: {disable_result['disable_status']}")
        print(f"   Original Config: {disable_result['original_config_name']}")

        if 'total_instances' in disable_result:
            print(f"   Current Instances: {disable_result['total_instances']}")

        if args.no_wait:
            print(f"   Note: Update initiated in background. Check status later.")

        print(f"\n💾 Re-enable information saved to: {endpoint_name}_disable_info.json")
        print(f"   Use 'reenable_endpoint.py --endpoint-name {endpoint_name}' to re-enable")

    except KeyboardInterrupt:
        logger.info("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()