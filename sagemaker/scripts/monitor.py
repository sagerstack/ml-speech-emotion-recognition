#!/usr/bin/env python3
"""
SageMaker Endpoint Monitoring Script

This script monitors SageMaker endpoint performance, costs, and health metrics.
It sets up CloudWatch alerts and provides cost monitoring for the serverless endpoint.
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
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class EndpointMetrics:
    """Data class for endpoint metrics."""
    endpoint_name: str
    invocations: int
    invocation_4xx_errors: int
    invocation_5xx_errors: int
    model_latency_avg: float
    model_latency_max: float
    error_rate: float
    timestamp: datetime


@dataclass
class CostMetrics:
    """Data class for cost metrics."""
    endpoint_name: str
    daily_cost: float
    monthly_cost: float
    forecast_monthly_cost: float
    invocations_per_day: int
    avg_invocation_cost: float
    timestamp: datetime


class SageMakerMonitor:
    """Monitors SageMaker endpoints for performance and cost metrics."""

    def __init__(self, config_path: str = "../model-deployment/config.yaml"):
        """Initialize the SageMaker monitor."""
        self.config_path = config_path
        self.config = self._load_config()
        self.session = boto3.Session(region_name=self.config['aws']['region'])
        self.cloudwatch = self.session.client('cloudwatch')
        self.sagemaker = self.session.client('sagemaker')
        self.ce = self.session.client('ce')  # Cost Explorer

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

    def get_endpoint_metrics(self, endpoint_name: str, hours: int = 24) -> EndpointMetrics:
        """Get CloudWatch metrics for endpoint."""
        try:
            logger.info(f"Getting metrics for endpoint: {endpoint_name}")

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            # Define metrics to collect
            metric_queries = [
                {
                    'Id': 'invocations',
                    'Label': 'Invocations',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/SageMaker',
                            'MetricName': 'Invocations',
                            'Dimensions': [
                                {'Name': 'EndpointName', 'Value': endpoint_name}
                            ]
                        },
                        'Period': 3600,  # 1 hour
                        'Stat': 'Sum'
                    }
                },
                {
                    'Id': 'invocation_4xx_errors',
                    'Label': 'Invocation4XXErrors',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/SageMaker',
                            'MetricName': 'Invocation4XXErrors',
                            'Dimensions': [
                                {'Name': 'EndpointName', 'Value': endpoint_name}
                            ]
                        },
                        'Period': 3600,
                        'Stat': 'Sum'
                    }
                },
                {
                    'Id': 'invocation_5xx_errors',
                    'Label': 'Invocation5XXErrors',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/SageMaker',
                            'MetricName': 'Invocation5XXErrors',
                            'Dimensions': [
                                {'Name': 'EndpointName', 'Value': endpoint_name}
                            ]
                        },
                        'Period': 3600,
                        'Stat': 'Sum'
                    }
                },
                {
                    'Id': 'model_latency',
                    'Label': 'ModelLatency',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/SageMaker',
                            'MetricName': 'ModelLatency',
                            'Dimensions': [
                                {'Name': 'EndpointName', 'Value': endpoint_name}
                            ]
                        },
                        'Period': 3600,
                        'Stat': 'Average'
                    }
                },
                {
                    'Id': 'model_latency_max',
                    'Label': 'ModelLatencyMax',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/SageMaker',
                            'MetricName': 'ModelLatency',
                            'Dimensions': [
                                {'Name': 'EndpointName', 'Value': endpoint_name}
                            ]
                        },
                        'Period': 3600,
                        'Stat': 'Maximum'
                    }
                }
            ]

            # Get metrics
            response = self.cloudwatch.get_metric_data(
                MetricDataQueries=metric_queries,
                StartTime=start_time,
                EndTime=end_time
            )

            # Process results
            results = response['MetricDataResults']

            # Sum up values over the time period
            invocations = sum(results[0]['Values']) if results[0]['Values'] else 0
            errors_4xx = sum(results[1]['Values']) if results[1]['Values'] else 0
            errors_5xx = sum(results[2]['Values']) if results[2]['Values'] else 0
            latency_avg = sum(results[3]['Values']) / len(results[3]['Values']) if results[3]['Values'] else 0
            latency_max = max(results[4]['Values']) if results[4]['Values'] else 0

            total_errors = errors_4xx + errors_5xx
            error_rate = (total_errors / invocations * 100) if invocations > 0 else 0

            metrics = EndpointMetrics(
                endpoint_name=endpoint_name,
                invocations=invocations,
                invocation_4xx_errors=errors_4xx,
                invocation_5xx_errors=errors_5xx,
                model_latency_avg=latency_avg,
                model_latency_max=latency_max,
                error_rate=error_rate,
                timestamp=datetime.utcnow()
            )

            logger.info(f"✅ Metrics retrieved for {endpoint_name}")
            logger.info(f"  Invocations: {invocations}")
            logger.info(f"  Error Rate: {error_rate:.2f}%")
            logger.info(f"  Avg Latency: {latency_avg:.2f}ms")

            return metrics

        except Exception as e:
            logger.error(f"Failed to get endpoint metrics: {e}")
            raise

    def estimate_costs(self, endpoint_name: str, days: int = 30) -> CostMetrics:
        """Estimate costs for the endpoint."""
        try:
            logger.info(f"Estimating costs for endpoint: {endpoint_name}")

            # Get configuration
            memory_mb = self.config['serverless']['memory_size_in_mb']
            max_concurrency = self.config['serverless']['max_concurrency']

            # Serverless pricing (approximate)
            # Pricing varies by region, these are us-east-1 estimates
            per_gb_second = 0.000006208  # $0.000006208 per GB-second
            per_request = 0.0000002  # $0.0000002 per request

            # Get recent metrics for cost calculation
            metrics = self.get_endpoint_metrics(endpoint_name, hours=24 * days)

            # Calculate daily invocations
            daily_invocations = metrics.invocations / days if days > 0 else 0

            # Estimate memory cost (simplified)
            # Memory is billed per GB-second of active time
            # We'll estimate based on invocation time and concurrency
            avg_invocation_time = metrics.model_latency_avg / 1000  # Convert ms to seconds
            daily_gb_seconds = (memory_mb / 1024) * avg_invocation_time * daily_invocations * max_concurrency

            daily_memory_cost = daily_gb_seconds * per_gb_second
            daily_request_cost = daily_invocations * per_request
            daily_total_cost = daily_memory_cost + daily_request_cost

            # Calculate monthly costs
            monthly_cost = daily_total_cost * 30

            # Forecast based on current usage
            forecast_monthly_cost = monthly_cost

            cost_metrics = CostMetrics(
                endpoint_name=endpoint_name,
                daily_cost=daily_total_cost,
                monthly_cost=monthly_cost,
                forecast_monthly_cost=forecast_monthly_cost,
                invocations_per_day=int(daily_invocations),
                avg_invocation_cost=per_request + (avg_invocation_time * memory_mb / 1024 * per_gb_second),
                timestamp=datetime.utcnow()
            )

            logger.info(f"✅ Cost estimates for {endpoint_name}:")
            logger.info(f"  Daily cost: ${daily_total_cost:.4f}")
            logger.info(f"  Monthly cost: ${monthly_cost:.2f}")
            logger.info(f"  Daily invocations: {int(daily_invocations)}")

            return cost_metrics

        except Exception as e:
            logger.error(f"Failed to estimate costs: {e}")
            raise

    def setup_cloudwatch_alarms(self, endpoint_name: str) -> bool:
        """Set up CloudWatch alarms for the endpoint."""
        try:
            logger.info(f"Setting up CloudWatch alarms for: {endpoint_name}")

            # Alarm configurations
            alarms = [
                {
                    'name': f'{endpoint_name}-HighErrorRate',
                    'description': 'High error rate detected',
                    'metric': 'Invocations',
                    'statistic': 'Average',
                    'threshold': 10.0,  # 10% error rate
                    'comparison': 'GreaterThanThreshold',
                    'datapoints': 2,
                    'period': 300  # 5 minutes
                },
                {
                    'name': f'{endpoint_name}-HighLatency',
                    'description': 'High model latency detected',
                    'metric': 'ModelLatency',
                    'statistic': 'Average',
                    'threshold': 30000,  # 30 seconds
                    'comparison': 'GreaterThanThreshold',
                    'datapoints': 2,
                    'period': 300
                },
                {
                    'name': f'{endpoint_name}-NoInvocations',
                    'description': 'No invocations detected',
                    'metric': 'Invocations',
                    'statistic': 'Sum',
                    'threshold': 1,
                    'comparison': 'LessThanThreshold',
                    'datapoints': 12,  # 1 hour of no activity
                    'period': 300
                }
            ]

            for alarm_config in alarms:
                alarm_name = alarm_config['name']

                # Check if alarm already exists
                try:
                    self.cloudwatch.describe_alarms(AlarmNames=[alarm_name])
                    logger.info(f"Alarm {alarm_name} already exists, skipping...")
                    continue
                except self.cloudwatch.exceptions.ResourceNotFoundException:
                    pass  # Alarm doesn't exist, create it

                # Create alarm
                self.cloudwatch.put_metric_alarm(
                    AlarmName=alarm_name,
                    AlarmDescription=alarm_config['description'],
                    Namespace='AWS/SageMaker',
                    MetricName=alarm_config['metric'],
                    Statistic=alarm_config['statistic'],
                    Dimensions=[
                        {
                            'Name': 'EndpointName',
                            'Value': endpoint_name
                        }
                    ],
                    Threshold=alarm_config['threshold'],
                    ComparisonOperator=alarm_config['comparison'],
                    EvaluationPeriods=alarm_config['datapoints'],
                    Period=alarm_config['period'],
                    TreatMissingData='notBreaching'
                )

                logger.info(f"✅ Created alarm: {alarm_name}")

            # Set up cost alert
            cost_threshold = self.config['cost_optimization']['cost_alert_threshold']
            cost_alarm_name = f'{endpoint_name}-HighCost'

            try:
                self.cloudwatch.describe_alarms(AlarmNames=[cost_alarm_name])
                logger.info(f"Cost alarm {cost_alarm_name} already exists")
            except self.cloudwatch.exceptions.ResourceNotFoundException:
                # Create cost monitoring alarm
                self.cloudwatch.put_metric_alarm(
                    AlarmName=cost_alarm_name,
                    AlarmDescription=f'Monthly cost exceeds ${cost_threshold}',
                    Namespace='AWS/Billing',
                    MetricName='EstimatedCharges',
                    Statistic='Maximum',
                    Dimensions=[
                        {
                            'Name': 'Currency',
                            'Value': 'USD'
                        }
                    ],
                    Threshold=cost_threshold,
                    ComparisonOperator='GreaterThanThreshold',
                    EvaluationPeriods=1,
                    Period=86400,  # 24 hours
                    TreatMissingData='notBreaching'
                )
                logger.info(f"✅ Created cost alarm: {cost_alarm_name}")

            logger.info("✅ All CloudWatch alarms created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to set up CloudWatch alarms: {e}")
            return False

    def check_endpoint_health(self, endpoint_name: str) -> Dict[str, Any]:
        """Check endpoint health status."""
        try:
            logger.info(f"Checking health of endpoint: {endpoint_name}")

            # Get endpoint status
            response = self.sagemaker.describe_endpoint(EndpointName=endpoint_name)
            endpoint_status = response['EndpointStatus']

            # Get recent metrics
            metrics = self.get_endpoint_metrics(endpoint_name, hours=1)

            # Health assessment
            health_status = {
                "endpoint_name": endpoint_name,
                "endpoint_status": endpoint_status,
                "invocations_last_hour": metrics.invocations,
                "error_rate": metrics.error_rate,
                "avg_latency_ms": metrics.model_latency_avg,
                "health_score": "healthy",
                "issues": [],
                "timestamp": datetime.utcnow().isoformat()
            }

            # Check for issues
            if endpoint_status != "InService":
                health_status["health_score"] = "unhealthy"
                health_status["issues"].append(f"Endpoint status: {endpoint_status}")

            if metrics.error_rate > 5:
                health_status["health_score"] = "degraded" if health_status["health_score"] == "healthy" else "unhealthy"
                health_status["issues"].append(f"High error rate: {metrics.error_rate:.1f}%")

            if metrics.model_latency_avg > 30000:  # 30 seconds
                health_status["health_score"] = "degraded" if health_status["health_score"] == "healthy" else "unhealthy"
                health_status["issues"].append(f"High latency: {metrics.model_latency_avg:.0f}ms")

            if metrics.invocations == 0:
                health_status["issues"].append("No invocations in last hour")

            logger.info(f"✅ Health check completed: {health_status['health_score']}")
            if health_status["issues"]:
                for issue in health_status["issues"]:
                    logger.warning(f"  Issue: {issue}")

            return health_status

        except Exception as e:
            logger.error(f"Failed to check endpoint health: {e}")
            return {
                "endpoint_name": endpoint_name,
                "health_score": "unknown",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def generate_report(self, endpoint_name: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive monitoring report."""
        try:
            logger.info(f"Generating monitoring report for: {endpoint_name}")

            # Gather all metrics
            endpoint_metrics = self.get_endpoint_metrics(endpoint_name, hours=24)
            cost_metrics = self.estimate_costs(endpoint_name, days=30)
            health_status = self.check_endpoint_health(endpoint_name)

            # Get endpoint info
            endpoint_info = self.sagemaker.describe_endpoint(EndpointName=endpoint_name)

            # Compile report
            report = {
                "report_type": "sagemaker_monitoring",
                "endpoint_name": endpoint_name,
                "report_timestamp": datetime.utcnow().isoformat(),
                "endpoint_info": {
                    "endpoint_arn": endpoint_info.get("EndpointArn"),
                    "endpoint_status": endpoint_info.get("EndpointStatus"),
                    "creation_time": endpoint_info.get("CreationTime").isoformat() if endpoint_info.get("CreationTime") else None,
                    "production_variants": endpoint_info.get("ProductionVariants", [])
                },
                "metrics_24h": asdict(endpoint_metrics),
                "cost_estimates": asdict(cost_metrics),
                "health_status": health_status,
                "recommendations": self._generate_recommendations(endpoint_metrics, cost_metrics, health_status)
            }

            # Save report if requested
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(report, f, indent=2)
                logger.info(f"✅ Report saved to: {output_file}")

            return report

        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            raise

    def _generate_recommendations(self, metrics: EndpointMetrics, costs: CostMetrics, health: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on metrics."""
        recommendations = []

        # Cost recommendations
        if costs.monthly_cost > self.config['cost_optimization']['cost_alert_threshold']:
            recommendations.append(
                f"⚠️  Monthly cost (${costs.monthly_cost:.2f}) exceeds alert threshold. "
                f"Consider reducing usage or optimizing model size."
            )

        if costs.invocations_per_day == 0:
            recommendations.append(
                "💡 No invocations detected. Consider deleting the endpoint to save costs."
            )

        # Performance recommendations
        if metrics.error_rate > 5:
            recommendations.append(
                f"⚠️  High error rate ({metrics.error_rate:.1f}%). "
                f"Check model logs and consider endpoint re-deployment."
            )

        if metrics.model_latency_avg > 30000:
            recommendations.append(
                f"⚠️  High latency ({metrics.model_latency_avg:.0f}ms). "
                f"Consider optimizing model or increasing memory size."
            )

        if health["health_score"] == "healthy":
            recommendations.append("✅ Endpoint is performing well.")

        return recommendations

    def monitor_continuously(self, endpoint_name: str, interval_minutes: int = 60) -> None:
        """Continuously monitor endpoint."""
        try:
            logger.info(f"Starting continuous monitoring for: {endpoint_name}")
            logger.info(f"Monitoring interval: {interval_minutes} minutes")

            while True:
                try:
                    # Get metrics and health
                    health = self.check_endpoint_health(endpoint_name)
                    metrics = self.get_endpoint_metrics(endpoint_name, hours=1)

                    # Log key metrics
                    logger.info(f"📊 {endpoint_name} - "
                               f"Status: {health['health_score']}, "
                               f"Invocations: {metrics.invocations}, "
                               f"Error Rate: {metrics.error_rate:.1f}%, "
                               f"Latency: {metrics.model_latency_avg:.0f}ms")

                    # Check for alerts
                    if health["health_score"] in ["degraded", "unhealthy"]:
                        logger.warning(f"⚠️  Health issues detected:")
                        for issue in health["issues"]:
                            logger.warning(f"    - {issue}")

                    # Wait for next interval
                    time.sleep(interval_minutes * 60)

                except KeyboardInterrupt:
                    logger.info("Monitoring stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                    time.sleep(60)  # Wait 1 minute before retrying

        except Exception as e:
            logger.error(f"Continuous monitoring failed: {e}")
            raise


def main():
    """Main monitoring function."""
    parser = argparse.ArgumentParser(description="Monitor SageMaker endpoints")
    parser.add_argument("endpoint_name", help="Name of the SageMaker endpoint")
    parser.add_argument("--config", type=str, default="../model-deployment/config.yaml", help="Configuration file path")
    parser.add_argument("--metrics", action="store_true", help="Get endpoint metrics")
    parser.add_argument("--costs", action="store_true", help="Estimate costs")
    parser.add_argument("--health", action="store_true", help="Check endpoint health")
    parser.add_argument("--alarms", action="store_true", help="Set up CloudWatch alarms")
    parser.add_argument("--report", type=str, help="Generate monitoring report")
    parser.add_argument("--monitor", type=int, metavar="MINUTES", help="Continuous monitoring interval in minutes")

    args = parser.parse_args()

    try:
        monitor = SageMakerMonitor(args.config)

        if args.metrics:
            metrics = monitor.get_endpoint_metrics(args.endpoint_name)
            print("Endpoint Metrics:")
            print(json.dumps(asdict(metrics), indent=2, default=str))

        elif args.costs:
            costs = monitor.estimate_costs(args.endpoint_name)
            print("Cost Estimates:")
            print(json.dumps(asdict(costs), indent=2, default=str))

        elif args.health:
            health = monitor.check_endpoint_health(args.endpoint_name)
            print("Endpoint Health:")
            print(json.dumps(health, indent=2, default=str))

        elif args.alarms:
            success = monitor.setup_cloudwatch_alarms(args.endpoint_name)
            if success:
                print("✅ CloudWatch alarms set up successfully")
            else:
                print("❌ Failed to set up CloudWatch alarms")

        elif args.report:
            report = monitor.generate_report(args.endpoint_name, args.report)
            print("Monitoring Report Generated:")
            print(json.dumps(report, indent=2, default=str))

        elif args.monitor:
            monitor.monitor_continuously(args.endpoint_name, args.monitor)

        else:
            # Default: show all information
            print(f"📊 SageMaker Endpoint Monitor: {args.endpoint_name}")
            print("=" * 50)

            metrics = monitor.get_endpoint_metrics(args.endpoint_name)
            print(f"\n📈 Metrics (24h):")
            print(f"  Invocations: {metrics.invocations}")
            print(f"  Error Rate: {metrics.error_rate:.2f}%")
            print(f"  Avg Latency: {metrics.model_latency_avg:.0f}ms")

            costs = monitor.estimate_costs(args.endpoint_name)
            print(f"\n💰 Cost Estimates:")
            print(f"  Daily: ${costs.daily_cost:.4f}")
            print(f"  Monthly: ${costs.monthly_cost:.2f}")

            health = monitor.check_endpoint_health(args.endpoint_name)
            print(f"\n🏥 Health Status: {health['health_score']}")
            if health.get('issues'):
                for issue in health['issues']:
                    print(f"  ⚠️  {issue}")

    except Exception as e:
        logger.error(f"❌ Monitoring failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()