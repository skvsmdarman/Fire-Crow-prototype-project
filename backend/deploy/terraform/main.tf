terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    bucket = "firecrow-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix = "firecrow-${var.environment}"
  common_tags = {
    Environment = var.environment
    Project     = "firecrow"
    ManagedBy   = "terraform"
  }
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-vpc" })
}

# Public subnets (for ALB)
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-public-${count.index}" })
}

# Private subnets (for ECS tasks, RDS, Redis)
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-private-${count.index}" })
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = merge(local.common_tags, { Name = "${local.name_prefix}-igw" })
}

# NAT Gateway (for private subnet egress)
resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = merge(local.common_tags, { Name = "${local.name_prefix}-nat-eip" })
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  tags          = merge(local.common_tags, { Name = "${local.name_prefix}-nat" })
}

# Route tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-public-rt" })
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-private-rt" })
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# Security Groups
resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-alb-sg"
  description = "ALB security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-alb-sg" })
}

resource "aws_security_group" "ecs" {
  name        = "${local.name_prefix}-ecs-sg"
  description = "ECS tasks security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 10000
    to_port         = 10000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port   = 10000
    to_port     = 10000
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ecs-sg" })
}

resource "aws_security_group" "rds" {
  name        = "${local.name_prefix}-rds-sg"
  description = "RDS security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-rds-sg" })
}

resource "aws_security_group" "redis" {
  name        = "${local.name_prefix}-redis-sg"
  description = "ElastiCache Redis security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-redis-sg" })
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
  enable_deletion_protection = var.environment == "prod"

  access_logs {
    bucket  = aws_s3_bucket.access_logs.bucket
    prefix  = "alb"
    enabled = true
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-alb" })
}

resource "aws_lb_target_group" "api" {
  name        = "${local.name_prefix}-api-tg"
  port        = 10000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 15
    path                = "/health/ready"
    matcher             = "200"
  }

  stickiness {
    type    = "lb_cookie"
    enabled = false
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-api-tg" })
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# RDS PostgreSQL
resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnet"
  subnet_ids = aws_subnet.private[*].id
  tags       = merge(local.common_tags, { Name = "${local.name_prefix}-db-subnet" })
}

resource "aws_db_instance" "postgres" {
  identifier                   = "${local.name_prefix}-postgres"
  engine                       = "postgres"
  engine_version               = "16.3"
  instance_class               = var.rds_instance_class
  allocated_storage            = var.rds_storage_gb
  storage_type                 = "gp3"
  storage_encrypted            = true
  db_name                      = "firecrow"
  username                     = "firecrow"
  password                     = random_password.rds.result
  db_subnet_group_name         = aws_db_subnet_group.main.name
  vpc_security_group_ids       = [aws_security_group.rds.id]
  backup_retention_period      = var.environment == "prod" ? 30 : 7
  backup_window                = "03:00-04:00"
  maintenance_window           = "sun:05:00-sun:06:00"
  copy_tags_to_snapshot        = true
  deletion_protection          = var.environment == "prod"
  skip_final_snapshot          = var.environment != "prod"
  performance_insights_enabled = var.environment == "prod"
  monitoring_interval          = 60
  monitoring_role_arn          = aws_iam_role.rds_enhanced_monitoring.arn

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-postgres" })
}

resource "random_password" "rds" {
  length  = 24
  special = false
}

# ElastiCache Redis
resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name_prefix}-redis-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id          = "${local.name_prefix}-redis"
  description                   = "Fire Crow Redis cluster"
  engine                        = "redis"
  engine_version                = "7.1"
  node_type                     = var.redis_node_type
  num_cache_clusters            = var.environment == "prod" ? 2 : 1
  port                          = 6379
  subnet_group_name             = aws_elasticache_subnet_group.main.name
  security_group_ids            = [aws_security_group.redis.id]
  automatic_failover_enabled    = var.environment == "prod"
  multi_az_enabled              = var.environment == "prod"
  transit_encryption_enabled    = true
  at_rest_encryption_enabled    = true
  apply_immediately             = var.environment != "prod"
  auto_minor_version_upgrade    = true
  maintenance_window            = "sun:06:00-sun:07:00"
  snapshot_retention_limit      = var.environment == "prod" ? 7 : 0
  snapshot_window               = "04:00-05:00"

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-redis" })
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = merge(local.common_tags, { Name = "${local.name_prefix}-cluster" })
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_execution" {
  name = "${local.name_prefix}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })

  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
    "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess",
  ]

  tags = local.common_tags
}

# ECS Task Role
resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

# ECS Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name_prefix}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "api"
      image = "${var.container_image}:${var.container_tag}"
      essential = true
      portMappings = [{
        containerPort = 10000
        protocol      = "tcp"
      }]
      environment = [
        { name = "DEBUG", value = "false" },
        { name = "PORT", value = "10000" },
        { name = "FRONTEND_URL", value = "https://${var.domain_name}" },
        { name = "CORS_ORIGINS", value = "https://${var.domain_name}" },
        { name = "FIRE_CROW_MOCK_SANDBOX", value = "false" },
        { name = "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", value = "15" },
        { name = "MFA_ENFORCE_FOR_ADMINS", value = "true" },
      ]
      secrets = [
        { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.database_url.arn },
        { name = "REDIS_URL", valueFrom = aws_secretsmanager_secret.redis_url.arn },
        { name = "SECRET_KEY", valueFrom = aws_secretsmanager_secret.secret_key.arn },
        { name = "ENCRYPTION_KEY", valueFrom = aws_secretsmanager_secret.encryption_key.arn },
        { name = "GITHUB_CLIENT_ID", valueFrom = aws_secretsmanager_secret.github_client_id.arn },
        { name = "GITHUB_CLIENT_SECRET", valueFrom = aws_secretsmanager_secret.github_client_secret.arn },
        { name = "GOOGLE_CLIENT_ID", valueFrom = aws_secretsmanager_secret.google_client_id.arn },
        { name = "GOOGLE_CLIENT_SECRET", valueFrom = aws_secretsmanager_secret.google_client_secret.arn },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:10000/health/live || exit 1"]
        interval    = 10
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
    }
  ])

  tags = local.common_tags
}

# ECS Worker Task Definition
resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name_prefix}-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "worker"
      image = "${var.container_image}:${var.container_tag}"
      essential = true
      command  = ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
      environment = [
        { name = "DEBUG", value = "false" },
        { name = "FIRE_CROW_MOCK_SANDBOX", value = "false" },
      ]
      secrets = [
        { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.database_url.arn },
        { name = "REDIS_URL", valueFrom = aws_secretsmanager_secret.redis_url.arn },
        { name = "SECRET_KEY", valueFrom = aws_secretsmanager_secret.secret_key.arn },
        { name = "ENCRYPTION_KEY", valueFrom = aws_secretsmanager_secret.encryption_key.arn },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.worker.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "worker"
        }
      }
    },
    {
      name  = "beat"
      image = "${var.container_image}:${var.container_tag}"
      essential = false
      command  = ["celery", "-A", "app.workers.celery_app", "beat", "--loglevel=info"]
      environment = [
        { name = "DEBUG", value = "false" },
        { name = "REDIS_URL_VAL", value = "" },
      ]
      secrets = [
        { name = "REDIS_URL", valueFrom = aws_secretsmanager_secret.redis_url.arn },
        { name = "SECRET_KEY", valueFrom = aws_secretsmanager_secret.secret_key.arn },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.beat.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "beat"
        }
      }
    }
  ])

  tags = local.common_tags
}

# ECS Services
resource "aws_ecs_service" "api" {
  name                              = "${local.name_prefix}-api"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.api.arn
  desired_count                     = var.api_desired_count
  launch_type                       = "FARGATE"
  platform_version                  = "1.4.0"
  health_check_grace_period_seconds = 30

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 10000
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = local.common_tags
}

resource "aws_ecs_service" "worker" {
  name            = "${local.name_prefix}-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"
  platform_version = "1.4.0"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  tags = local.common_tags
}

# CloudWatch
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name_prefix}/api"
  retention_in_days = 90
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${local.name_prefix}/worker"
  retention_in_days = 90
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "beat" {
  name              = "/ecs/${local.name_prefix}/beat"
  retention_in_days = 90
  tags              = local.common_tags
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "${local.name_prefix}-alb-5xx-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_ELB_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "ALB 5XX errors exceeded threshold"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "target_response_time" {
  alarm_name          = "${local.name_prefix}-target-response-time-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 3.0
  alarm_description   = "Target response time exceeded 3s average"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  dimensions = {
    TargetGroup = aws_lb_target_group.api.arn_suffix
    LoadBalancer = aws_lb.main.arn_suffix
  }
  tags = local.common_tags
}

# SNS for alarms
resource "aws_sns_topic" "alarms" {
  name = "${local.name_prefix}-alarms"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "alarms_email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# S3 for access logs
resource "aws_s3_bucket" "access_logs" {
  bucket = "${local.name_prefix}-access-logs"
  tags   = local.common_tags
}

resource "aws_s3_bucket_lifecycle_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  rule {
    id     = "expire"
    status = "Enabled"
    expiration {
      days = 90
    }
  }
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  bucket                  = aws_s3_bucket.access_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Secrets Manager
resource "aws_secretsmanager_secret" "database_url" {
  name        = "${local.name_prefix}-database-url"
  description = "PostgreSQL connection string"
  tags        = local.common_tags
}

resource "aws_secretsmanager_secret" "redis_url" {
  name        = "${local.name_prefix}-redis-url"
  description = "Redis connection string"
  tags        = local.common_tags
}

resource "aws_secretsmanager_secret" "secret_key" {
  name        = "${local.name_prefix}-secret-key"
  description = "Django/FastAPI SECRET_KEY"
  tags        = local.common_tags
}

resource "aws_secretsmanager_secret" "encryption_key" {
  name        = "${local.name_prefix}-encryption-key"
  description = "Encryption key for provider tokens"
  tags        = local.common_tags
}

resource "aws_secretsmanager_secret" "github_client_id" {
  name        = "${local.name_prefix}-github-client-id"
  tags        = local.common_tags
}

resource "aws_secretsmanager_secret" "github_client_secret" {
  name        = "${local.name_prefix}-github-client-secret"
  tags        = local.common_tags
}

resource "aws_secretsmanager_secret" "google_client_id" {
  name        = "${local.name_prefix}-google-client-id"
  tags        = local.common_tags
}

resource "aws_secretsmanager_secret" "google_client_secret" {
  name        = "${local.name_prefix}-google-client-secret"
  tags        = local.common_tags
}

# IAM for RDS Enhanced Monitoring
resource "aws_iam_role" "rds_enhanced_monitoring" {
  name = "${local.name_prefix}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })

  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole",
  ]

  tags = local.common_tags
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}
