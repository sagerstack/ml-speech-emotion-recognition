#!/usr/bin/env python3
"""
SageMaker Endpoint Re-enabler

This script re-enables a previously disabled SageMaker endpoint by restoring
its original endpoint configuration with the original instance counts.

Usage:
    python reenable_endpoint.py --endpoint-name speech-emotion-1763484306
    python reenable_endpoint.py --endpoint-name speech-emotion-1763484306 --config-name original-config
"""

import argparse
import json
import logging
import sys
import time
import os
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SageMakerEndpointReenabler:
    """Utility class for re-enabling disabled SageMaker endpoints."""

    def __init__(self, region: str = "us-east-1"):
        """Initialize the re-enabler with AWS SageMaker client."""
        self.region = region
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        logger.info(f"✅ SageMaker client initialized for region: {region}")

    def load_disable_info(self, endpoint_name: str) -> Optional[Dict[str, Any]]:
        """Load disable information from saved file."""
        # Try multiple locations for the disable info file
        possible_paths = [
            f"{endpoint_name}_disable_info.json",  # Current directory
            f"../{endpoint_name}_disable_info.json",  # Parent directory
            f"../../{endpoint_name}_disable_info.json",  # Project root
            f"{os.path.dirname(__file__)}/../../{endpoint_name}_disable_info.json",  # From script location
        ]

        for disable_info_file in possible_paths:
            try:
                if os.path.exists(disable_info_file):
                    with open(disable_info_file, 'r') as f:
                        disable_info = json.load(f)
                    logger.info(f"✅ Loaded disable info from: {disable_info_file}")
                    return disable_info
            except Exception as e:
                logger.debug(f"Could not load from {disable_info_file}: {e}")
                continue

        logger.warning(f"⚠️  Disable info file not found in any location")
        return None

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
            # Re-raise the exception so the caller can handle it
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

    def verify_config_exists(self, config_name: str) -> bool:
        """Verify that the endpoint configuration exists."""
        try:
            self.sagemaker.describe_endpoint_config(EndpointConfigName=config_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException':
                return False
            else:
                raise

    def recreate_endpoint_from_info(self, endpoint_name: str, original_config_name: str, original_variants: list) -> str:
        """Recreate the endpoint from saved information."""
        try:
            # First, ensure the original configuration exists
            config_exists = True
            try:
                self.sagemaker.describe_endpoint_config(EndpointConfigName=original_config_name)
                logger.info(f"✅ Original config exists: {original_config_name}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ValidationException':
                    # Config doesn't exist, recreate it
                    logger.info(f"🔧 Recreating missing config: {original_config_name}")
                    self.sagemaker.create_endpoint_config(
                        EndpointConfigName=original_config_name,
                        ProductionVariants=original_variants
                    )
                    logger.info(f"✅ Recreated original config: {original_config_name}")
                else:
                    raise

            # Now recreate the endpoint
            logger.info(f"🔧 Recreating endpoint: {endpoint_name}")
            self.sagemaker.create_endpoint(
                EndpointName=endpoint_name,
                EndpointConfigName=original_config_name
            )

            logger.info(f"✅ Endpoint recreation initiated: {endpoint_name}")
            return original_config_name

        except Exception as e:
            logger.error(f"❌ Failed to recreate endpoint: {e}")
            raise

    def recreate_original_config(self, endpoint_name: str, original_variants: list) -> str:
        """Recreate the original endpoint configuration."""
        original_config_name = f"{endpoint_name}-original-recreated"

        try:
            # Recreate the original configuration
            self.sagemaker.create_endpoint_config(
                EndpointConfigName=original_config_name,
                ProductionVariants=original_variants
            )

            logger.info(f"✅ Recreated original config: {original_config_name}")
            return original_config_name

        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException' and 'already exists' in str(e):
                logger.warning(f"⚠️  Original config already exists: {original_config_name}")
                return original_config_name
            else:
                logger.error(f"❌ Failed to recreate original config: {e}")
                raise

    def update_endpoint_to_config(
        self,
        endpoint_name: str,
        config_name: str
    ) -> Dict[str, Any]:
        """Update endpoint to use specified configuration."""
        try:
            response = self.sagemaker.update_endpoint(
                EndpointName=endpoint_name,
                EndpointConfigName=config_name
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
        timeout: int = 900  # 15 minutes for re-enabling
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
                    failure_reason = response.get("FailureReason", "Unknown reason")
                    logger.error(f"❌ Endpoint failed with status: {current_status}")
                    logger.error(f"   Failure reason: {failure_reason}")
                    return False

                # Show progress for long-running operations
                if current_status == "Updating":
                    elapsed = time.time() - start_time
                    logger.info(f"   Update in progress... ({elapsed:.0f}s elapsed)")

                time.sleep(30)  # Wait 30 seconds before checking again

            except ClientError as e:
                logger.error(f"❌ Error checking endpoint status: {e}")
                return False

        logger.error(f"❌ Timeout waiting for endpoint to reach status: {target_status}")
        return False

    def cleanup_disabled_config(self, disabled_config_name: str) -> None:
        """Clean up the disabled configuration (optional)."""
        try:
            self.sagemaker.delete_endpoint_config(EndpointConfigName=disabled_config_name)
            logger.info(f"🧹 Cleaned up disabled config: {disabled_config_name}")
        except ClientError as e:
            logger.warning(f"⚠️  Failed to clean up disabled config: {e}")

    def reenable_endpoint(
        self,
        endpoint_name: str,
        config_name: Optional[str] = None,
        wait_for_completion: bool = True,
        cleanup_disabled: bool = False
    ) -> Dict[str, Any]:
        """
        Re-enable endpoint by restoring original configuration.

        Args:
            endpoint_name: Name of the endpoint to re-enable
            config_name: Specific config name to use (if not provided, will use saved info)
            wait_for_completion: Whether to wait for the update to complete
            cleanup_disabled: Whether to clean up the disabled config

        Returns:
            Dictionary with re-enable operation details
        """
        logger.info(f"🔄 Starting re-enable process for endpoint: {endpoint_name}")

        try:
            # Load disable information for context
            disable_info = self.load_disable_info(endpoint_name)
            if not disable_info:
                logger.error("❌ No saved disable info found - cannot recreate endpoint")
                raise ValueError("Must have saved disable info for endpoint recreation")

            # Step 1: Check if endpoint exists or needs to be recreated
            try:
                endpoint_info = self.get_endpoint_info(endpoint_name)
                current_config_name = endpoint_info["EndpointConfigName"]
                endpoint_exists = True
                logger.info("📋 Endpoint exists, will update configuration")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ValidationError':
                    endpoint_exists = False
                    current_config_name = None
                    logger.info("📋 Endpoint not found, will recreate from saved information")
                else:
                    raise

            # Determine target configuration
            target_config_name = config_name or disable_info["original_config_name"]
            logger.info(f"   Using target config: {target_config_name}")

            if endpoint_exists:
                # Case 1: Update existing endpoint
                logger.info("🔄 Updating existing endpoint to target configuration...")
                update_response = self.update_endpoint_to_config(endpoint_name, target_config_name)

                if wait_for_completion:
                    logger.info("⏳ Waiting for endpoint update to complete...")
                    success = self.wait_for_endpoint_update(endpoint_name, target_status="InService")

                    if not success:
                        raise Exception("Endpoint update failed or timed out")

                    final_info = self.get_endpoint_info(endpoint_name)
                    final_config = self.get_endpoint_config(final_info["EndpointConfigName"])
                    total_instances = sum(
                        variant["InitialInstanceCount"]
                        for variant in final_config["ProductionVariants"]
                    )

                    reenable_info = {
                        "endpoint_name": endpoint_name,
                        "status": "updated",
                        "instances": total_instances,
                        "config_name": target_config_name,
                        "previous_config": current_config_name,
                        "enable_time": time.time()
                    }
                else:
                    reenable_info = {
                        "endpoint_name": endpoint_name,
                        "status": "update_initiated",
                        "target_config": target_config_name,
                        "previous_config": current_config_name,
                        "message": "Update operation initiated, not waiting for completion"
                    }

            else:
                # Case 2: Recreate endpoint from saved information
                logger.info("🔧 Recreating endpoint from saved information...")

                # Recreate both config and endpoint
                recreated_config = self.recreate_endpoint_from_info(
                    endpoint_name,
                    target_config_name,
                    disable_info["original_variants"]
                )

                if wait_for_completion:
                    logger.info("⏳ Waiting for endpoint creation to complete...")
                    success = self.wait_for_endpoint_update(endpoint_name, target_status="InService", timeout=900)

                    if not success:
                        raise Exception("Endpoint creation failed or timed out")

                    final_info = self.get_endpoint_info(endpoint_name)
                    final_config = self.get_endpoint_config(final_info["EndpointConfigName"])
                    total_instances = sum(
                        variant["InitialInstanceCount"]
                        for variant in final_config["ProductionVariants"]
                    )

                    reenable_info = {
                        "endpoint_name": endpoint_name,
                        "status": "recreated",
                        "instances": total_instances,
                        "config_name": target_config_name,
                        "previous_status": "deleted",
                        "enable_time": time.time(),
                        "disable_timestamp": disable_info.get("disable_timestamp"),
                        "downtime_hours": (time.time() - disable_info.get("disable_timestamp", time.time())) / 3600
                    }
                else:
                    reenable_info = {
                        "endpoint_name": endpoint_name,
                        "status": "recreation_initiated",
                        "target_config": target_config_name,
                        "previous_status": "deleted",
                        "message": "Recreation operation initiated, not waiting for completion"
                    }

            return reenable_info

        except Exception as e:
            logger.error(f"❌ Failed to re-enable endpoint: {e}")
            raise

    def list_configs(self, endpoint_name: Optional[str] = None) -> Dict[str, Any]:
        """List endpoint configurations with optional endpoint filter."""
        try:
            configs = []
            paginator = self.sagemaker.get_paginator('list_endpoint_configs')

            for page in paginator.paginate():
                for config in page.get('EndpointConfigs', []):
                    if endpoint_name is None or endpoint_name in config.get('EndpointConfigName', ''):
                        configs.append(config)

            return {"configs": configs, "count": len(configs)}

        except ClientError as e:
            logger.error(f"❌ Failed to list endpoint configs: {e}")
            raise


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(
        description="Re-enable a previously disabled SageMaker endpoint"
    )
    parser.add_argument(
        "--endpoint-name",
        required=True,
        help="Name of the SageMaker endpoint to re-enable"
    )
    parser.add_argument(
        "--config-name",
        help="Specific endpoint config name to use (if not provided, uses saved info)"
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
        "--cleanup",
        action="store_true",
        help="Clean up disabled configuration after re-enabling"
    )
    parser.add_argument(
        "--list-configs",
        action="store_true",
        help="List available endpoint configurations"
    )

    args = parser.parse_args()

    try:
        # Initialize re-enabler
        reenabler = SageMakerEndpointReenabler(region=args.region)

        if args.list_configs:
            # List configurations
            logger.info("📋 Listing SageMaker endpoint configurations...")
            configs_data = reenabler.list_configs(args.endpoint_name)

            print(f"\nFound {configs_data['count']} endpoint configurations:")
            print("-" * 80)

            for config in configs_data['configs']:
                print(f"Name: {config.get('EndpointConfigName')}")
                print(f"ARN: {config.get('EndpointConfigArn')}")
                print(f"Created: {config.get('CreationTime')}")
                print("-" * 40)

            return

        # Re-enable endpoint
        endpoint_name = args.endpoint_name

        # Get current endpoint info or show deleted status
        try:
            endpoint_info = reenabler.get_endpoint_info(endpoint_name)
            current_status = endpoint_info["EndpointStatus"]
            current_config = endpoint_info["EndpointConfigName"]
            endpoint_exists = True

            print(f"\nEndpoint Information:")
            print(f"  Name: {endpoint_name}")
            print(f"  Status: {current_status}")
            print(f"  Current Config: {current_config}")

        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationError':
                endpoint_exists = False
                current_status = "Not Found"
                current_config = None

                print(f"\nEndpoint Information:")
                print(f"  Name: {endpoint_name}")
                print(f"  Status: {current_status} (will be recreated)")
                print(f"  Current Config: None")
            else:
                raise

        # Load disable info if available
        disable_info = reenabler.load_disable_info(endpoint_name)
        if disable_info:
            print(f"  Saved Original Config: {disable_info['original_config_name']}")
            print(f"  Disabled At: {disable_info['disable_timestamp']}")
            if not endpoint_exists:
                downtime_hours = (time.time() - disable_info.get('disable_timestamp', time.time())) / 3600
                print(f"  Downtime: {downtime_hours:.1f} hours")

        if args.config_name:
            print(f"  Target Config: {args.config_name}")
        elif disable_info:
            print(f"  Target Config: {disable_info['original_config_name']} (from saved info)")
        else:
            print(f"  Target Config: [Need to specify --config-name]")

        if not args.confirm:
            if endpoint_exists:
                response = input(f"\nRe-enable endpoint '{endpoint_name}'? (y/N): ")
            else:
                response = input(f"\nRecreate endpoint '{endpoint_name}' from saved configuration? (y/N): ")
            if response.lower() != 'y':
                logger.info("❌ Operation cancelled")
                return

        # Perform re-enable operation
        logger.info(f"🔄 Re-enabling endpoint: {endpoint_name}")
        reenable_result = reenabler.reenable_endpoint(
            endpoint_name,
            config_name=args.config_name,
            wait_for_completion=not args.no_wait,
            cleanup_disabled=args.cleanup
        )

        print(f"\n✅ Endpoint re-enable operation completed!")
        print(f"   Status: {reenable_result['reenable_status']}")
        print(f"   Target Config: {reenable_result['target_config_name']}")
        print(f"   Previous Config: {reenable_result['previous_config_name']}")

        if 'total_instances' in reenable_result:
            print(f"   Current Instances: {reenable_result['total_instances']}")

        if args.no_wait:
            print(f"   Note: Update initiated in background. Check status later.")

        if args.cleanup:
            print(f"   Note: Disabled configuration cleaned up")

    except KeyboardInterrupt:
        logger.info("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()