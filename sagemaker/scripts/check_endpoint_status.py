#!/usr/bin/env python3
"""
SageMaker Endpoint Status Checker

This script checks the status and health of SageMaker endpoints,
providing detailed information about instance counts, costs, and usage.

Usage:
    python check_endpoint_status.py --endpoint-name speech-emotion-1763484306
    python check_endpoint_status.py --list-all
    python check_endpoint_status.py --status-filter InService
"""

import argparse
import json
import logging
import sys
import time
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SageMakerEndpointStatusChecker:
    """Utility class for checking SageMaker endpoint status and health."""

    def __init__(self, region: str = "us-east-1"):
        """Initialize the status checker with AWS clients."""
        self.region = region
        self.session = boto3.Session(region_name=region)
        self.sagemaker = self.session.client('sagemaker')
        self.cloudwatch = self.session.client('cloudwatch')
        logger.info(f"✅ SageMaker clients initialized for region: {region}")

    def get_endpoint_info(self, endpoint_name: str) -> Dict[str, Any]:
        """Get detailed endpoint information."""
        try:
            response = self.sagemaker.describe_endpoint(EndpointName=endpoint_name)

            # Get endpoint config details
            config_response = self.sagemaker.describe_endpoint_config(
                EndpointConfigName=response['EndpointConfigName']
            )

            # Calculate instance information
            production_variants = config_response.get('ProductionVariants', [])
            total_instances = sum(variant.get('InitialInstanceCount', 0) for variant in production_variants)

            return {
                "endpoint_name": response.get("EndpointName"),
                "endpoint_arn": response.get("EndpointArn"),
                "endpoint_status": response.get("EndpointStatus"),
                "endpoint_config_name": response.get("EndpointConfigName"),
                "creation_time": response.get("CreationTime"),
                "last_modified_time": response.get("LastModifiedTime"),
                "failure_reason": response.get("FailureReason"),
                "production_variants": production_variants,
                "total_instances": total_instances,
                "instance_types": list(set(variant.get('InstanceType', 'unknown') for variant in production_variants)),
                "model_names": list(set(variant.get('ModelName', 'unknown') for variant in production_variants))
            }

        except ClientError as e:
            logger.error(f"❌ Failed to get endpoint info: {e}")
            raise

    def get_endpoint_metrics(self, endpoint_name: str, days: int = 7) -> Dict[str, Any]:
        """Get endpoint usage metrics from CloudWatch."""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            metrics = {}

            # Invocations
            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/SageMaker',
                    MetricName='Invocations',
                    Dimensions=[{'Name': 'EndpointName', 'Value': endpoint_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,  # 1 day
                    Statistics=['Sum']
                )
                invocations = sum(dp['Sum'] for dp in response['Datapoints'])
                metrics['total_invocations'] = int(invocations)
                metrics['daily_invocations'] = invocations / days if days > 0 else 0
            except Exception as e:
                logger.warning(f"Could not get invocations metric: {e}")
                metrics['total_invocations'] = 0
                metrics['daily_invocations'] = 0

            # Latency (4XX errors often indicate endpoint issues)
            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/SageMaker',
                    MetricName='ModelLatency',
                    Dimensions=[{'Name': 'EndpointName', 'Value': endpoint_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,
                    Statistics=['Average']
                )
                latencies = [dp['Average'] for dp in response['Datapoints']]
                metrics['average_latency_ms'] = sum(latencies) / len(latencies) if latencies else 0
            except Exception as e:
                logger.warning(f"Could not get latency metric: {e}")
                metrics['average_latency_ms'] = 0

            # 4XX Errors
            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/SageMaker',
                    MetricName='Invocation4XXErrors',
                    Dimensions=[{'Name': 'EndpointName', 'Value': endpoint_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,
                    Statistics=['Sum']
                )
                errors = sum(dp['Sum'] for dp in response['Datapoints'])
                metrics['total_4xx_errors'] = int(errors)
                metrics['error_rate'] = (errors / metrics['total_invocations']) if metrics['total_invocations'] > 0 else 0
            except Exception as e:
                logger.warning(f"Could not get error metric: {e}")
                metrics['total_4xx_errors'] = 0
                metrics['error_rate'] = 0

            return metrics

        except Exception as e:
            logger.error(f"Failed to get endpoint metrics: {e}")
            return {}

    def estimate_cost(self, endpoint_info: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate monthly cost for the endpoint."""
        try:
            instance_costs = {
                'ml.t2.medium': 0.064,    # per hour
                'ml.t2.large': 0.256,     # per hour
                'ml.t2.xlarge': 0.512,    # per hour
                'ml.t2.2xlarge': 1.024,   # per hour
                'ml.m5.large': 0.192,     # per hour
                'ml.m5.xlarge': 0.384,    # per hour
                'ml.m5.2xlarge': 0.768,   # per hour
                'ml.m5.4xlarge': 1.536,   # per hour
                'ml.c5.large': 0.170,     # per hour
                'ml.c5.xlarge': 0.340,    # per hour
                'ml.c5.2xlarge': 0.680,   # per hour
                'ml.c5.4xlarge': 1.360,   # per hour
                'ml.p3.2xlarge': 3.825,   # per hour
                'ml.p3.8xlarge': 15.300,  # per hour
                # Add more instance types as needed
            }

            production_variants = endpoint_info.get('production_variants', [])
            hourly_cost = 0.0
            instance_details = []

            for variant in production_variants:
                instance_type = variant.get('InstanceType', 'unknown')
                instance_count = variant.get('InitialInstanceCount', 0)

                if instance_type in instance_costs:
                    cost_per_hour = instance_costs[instance_type] * instance_count
                    hourly_cost += cost_per_hour
                    instance_details.append({
                        'instance_type': instance_type,
                        'count': instance_count,
                        'hourly_cost': cost_per_hour
                    })
                else:
                    # Default cost estimate for unknown instance types
                    estimated_cost = 0.5 * instance_count  # Conservative estimate
                    hourly_cost += estimated_cost
                    instance_details.append({
                        'instance_type': instance_type,
                        'count': instance_count,
                        'hourly_cost': estimated_cost,
                        'estimated': True
                    })

            daily_cost = hourly_cost * 24
            monthly_cost = daily_cost * 30

            return {
                'hourly_cost': hourly_cost,
                'daily_cost': daily_cost,
                'monthly_cost': monthly_cost,
                'instance_details': instance_details
            }

        except Exception as e:
            logger.error(f"Failed to estimate cost: {e}")
            return {
                'hourly_cost': 0.0,
                'daily_cost': 0.0,
                'monthly_cost': 0.0,
                'instance_details': []
            }

    def check_endpoint_health(self, endpoint_name: str) -> Dict[str, Any]:
        """Perform a comprehensive health check of the endpoint."""
        try:
            # Get basic endpoint info
            endpoint_info = self.get_endpoint_info(endpoint_name)
            status = endpoint_info['endpoint_status']

            health_status = {
                'endpoint_name': endpoint_name,
                'status': status,
                'timestamp': datetime.utcnow().isoformat(),
                'checks': {}
            }

            # Status check
            if status == 'InService':
                health_status['checks']['status'] = 'healthy'
                health_status['checks']['status_message'] = 'Endpoint is in service'
            elif status == 'Creating':
                health_status['checks']['status'] = 'initializing'
                health_status['checks']['status_message'] = 'Endpoint is being created'
            elif status == 'Updating':
                health_status['checks']['status'] = 'updating'
                health_status['checks']['status_message'] = 'Endpoint is being updated'
            elif status == 'Failed':
                health_status['checks']['status'] = 'unhealthy'
                health_status['checks']['status_message'] = f"Endpoint failed: {endpoint_info.get('failure_reason', 'Unknown')}"
            else:
                health_status['checks']['status'] = 'unknown'
                health_status['checks']['status_message'] = f"Unknown status: {status}"

            # Instance check
            total_instances = endpoint_info.get('total_instances', 0)
            if total_instances > 0:
                health_status['checks']['instances'] = 'active'
                health_status['checks']['instances_message'] = f'Running {total_instances} instances'
            elif total_instances == 0 and status == 'InService':
                health_status['checks']['instances'] = 'disabled'
                health_status['checks']['instances_message'] = 'Endpoint is disabled (0 instances)'
            else:
                health_status['checks']['instances'] = 'none'
                health_status['checks']['instances_message'] = 'No active instances'

            # Usage metrics
            metrics = self.get_endpoint_metrics(endpoint_name, days=7)
            health_status['metrics'] = metrics

            # Usage check
            if metrics.get('total_invocations', 0) > 0:
                health_status['checks']['usage'] = 'active'
                health_status['checks']['usage_message'] = f'Average {metrics.get("daily_invocations", 0):.1f} invocations/day'
            else:
                health_status['checks']['usage'] = 'inactive'
                health_status['checks']['usage_message'] = 'No invocations in the last 7 days'

            # Error check
            error_rate = metrics.get('error_rate', 0)
            if error_rate == 0:
                health_status['checks']['errors'] = 'none'
                health_status['checks']['errors_message'] = 'No 4XX errors detected'
            elif error_rate < 0.05:  # Less than 5% error rate
                health_status['checks']['errors'] = 'low'
                health_status['checks']['errors_message'] = f'Low error rate: {error_rate:.2%}'
            else:
                health_status['checks']['errors'] = 'high'
                health_status['checks']['errors_message'] = f'High error rate: {error_rate:.2%}'

            # Cost estimation
            cost_info = self.estimate_cost(endpoint_info)
            health_status['cost'] = cost_info

            # Overall health assessment
            overall_health = 'healthy'
            issues = []

            if health_status['checks']['status'] not in ['healthy', 'initializing']:
                overall_health = 'unhealthy'
                issues.append(f"Status: {health_status['checks']['status_message']}")

            if health_status['checks']['errors'] == 'high':
                overall_health = 'degraded'
                issues.append(f"High error rate: {health_status['checks']['errors_message']}")

            if health_status['checks']['usage'] == 'inactive' and total_instances > 0:
                overall_health = 'warning'
                issues.append(f"No usage but {total_instances} instances running")

            health_status['overall_health'] = overall_health
            health_status['issues'] = issues

            return health_status

        except Exception as e:
            logger.error(f"Failed to check endpoint health: {e}")
            return {
                'endpoint_name': endpoint_name,
                'status': 'error',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }

    def list_endpoints(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all SageMaker endpoints with optional status filter."""
        try:
            endpoints = []
            paginator = self.sagemaker.get_paginator('list_endpoints')

            for page in paginator.paginate():
                for endpoint in page.get('Endpoints', []):
                    if status_filter is None or endpoint.get('EndpointStatus') == status_filter:
                        endpoints.append(endpoint)

            return endpoints

        except Exception as e:
            logger.error(f"Failed to list endpoints: {e}")
            return []

    def get_status_summary(self, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """Get a summary of all endpoints and their status."""
        try:
            endpoints = self.list_endpoints(status_filter)

            summary = {
                'timestamp': datetime.utcnow().isoformat(),
                'region': self.region,
                'total_endpoints': len(endpoints),
                'status_breakdown': {},
                'endpoints': []
            }

            # Count by status
            for endpoint in endpoints:
                status = endpoint.get('EndpointStatus', 'Unknown')
                summary['status_breakdown'][status] = summary['status_breakdown'].get(status, 0) + 1

                # Add basic endpoint info
                summary['endpoints'].append({
                    'name': endpoint.get('EndpointName'),
                    'status': status,
                    'created': endpoint.get('CreationTime').isoformat() if endpoint.get('CreationTime') else None
                })

            return summary

        except Exception as e:
            logger.error(f"Failed to get status summary: {e}")
            return {'error': str(e)}


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(
        description="Check SageMaker endpoint status and health"
    )
    parser.add_argument(
        "--endpoint-name",
        help="Specific endpoint name to check"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--list-all",
        action="store_true",
        help="List all endpoints"
    )
    parser.add_argument(
        "--status-filter",
        help="Filter endpoints by status (e.g., InService, Failed)"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show status summary of all endpoints"
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Perform comprehensive health check"
    )
    parser.add_argument(
        "--metrics-days",
        type=int,
        default=7,
        help="Number of days to analyze metrics (default: 7)"
    )
    parser.add_argument(
        "--cost-estimate",
        action="store_true",
        help="Show cost estimation"
    )
    parser.add_argument(
        "--format",
        choices=['table', 'json'],
        default='table',
        help="Output format (default: table)"
    )

    args = parser.parse_args()

    try:
        # Initialize checker
        checker = SageMakerEndpointStatusChecker(region=args.region)

        if args.list_all or args.status_filter or args.summary:
            # List endpoints
            if args.summary:
                print("📊 Endpoint Status Summary")
                print("=" * 50)
                summary = checker.get_status_summary(args.status_filter)

                if args.format == 'json':
                    print(json.dumps(summary, indent=2, default=str))
                else:
                    print(f"Region: {summary.get('region', 'unknown')}")
                    print(f"Total Endpoints: {summary.get('total_endpoints', 0)}")
                    print(f"Status Breakdown:")
                    for status, count in summary.get('status_breakdown', {}).items():
                        print(f"  {status}: {count}")
                    print()
            else:
                print("📋 SageMaker Endpoints")
                print("=" * 50)
                endpoints = checker.list_endpoints(args.status_filter)

                if args.format == 'json':
                    print(json.dumps(endpoints, indent=2, default=str))
                else:
                    for endpoint in endpoints:
                        print(f"Name: {endpoint.get('EndpointName')}")
                        print(f"Status: {endpoint.get('EndpointStatus')}")
                        print(f"Created: {endpoint.get('CreationTime')}")
                        print("-" * 40)

            return

        if not args.endpoint_name:
            logger.error("❌ --endpoint-name is required when not using list/summary options")
            parser.print_help()
            sys.exit(1)

        endpoint_name = args.endpoint_name

        if args.health_check:
            # Comprehensive health check
            print(f"🏥 Health Check for Endpoint: {endpoint_name}")
            print("=" * 60)

            health = checker.check_endpoint_health(endpoint_name)

            if args.format == 'json':
                print(json.dumps(health, indent=2, default=str))
            else:
                print(f"Overall Health: {health.get('overall_health', 'unknown').upper()}")
                print(f"Status: {health.get('status', 'unknown')}")
                print(f"Last Checked: {health.get('timestamp', 'unknown')}")

                print("\n📋 Individual Checks:")
                for check_name, check_data in health.get('checks', {}).items():
                    if isinstance(check_data, dict):
                        print(f"  {check_name.title()}: {check_data.get('status', 'unknown')}")
                        print(f"    {check_data.get('message', 'No message')}")
                    else:
                        print(f"  {check_name.title()}: {check_data}")

                if health.get('issues'):
                    print("\n⚠️  Issues:")
                    for issue in health.get('issues', []):
                        print(f"  • {issue}")

                # Metrics
                metrics = health.get('metrics', {})
                if metrics:
                    print(f"\n📈 Usage Metrics (last {args.metrics_days} days):")
                    print(f"  Total Invocations: {metrics.get('total_invocations', 0):,}")
                    print(f"  Daily Average: {metrics.get('daily_invocations', 0):.1f}")
                    print(f"  Average Latency: {metrics.get('average_latency_ms', 0):.1f} ms")
                    print(f"  Error Rate: {metrics.get('error_rate', 0):.2%}")

                # Cost information
                if args.cost_estimate:
                    cost = health.get('cost', {})
                    if cost:
                        print(f"\n💰 Cost Estimates:")
                        print(f"  Hourly: ${cost.get('hourly_cost', 0):.2f}")
                        print(f"  Daily: ${cost.get('daily_cost', 0):.2f}")
                        print(f"  Monthly: ${cost.get('monthly_cost', 0):.2f}")

        else:
            # Basic endpoint info
            print(f"ℹ️  Endpoint Information: {endpoint_name}")
            print("=" * 50)

            info = checker.get_endpoint_info(endpoint_name)

            if args.format == 'json':
                print(json.dumps(info, indent=2, default=str))
            else:
                print(f"Name: {info.get('endpoint_name')}")
                print(f"Status: {info.get('endpoint_status')}")
                print(f"Config: {info.get('endpoint_config_name')}")
                print(f"Total Instances: {info.get('total_instances', 0)}")
                print(f"Instance Types: {', '.join(info.get('instance_types', []))}")
                print(f"Model Names: {', '.join(info.get('model_names', []))}")
                print(f"Created: {info.get('creation_time')}")
                print(f"Last Modified: {info.get('last_modified_time')}")

                if info.get('failure_reason'):
                    print(f"Failure Reason: {info['failure_reason']}")

                # Optional metrics and cost
                if args.cost_estimate:
                    cost = checker.estimate_cost(info)
                    print(f"\n💰 Cost Estimates:")
                    print(f"  Hourly: ${cost.get('hourly_cost', 0):.2f}")
                    print(f"  Monthly: ${cost.get('monthly_cost', 0):.2f}")

    except KeyboardInterrupt:
        logger.info("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()