variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ARN of the ACM certificate for HTTPS"
  type        = string
}

variable "container_image" {
  description = "Container image repository"
  type        = string
  default     = "ghcr.io/johan-droid/firecrow"
}

variable "container_tag" {
  description = "Container image tag"
  type        = string
  default     = "latest"
}

variable "api_desired_count" {
  description = "Number of API task replicas"
  type        = number
  default     = 2
}

variable "api_cpu" {
  description = "CPU units for API tasks (512 = 0.5 vCPU)"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Memory (MB) for API tasks"
  type        = number
  default     = 1024
}

variable "worker_desired_count" {
  description = "Number of worker task replicas"
  type        = number
  default     = 2
}

variable "worker_cpu" {
  description = "CPU units for worker tasks"
  type        = number
  default     = 1024
}

variable "worker_memory" {
  description = "Memory (MB) for worker tasks"
  type        = number
  default     = 2048
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "rds_storage_gb" {
  description = "RDS storage in GB"
  type        = number
  default     = 100
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.medium"
}

variable "alarm_email" {
  description = "Email for CloudWatch alarm notifications"
  type        = string
}

variable "sla_uptime_percentage" {
  description = "Target uptime percentage"
  type        = number
  default     = 99.5
}
