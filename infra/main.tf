provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_vpc" "default" {
  default = true
}
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

locals {
  base_name              = "${var.project_prefix}-${var.environment}"
  api_repository_name    = "${var.project_prefix}-api"
  worker_repository_name = "${var.project_prefix}-worker"
  cluster_name           = "${local.base_name}-cluster"
  api_service_name       = "${local.base_name}-api-service"
  worker_service_name    = "${local.base_name}-worker-service"
  codedeploy_app_name    = "${local.base_name}-codedeploy-app"
  codedeploy_group_name  = "${local.base_name}-api-dg"
  input_bucket_name      = "${var.project_prefix}-${data.aws_caller_identity.current.account_id}-${var.environment}-input"
  output_bucket_name     = "${var.project_prefix}-${data.aws_caller_identity.current.account_id}-${var.environment}-output"
  jobs_table_name        = "ImageResizerJobs"
  api_log_group_name     = "/ecs/imageresizer-api"
  worker_log_group_name  = "/ecs/imageresizer-worker"
  api_container_name     = "api"
  worker_container_name  = "worker"
  main_queue_name        = "${local.base_name}-jobs"
  dlq_queue_name         = "${local.base_name}-jobs-dlq"
  execution_role_name    = "${local.base_name}-ecs-exec-role"
  api_task_role_name     = "${local.base_name}-api-task-role"
  worker_task_role_name  = "${local.base_name}-worker-task-role"
  codedeploy_role_name   = "${local.base_name}-codedeploy-role"
  alb_name               = "${local.base_name}-alb"
  alb_sg_name            = "${local.base_name}-alb-sg"
  api_sg_name            = "${local.base_name}-api-sg"
  worker_sg_name         = "${local.base_name}-worker-sg"
  api_task_family        = "${local.base_name}-api-task"
  worker_task_family     = "${local.base_name}-worker-task"
  api_blue_tg_name       = "${var.project_prefix}-${var.environment}-ab"
  api_green_tg_name      = "${var.project_prefix}-${var.environment}-ag"
  tags = {
    Project = var.project_name
    Env     = var.environment
    Owner   = var.owner
  }
}

resource "aws_ecr_repository" "api" {
  name                 = local.api_repository_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = local.tags
}

resource "aws_ecr_repository" "worker" {
  name                 = local.worker_repository_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "api" {
  name              = local.api_log_group_name
  retention_in_days = var.log_retention_days
  tags              = local.tags
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = local.worker_log_group_name
  retention_in_days = var.log_retention_days
  tags              = local.tags
}

resource "aws_s3_bucket" "input" {
  bucket = local.input_bucket_name
  tags   = local.tags
}

resource "aws_s3_bucket_public_access_block" "input" {
  bucket                  = aws_s3_bucket.input.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "input" {
  bucket = aws_s3_bucket.input.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "input" {
  bucket = aws_s3_bucket.input.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_policy" "input_tls_only" {
  bucket = aws_s3_bucket.input.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyInsecureTransport"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.input.arn,
          "${aws_s3_bucket.input.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket" "output" {
  bucket = local.output_bucket_name
  tags   = local.tags
}

resource "aws_s3_bucket_public_access_block" "output" {
  bucket                  = aws_s3_bucket.output.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "output" {
  bucket = aws_s3_bucket.output.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "output" {
  bucket = aws_s3_bucket.output.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_policy" "output_tls_only" {
  bucket = aws_s3_bucket.output.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyInsecureTransport"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.output.arn,
          "${aws_s3_bucket.output.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

resource "aws_sqs_queue" "dlq" {
  name                      = local.dlq_queue_name
  message_retention_seconds = 1209600
  tags                      = local.tags
}

resource "aws_sqs_queue" "main" {
  name                       = local.main_queue_name
  visibility_timeout_seconds = 300
  receive_wait_time_seconds  = 20
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5
  })
  tags = local.tags
}

resource "aws_dynamodb_table" "jobs" {
  name         = local.jobs_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "jobId"

  attribute {
    name = "jobId"
    type = "S"
  }

  tags = local.tags
}

data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_execution" {
  name               = local.execution_role_name
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed_policy" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "api_task" {
  name               = local.api_task_role_name
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "api_task_inline" {
  statement {
    sid = "InputBucketAccess"
    actions = [
      "s3:PutObject",
      "s3:GetObject"
    ]
    resources = ["${aws_s3_bucket.input.arn}/uploads/*"]
  }

  statement {
    sid = "OutputBucketReadAccess"
    actions = [
      "s3:GetObject"
    ]
    resources = ["${aws_s3_bucket.output.arn}/outputs/*"]
  }

  statement {
    sid = "BucketListPrefixAccess"
    actions = [
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.input.arn,
      aws_s3_bucket.output.arn
    ]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        "uploads/*",
        "outputs/*"
      ]
    }
  }

  statement {
    sid = "BucketHeadAccessForReadiness"
    actions = [
      "s3:ListBucket"
    ]
    resources = [aws_s3_bucket.input.arn]
  }

  statement {
    sid = "SendJobsToQueue"
    actions = [
      "sqs:SendMessage",
      "sqs:GetQueueAttributes"
    ]
    resources = [aws_sqs_queue.main.arn]
  }

  statement {
    sid = "WriteAndReadJobsTable"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
      "dynamodb:ConditionCheckItem",
      "dynamodb:DescribeTable"
    ]
    resources = [aws_dynamodb_table.jobs.arn]
  }
}

resource "aws_iam_role_policy" "api_task_inline" {
  name   = "${local.base_name}-api-task-inline"
  role   = aws_iam_role.api_task.id
  policy = data.aws_iam_policy_document.api_task_inline.json
}

resource "aws_iam_role" "worker_task" {
  name               = local.worker_task_role_name
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "worker_task_inline" {
  statement {
    sid = "ReadAndAckQueueMessages"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:ChangeMessageVisibility",
      "sqs:GetQueueAttributes"
    ]
    resources = [aws_sqs_queue.main.arn]
  }

  statement {
    sid = "ReadInputObjects"
    actions = [
      "s3:GetObject"
    ]
    resources = ["${aws_s3_bucket.input.arn}/uploads/*"]
  }

  statement {
    sid = "WriteOutputObjects"
    actions = [
      "s3:PutObject",
      "s3:GetObject"
    ]
    resources = ["${aws_s3_bucket.output.arn}/outputs/*"]
  }

  statement {
    sid = "ReadAndUpdateJobsTable"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:UpdateItem"
    ]
    resources = [aws_dynamodb_table.jobs.arn]
  }
}

resource "aws_iam_role_policy" "worker_task_inline" {
  name   = "${local.base_name}-worker-task-inline"
  role   = aws_iam_role.worker_task.id
  policy = data.aws_iam_policy_document.worker_task_inline.json
}

data "aws_iam_policy_document" "codedeploy_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["codedeploy.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "codedeploy" {
  name               = local.codedeploy_role_name
  assume_role_policy = data.aws_iam_policy_document.codedeploy_assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "codedeploy_managed_policy" {
  role       = aws_iam_role.codedeploy.name
  policy_arn = "arn:aws:iam::aws:policy/AWSCodeDeployRoleForECS"
}

resource "aws_ecs_cluster" "main" {
  name = local.cluster_name
  tags = local.tags
}

resource "aws_security_group" "alb" {
  name        = local.alb_sg_name
  description = "Allow inbound HTTP from internet"
  vpc_id      = data.aws_vpc.default.id
  tags        = local.tags
}

resource "aws_vpc_security_group_ingress_rule" "alb_http_in" {
  security_group_id = aws_security_group.alb.id
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "alb_https_out" {
  security_group_id = aws_security_group.alb.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_api" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.api.id
  ip_protocol                  = "tcp"
  from_port                    = var.api_container_port
  to_port                      = var.api_container_port
}

resource "aws_security_group" "api" {
  name        = local.api_sg_name
  description = "Allow API traffic only from ALB security group"
  vpc_id      = data.aws_vpc.default.id
  tags        = local.tags
}

resource "aws_vpc_security_group_ingress_rule" "api_from_alb" {
  security_group_id            = aws_security_group.api.id
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = var.api_container_port
  to_port                      = var.api_container_port
}

resource "aws_vpc_security_group_egress_rule" "api_https_out" {
  security_group_id = aws_security_group.api.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_security_group" "worker" {
  name        = local.worker_sg_name
  description = "Worker has no inbound traffic"
  vpc_id      = data.aws_vpc.default.id
  tags        = local.tags
}

resource "aws_vpc_security_group_egress_rule" "worker_https_out" {
  security_group_id = aws_security_group.worker.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_lb" "api" {
  name               = local.alb_name
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = data.aws_subnets.default.ids
  tags               = local.tags
}

resource "aws_lb_target_group" "api_blue" {
  name        = local.api_blue_tg_name
  port        = var.api_container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = data.aws_vpc.default.id

  health_check {
    enabled             = true
    path                = "/healthz"
    matcher             = "200-399"
    healthy_threshold   = 2
    unhealthy_threshold = 5
    interval            = 30
    timeout             = 5
  }

  tags = local.tags
}

resource "aws_lb_target_group" "api_green" {
  name        = local.api_green_tg_name
  port        = var.api_container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = data.aws_vpc.default.id

  health_check {
    enabled             = true
    path                = "/healthz"
    matcher             = "200-399"
    healthy_threshold   = 2
    unhealthy_threshold = 5
    interval            = 30
    timeout             = 5
  }

  tags = local.tags
}

resource "aws_lb_listener" "api_http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_blue.arn
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = local.api_task_family
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.api_cpu)
  memory                   = tostring(var.api_memory)
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.api_task.arn

  container_definitions = jsonencode([
    {
      name      = local.api_container_name
      image     = var.api_image
      essential = true
      portMappings = [
        {
          containerPort = var.api_container_port
          hostPort      = var.api_container_port
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "ENVIRONMENT", value = "aws" },
        { name = "AWS_REGION", value = data.aws_region.current.name },
        { name = "JOBS_BUCKET_INPUT", value = aws_s3_bucket.input.bucket },
        { name = "JOBS_BUCKET_OUTPUT", value = aws_s3_bucket.output.bucket },
        { name = "JOBS_QUEUE_URL", value = aws_sqs_queue.main.url },
        { name = "JOBS_TABLE_NAME", value = aws_dynamodb_table.jobs.name },
        { name = "PRESIGN_TTL_SECONDS", value = "900" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = local.tags
}

resource "aws_ecs_task_definition" "worker" {
  family                   = local.worker_task_family
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.worker_cpu)
  memory                   = tostring(var.worker_memory)
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.worker_task.arn

  container_definitions = jsonencode([
    {
      name      = local.worker_container_name
      image     = var.worker_image
      essential = true
      command   = ["sh", "-c", "while true; do sleep 30; done"]
      environment = [
        { name = "ENVIRONMENT", value = "aws" },
        { name = "AWS_REGION", value = data.aws_region.current.name },
        { name = "JOBS_BUCKET_INPUT", value = aws_s3_bucket.input.bucket },
        { name = "JOBS_BUCKET_OUTPUT", value = aws_s3_bucket.output.bucket },
        { name = "JOBS_QUEUE_URL", value = aws_sqs_queue.main.url },
        { name = "JOBS_TABLE_NAME", value = aws_dynamodb_table.jobs.name }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.worker.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = local.tags
}

resource "aws_ecs_service" "api" {
  name            = local.api_service_name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  deployment_controller {
    type = "CODE_DEPLOY"
  }

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api_blue.arn
    container_name   = local.api_container_name
    container_port   = var.api_container_port
  }

  lifecycle {
    ignore_changes = [task_definition, load_balancer]
  }

  depends_on = [aws_lb_listener.api_http]
  tags       = local.tags
}

resource "aws_ecs_service" "worker" {
  name            = local.worker_service_name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.worker.id]
    assign_public_ip = true
  }

  lifecycle {
    ignore_changes = [task_definition]
  }

  tags = local.tags
}

resource "aws_codedeploy_app" "api" {
  name             = local.codedeploy_app_name
  compute_platform = "ECS"
  tags             = local.tags
}

resource "aws_codedeploy_deployment_group" "api" {
  app_name               = aws_codedeploy_app.api.name
  deployment_group_name  = local.codedeploy_group_name
  service_role_arn       = aws_iam_role.codedeploy.arn
  deployment_config_name = "CodeDeployDefault.ECSCanary10Percent5Minutes"

  deployment_style {
    deployment_type   = "BLUE_GREEN"
    deployment_option = "WITH_TRAFFIC_CONTROL"
  }

  ecs_service {
    cluster_name = aws_ecs_cluster.main.name
    service_name = aws_ecs_service.api.name
  }

  blue_green_deployment_config {
    deployment_ready_option {
      action_on_timeout = "CONTINUE_DEPLOYMENT"
    }

    terminate_blue_instances_on_deployment_success {
      action                           = "TERMINATE"
      termination_wait_time_in_minutes = 5
    }
  }

  load_balancer_info {
    target_group_pair_info {
      prod_traffic_route {
        listener_arns = [aws_lb_listener.api_http.arn]
      }

      target_group {
        name = aws_lb_target_group.api_blue.name
      }

      target_group {
        name = aws_lb_target_group.api_green.name
      }
    }
  }

  auto_rollback_configuration {
    enabled = true
    events  = ["DEPLOYMENT_FAILURE"]
  }

  depends_on = [aws_ecs_service.api]
}
