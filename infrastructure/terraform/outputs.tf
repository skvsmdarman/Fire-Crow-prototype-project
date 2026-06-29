output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
  sensitive   = true
}

output "database_url_secret_arn" {
  description = "ARN of the database URL secret"
  value       = aws_secretsmanager_secret.database_url.arn
}

output "redis_url_secret_arn" {
  description = "ARN of the Redis URL secret"
  value       = aws_secretsmanager_secret.redis_url.arn
}

output "sns_alarms_topic_arn" {
  description = "ARN of the SNS alarms topic"
  value       = aws_sns_topic.alarms.arn
}

output "api_service_name" {
  description = "ECS API service name"
  value       = aws_ecs_service.api.name
}
