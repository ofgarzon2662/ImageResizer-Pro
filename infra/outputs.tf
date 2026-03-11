output "alb_dns_name" {
  description = "Public ALB DNS name for API access."
  value       = aws_lb.api.dns_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.main.name
}

output "api_service_name" {
  description = "API ECS service name."
  value       = aws_ecs_service.api.name
}

output "worker_service_name" {
  description = "Worker ECS service name."
  value       = aws_ecs_service.worker.name
}

output "codedeploy_app_name" {
  description = "CodeDeploy ECS application name."
  value       = aws_codedeploy_app.api.name
}

output "codedeploy_deployment_group_name" {
  description = "CodeDeploy deployment group name for API blue/green."
  value       = aws_codedeploy_deployment_group.api.deployment_group_name
}

output "api_task_definition_arn" {
  description = "API task definition ARN."
  value       = aws_ecs_task_definition.api.arn
}

output "worker_task_definition_arn" {
  description = "Worker task definition ARN."
  value       = aws_ecs_task_definition.worker.arn
}

output "s3_input_bucket_name" {
  description = "Input bucket name."
  value       = aws_s3_bucket.input.bucket
}

output "s3_output_bucket_name" {
  description = "Output bucket name."
  value       = aws_s3_bucket.output.bucket
}

output "sqs_queue_url" {
  description = "Main SQS queue URL."
  value       = aws_sqs_queue.main.url
}

output "sqs_dlq_url" {
  description = "DLQ URL."
  value       = aws_sqs_queue.dlq.url
}

output "dynamodb_table_name" {
  description = "Jobs DynamoDB table name."
  value       = aws_dynamodb_table.jobs.name
}
