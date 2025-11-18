#!/usr/bin/env python3
"""
SageMaker Resource Cleanup Script

This script cleans up SageMaker resources including endpoints, endpoint configs,
models, and associated resources to prevent unnecessary charges.
"""

import os
import sys
import json
import time
import logging
import boto3
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SageMakerCleanup:
    """Handles cleanup of SageMaker resources."""

    def __init__(self, config_path: str = "../model-deployment/config.yaml"):
        """Initialize the cleanup manager."""
        self.config_path = config_path
        self.config = self._load_config()
        self.session = boto3.Session(region_name=self.config['aws']['region'])
        self.sagemaker = self.session.client('sagemaker')
        self.cloudwatch = self.session.client('cloudwatch')
        self.s3 = self.session.client('s3')

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration."""
        try:
            config_file = Path(__file__).parent / self.config_path
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def list_all_resources(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all SageMaker resources."""
        try:
            logger.info("Discovering SageMaker resources...")

            resources = {
                "endpoints": [],
                "endpoint_configs": [],
                "models": [],
                "notebook_instances": [],
                "training_jobs": [],
                "transform_jobs": []
            }

            # List endpoints
            try:
                response = self.sagemaker.list_endpoints(
                    SortBy='CreationTime',
                    SortOrder='Descending',
                    MaxResults=100
                )
                resources["endpoints"] = response.get('Endpoints', [])
                logger.info(f"Found {len(resources['endpoints'])} endpoints")
            except Exception as e:
                logger.warning(f"Could not list endpoints: {e}")

            # List endpoint configs
            try:
                response = self.sagemaker.list_endpoint_configs(
                    SortBy='CreationTime',
                    SortOrder='Descending',
                    MaxResults=100
                )
                resources["endpoint_configs"] = response.get('EndpointConfigs', [])
                logger.info(f"Found {len(resources['endpoint_configs'])} endpoint configs")
            except Exception as e:
                logger.warning(f"Could not list endpoint configs: {e}")

            # List models
            try:
                response = self.sagemaker.list_models(
                    SortBy='CreationTime',
                    SortOrder='Descending',
                    MaxResults=100
                )
                resources["models"] = response.get('Models', [])
                logger.info(f"Found {len(resources['models'])} models")
            except Exception as e:
                logger.warning(f"Could not list models: {e}")

            # List notebook instances
            try:
                response = self.sagemaker.list_notebook_instances(
                    SortBy='CreationTime',
                    SortOrder='Descending',
                    MaxResults=100
                )
                resources["notebook_instances"] = response.get('NotebookInstances', [])
                logger.info(f"Found {len(resources['notebook_instances'])} notebook instances")
            except Exception as e:
                logger.warning(f"Could not list notebook instances: {e}")

            # List training jobs
            try:
                response = self.sagemaker.list_training_jobs(
                    SortBy='CreationTime',
                    SortOrder='Descending',
                    MaxResults=100
                )
                resources["training_jobs"] = response.get('TrainingJobSummaries', [])
                logger.info(f"Found {len(resources['training_jobs'])} training jobs")
            except Exception as e:
                logger.warning(f"Could not list training jobs: {e}")

            # List transform jobs
            try:
                response = self.sagemaker.list_transform_jobs(
                    SortBy='CreationTime',
                    SortOrder='Descending',
                    MaxResults=100
                )
                resources["transform_jobs"] = response.get('TransformJobSummaries', [])
                logger.info(f"Found {len(resources['transform_jobs'])} transform jobs")
            except Exception as e:
                logger.warning(f"Could not list transform jobs: {e}")

            return resources

        except Exception as e:
            logger.error(f"Failed to list resources: {e}")
            raise

    def get_endpoint_age(self, endpoint_name: str) -> int:
        """Get endpoint age in days."""
        try:
            response = self.sagemaker.describe_endpoint(EndpointName=endpoint_name)
            creation_time = response['CreationTime']
            age = datetime.now(creation_time.tzinfo) - creation_time
            return age.days
        except Exception as e:
            logger.warning(f"Could not get age for endpoint {endpoint_name}: {e}")
            return 0

    def get_endpoint_usage(self, endpoint_name: str, days: int = 7) -> int:
        """Get endpoint usage (invocations) over specified days."""
        try:
            cloudwatch = self.session.client('cloudwatch')
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/SageMaker',
                MetricName='Invocations',
                Dimensions=[
                    {'Name': 'EndpointName', 'Value': endpoint_name}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,  # 1 day
                Statistics=['Sum']
            )

            total_invocations = sum(dp['Sum'] for dp in response['Datapoints'])
            return int(total_invocations)

        except Exception as e:
            logger.warning(f"Could not get usage for endpoint {endpoint_name}: {e}")
            return 0

    def identify_unused_resources(self, days_threshold: int = 30, usage_threshold: int = 10) -> Dict[str, List[str]]:
        """Identify resources that can be safely cleaned up."""
        try:
            logger.info("Identifying unused resources...")

            resources = self.list_all_resources()
            unused_resources = {
                "endpoints": [],
                "endpoint_configs": [],
                "models": []
            }

            # Check endpoints
            for endpoint in resources["endpoints"]:
                endpoint_name = endpoint["EndpointName"]
                endpoint_status = endpoint["EndpointStatus"]

                if endpoint_status == "InService":
                    age = self.get_endpoint_age(endpoint_name)
                    usage = self.get_endpoint_usage(endpoint_name)

                    # Mark as unused if old and low usage
                    if age > days_threshold and usage < usage_threshold:
                        unused_resources["endpoints"].append(endpoint_name)
                        logger.info(f"  Endpoint {endpoint_name}: age={age}d, usage={usage}")

                elif endpoint_status in ["Failed", "Deleted"]:
                    # Always clean up failed or deleted endpoints
                    unused_resources["endpoints"].append(endpoint_name)
                    logger.info(f"  Endpoint {endpoint_name}: status={endpoint_status}")

            # Check endpoint configs
            for config in resources["endpoint_configs"]:
                config_name = config["EndpointConfigName"]
                # Note: We could check if this config is still in use, but for simplicity,
                # we'll include all configs that are older than the threshold
                creation_time = config["CreationTime"]
                age = datetime.now(creation_time.tzinfo) - creation_time
                if age.days > days_threshold:
                    unused_resources["endpoint_configs"].append(config_name)

            # Check models
            for model in resources["models"]:
                model_name = model["ModelName"]
                creation_time = model["CreationTime"]
                age = datetime.now(creation_time.tzinfo) - creation_time
                if age.days > days_threshold:
                    unused_resources["models"].append(model_name)

            logger.info(f"Identified {len(unused_resources['endpoints'])} endpoints, "
                       f"{len(unused_resources['endpoint_configs'])} configs, "
                       f"{len(unused_resources['models'])} models for cleanup")

            return unused_resources

        except Exception as e:
            logger.error(f"Failed to identify unused resources: {e}")
            return {"endpoints": [], "endpoint_configs": [], "models": []}

    def delete_endpoint(self, endpoint_name: str, force: bool = False) -> bool:
        """Delete a SageMaker endpoint."""
        try:
            logger.info(f"Deleting endpoint: {endpoint_name}")

            if not force:
                # Get endpoint info for confirmation
                try:
                    response = self.sagemaker.describe_endpoint(EndpointName=endpoint_name)
                    logger.info(f"  Status: {response['EndpointStatus']}")
                    logger.info(f"  Created: {response['CreationTime']}")
                    logger.info(f"  Last Modified: {response['LastModifiedTime']}")
                except Exception as e:
                    logger.warning(f"Could not get endpoint info: {e}")

            # Delete endpoint
            self.sagemaker.delete_endpoint(EndpointName=endpoint_name)
            logger.info(f"✅ Endpoint {endpoint_name} deleted")
            return True

        except Exception as e:
            logger.error(f"Failed to delete endpoint {endpoint_name}: {e}")
            return False

    def delete_endpoint_config(self, config_name: str, force: bool = False) -> bool:
        """Delete an endpoint configuration."""
        try:
            logger.info(f"Deleting endpoint config: {config_name}")

            if not force:
                # Get config info
                try:
                    response = self.sagemaker.describe_endpoint_config(EndpointConfigName=config_name)
                    logger.info(f"  Production Variants: {len(response.get('ProductionVariants', []))}")
                except Exception as e:
                    logger.warning(f"Could not get endpoint config info: {e}")

            # Delete endpoint config
            self.sagemaker.delete_endpoint_config(EndpointConfigName=config_name)
            logger.info(f"✅ Endpoint config {config_name} deleted")
            return True

        except Exception as e:
            logger.error(f"Failed to delete endpoint config {config_name}: {e}")
            return False

    def delete_model(self, model_name: str, force: bool = False) -> bool:
        """Delete a SageMaker model."""
        try:
            logger.info(f"Deleting model: {model_name}")

            if not force:
                # Get model info
                try:
                    response = self.sagemaker.describe_model(ModelName=model_name)
                    logger.info(f"  Primary Container: {response.get('PrimaryContainer', {}).get('Image', 'Unknown')}")
                except Exception as e:
                    logger.warning(f"Could not get model info: {e}")

            # Delete model
            self.sagemaker.delete_model(ModelName=model_name)
            logger.info(f"✅ Model {model_name} deleted")
            return True

        except Exception as e:
            logger.error(f"Failed to delete model {model_name}: {e}")
            return False

    def cleanup_endpoint_chain(self, endpoint_name: str, delete_config: bool = True, delete_model: bool = True) -> bool:
        """Clean up an endpoint and its associated config and model."""
        try:
            logger.info(f"Cleaning up endpoint chain: {endpoint_name}")
            success = True

            # Get endpoint config and model names before deleting endpoint
            try:
                endpoint_response = self.sagemaker.describe_endpoint(EndpointName=endpoint_name)
                config_name = endpoint_response['EndpointConfigName']

                config_response = self.sagemaker.describe_endpoint_config(EndpointConfigName=config_name)
                production_variants = config_response.get('ProductionVariants', [])
                model_names = [variant['ModelName'] for variant in production_variants]
            except Exception as e:
                logger.warning(f"Could not get endpoint details: {e}")
                config_name = None
                model_names = []

            # Delete endpoint
            if not self.delete_endpoint(endpoint_name):
                success = False

            # Delete endpoint config
            if delete_config and config_name:
                if not self.delete_endpoint_config(config_name):
                    success = False

            # Delete models
            if delete_model:
                for model_name in model_names:
                    if not self.delete_model(model_name):
                        success = False

            if success:
                logger.info(f"✅ Successfully cleaned up endpoint chain: {endpoint_name}")
            else:
                logger.error(f"❌ Partial cleanup for endpoint chain: {endpoint_name}")

            return success

        except Exception as e:
            logger.error(f"Failed to cleanup endpoint chain {endpoint_name}: {e}")
            return False

    def cleanup_s3_artifacts(self, bucket_prefix: str = None, days_threshold: int = 30) -> bool:
        """Clean up S3 artifacts older than threshold."""
        try:
            if not bucket_prefix:
                bucket_prefix = self.config.get('aws', {}).get('bucket_prefix', 'sagemaker')

            logger.info(f"Cleaning up S3 artifacts with prefix: {bucket_prefix}")

            # Get default bucket
            sagemaker_session = self.session.client('sagemaker')
            buckets = []

            # Try to find S3 buckets with the prefix
            all_buckets = self.s3.list_buckets()
            for bucket in all_buckets['Buckets']:
                bucket_name = bucket['Name']
                if bucket_prefix in bucket_name:
                    buckets.append(bucket_name)

            if not buckets:
                logger.warning(f"No buckets found with prefix: {bucket_prefix}")
                return True

            total_deleted = 0
            cutoff_date = datetime.now() - timedelta(days=days_threshold)

            for bucket_name in buckets:
                try:
                    logger.info(f"Processing bucket: {bucket_name}")

                    # List objects with prefix
                    paginator = self.s3.get_paginator('list_objects_v2')
                    pages = paginator.paginate(
                        Bucket=bucket_name,
                        Prefix=bucket_prefix
                    )

                    for page in pages:
                        if 'Contents' not in page:
                            continue

                        for obj in page['Contents']:
                            key = obj['Key']
                            last_modified = obj['LastModified'].replace(tzinfo=None)

                            if last_modified < cutoff_date:
                                try:
                                    self.s3.delete_object(Bucket=bucket_name, Key=key)
                                    total_deleted += 1
                                    logger.debug(f"Deleted: s3://{bucket_name}/{key}")
                                except Exception as e:
                                    logger.warning(f"Failed to delete s3://{bucket_name}/{key}: {e}")

                except Exception as e:
                    logger.error(f"Failed to process bucket {bucket_name}: {e}")

            logger.info(f"✅ Deleted {total_deleted} S3 objects")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup S3 artifacts: {e}")
            return False

    def cleanup_cloudwatch_alarms(self, endpoint_name: str = None) -> bool:
        """Clean up CloudWatch alarms."""
        try:
            logger.info("Cleaning up CloudWatch alarms...")

            alarms_to_delete = []

            if endpoint_name:
                # Get alarms for specific endpoint
                response = self.cloudwatch.describe_alarms(
                    AlarmNames=[f"{endpoint_name}-HighErrorRate"],
                    AlarmNames=[f"{endpoint_name}-HighLatency"],
                    AlarmNames=[f"{endpoint_name}-NoInvocations"],
                    AlarmNames=[f"{endpoint_name}-HighCost"]
                )
                alarms_to_delete = [alarm['AlarmName'] for alarm in response['MetricAlarms']]
            else:
                # Get all SageMaker alarms
                response = self.cloudwatch.describe_alarms(
                    AlarmNamePrefix='sagemaker-'
                )
                alarms_to_delete = [alarm['AlarmName'] for alarm in response['MetricAlarms']]

            # Delete alarms
            deleted_count = 0
            for alarm_name in alarms_to_delete:
                try:
                    self.cloudwatch.delete_alarms(AlarmNames=[alarm_name])
                    deleted_count += 1
                    logger.debug(f"Deleted alarm: {alarm_name}")
                except Exception as e:
                    logger.warning(f"Failed to delete alarm {alarm_name}: {e}")

            logger.info(f"✅ Deleted {deleted_count} CloudWatch alarms")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup CloudWatch alarms: {e}")
            return False

    def dry_run_cleanup(self, days_threshold: int = 30, usage_threshold: int = 10) -> Dict[str, Any]:
        """Perform a dry run to identify what would be cleaned up."""
        try:
            logger.info("🔍 Performing dry run cleanup...")

            unused_resources = self.identify_unused_resources(days_threshold, usage_threshold)

            # Estimate cost savings
            estimated_monthly_savings = 0.0
            memory_size_gb = self.config['serverless']['memory_size_in_mb'] / 1024

            for endpoint_name in unused_resources["endpoints"]:
                # Rough estimate of monthly cost per endpoint
                # This is a simplified calculation
                daily_cost = memory_size_gb * 0.000006208 * 24 * 3600  # Memory cost per day
                monthly_cost = daily_cost * 30
                estimated_monthly_savings += monthly_cost

            dry_run_report = {
                "dry_run": True,
                "timestamp": datetime.utcnow().isoformat(),
                "criteria": {
                    "days_threshold": days_threshold,
                    "usage_threshold": usage_threshold
                },
                "resources_to_delete": unused_resources,
                "estimated_monthly_savings": estimated_monthly_savings,
                "summary": {
                    "endpoints": len(unused_resources["endpoints"]),
                    "endpoint_configs": len(unused_resources["endpoint_configs"]),
                    "models": len(unused_resources["models"])
                }
            }

            logger.info("📋 Dry Run Summary:")
            logger.info(f"  Endpoints to delete: {len(unused_resources['endpoints'])}")
            logger.info(f"  Endpoint configs to delete: {len(unused_resources['endpoint_configs'])}")
            logger.info(f"  Models to delete: {len(unused_resources['models'])}")
            logger.info(f"  Estimated monthly savings: ${estimated_monthly_savings:.2f}")

            return dry_run_report

        except Exception as e:
            logger.error(f"Dry run failed: {e}")
            return {}

    def full_cleanup(self, days_threshold: int = 30, usage_threshold: int = 10,
                    dry_run: bool = True, force: bool = False) -> Dict[str, Any]:
        """Perform full cleanup of unused resources."""
        try:
            logger.info(f"🧹 Starting full cleanup...")

            if dry_run:
                return self.dry_run_cleanup(days_threshold, usage_threshold)

            # Get unused resources
            unused_resources = self.identify_unused_resources(days_threshold, usage_threshold)

            cleanup_results = {
                "cleanup_timestamp": datetime.utcnow().isoformat(),
                "criteria": {
                    "days_threshold": days_threshold,
                    "usage_threshold": usage_threshold
                },
                "results": {
                    "endpoints": {"success": [], "failed": []},
                    "endpoint_configs": {"success": [], "failed": []},
                    "models": {"success": [], "failed": []},
                    "s3_artifacts": False,
                    "cloudwatch_alarms": False
                }
            }

            # Clean up endpoints
            for endpoint_name in unused_resources["endpoints"]:
                if self.cleanup_endpoint_chain(endpoint_name):
                    cleanup_results["results"]["endpoints"]["success"].append(endpoint_name)
                else:
                    cleanup_results["results"]["endpoints"]["failed"].append(endpoint_name)

            # Clean up orphaned endpoint configs
            for config_name in unused_resources["endpoint_configs"]:
                if self.delete_endpoint_config(config_name, force):
                    cleanup_results["results"]["endpoint_configs"]["success"].append(config_name)
                else:
                    cleanup_results["results"]["endpoint_configs"]["failed"].append(config_name)

            # Clean up orphaned models
            for model_name in unused_resources["models"]:
                if self.delete_model(model_name, force):
                    cleanup_results["results"]["models"]["success"].append(model_name)
                else:
                    cleanup_results["results"]["models"]["failed"].append(model_name)

            # Clean up S3 artifacts
            if self.cleanup_s3_artifacts():
                cleanup_results["results"]["s3_artifacts"] = True

            # Clean up CloudWatch alarms
            if self.cleanup_cloudwatch_alarms():
                cleanup_results["results"]["cloudwatch_alarms"] = True

            # Summary
            total_success = (
                len(cleanup_results["results"]["endpoints"]["success"]) +
                len(cleanup_results["results"]["endpoint_configs"]["success"]) +
                len(cleanup_results["results"]["models"]["success"])
            )
            total_failed = (
                len(cleanup_results["results"]["endpoints"]["failed"]) +
                len(cleanup_results["results"]["endpoint_configs"]["failed"]) +
                len(cleanup_results["results"]["models"]["failed"])
            )

            logger.info(f"✅ Cleanup completed:")
            logger.info(f"  Successful: {total_success}")
            logger.info(f"  Failed: {total_failed}")

            cleanup_results["summary"] = {
                "total_success": total_success,
                "total_failed": total_failed
            }

            return cleanup_results

        except Exception as e:
            logger.error(f"Full cleanup failed: {e}")
            raise


def main():
    """Main cleanup function."""
    parser = argparse.ArgumentParser(description="Clean up SageMaker resources")
    parser.add_argument("--config", type=str, default="../model-deployment/config.yaml", help="Configuration file path")
    parser.add_argument("--list", action="store_true", help="List all resources")
    parser.add_argument("--identify", action="store_true", help="Identify unused resources")
    parser.add_argument("--endpoint", type=str, help="Delete specific endpoint")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--cleanup", action="store_true", help="Perform full cleanup")
    parser.add_argument("--force", action="store_true", help="Force deletion without prompts")
    parser.add_argument("--days", type=int, default=30, help="Age threshold in days")
    parser.add_argument("--usage", type=int, default=10, help="Usage threshold (invocations)")
    parser.add_argument("--s3", action="store_true", help="Clean up S3 artifacts")
    parser.add_argument("--alarms", action="store_true", help="Clean up CloudWatch alarms")

    args = parser.parse_args()

    try:
        cleanup = SageMakerCleanup(args.config)

        if args.list:
            resources = cleanup.list_all_resources()
            print("SageMaker Resources:")
            print(json.dumps(resources, indent=2, default=str))

        elif args.identify:
            unused = cleanup.identify_unused_resources(args.days, args.usage)
            print("Unused Resources:")
            print(json.dumps(unused, indent=2))

        elif args.endpoint:
            success = cleanup.cleanup_endpoint_chain(args.endpoint, force=args.force)
            if success:
                print(f"✅ Endpoint {args.endpoint} cleaned up successfully")
            else:
                print(f"❌ Failed to clean up endpoint {args.endpoint}")

        elif args.s3:
            success = cleanup.cleanup_s3_artifacts(days_threshold=args.days)
            if success:
                print("✅ S3 artifacts cleaned up successfully")
            else:
                print("❌ Failed to clean up S3 artifacts")

        elif args.alarms:
            success = cleanup.cleanup_cloudwatch_alarms()
            if success:
                print("✅ CloudWatch alarms cleaned up successfully")
            else:
                print("❌ Failed to clean up CloudWatch alarms")

        elif args.dry_run or args.cleanup:
            results = cleanup.full_cleanup(
                days_threshold=args.days,
                usage_threshold=args.usage,
                dry_run=args.dry_run,
                force=args.force
            )
            print("Cleanup Results:")
            print(json.dumps(results, indent=2, default=str))

        else:
            parser.print_help()

    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()