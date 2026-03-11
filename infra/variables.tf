variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "project_prefix" {
  description = "Unique prefix used for all resource names."
  type        = string
  default     = "imageresizer-s2"
}

variable "project_name" {
  description = "Project tag value."
  type        = string
  default     = "ImageResizerPro"
}

variable "environment" {
  description = "Environment tag value."
  type        = string
  default     = "sprint2"
}

variable "owner" {
  description = "Owner tag value."
  type        = string
}

variable "api_container_port" {
  description = "API container port."
  type        = number
  default     = 8000
}

variable "api_cpu" {
  description = "API task CPU units."
  type        = number
  default     = 256
}

variable "api_memory" {
  description = "API task memory in MiB."
  type        = number
  default     = 512
}

variable "worker_cpu" {
  description = "Worker task CPU units."
  type        = number
  default     = 256
}

variable "worker_memory" {
  description = "Worker task memory in MiB."
  type        = number
  default     = 512
}

variable "api_desired_count" {
  description = "Desired number of API tasks."
  type        = number
  default     = 1
}

variable "worker_desired_count" {
  description = "Desired number of worker tasks."
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days."
  type        = number
  default     = 14
}

variable "api_image" {
  description = "Initial API image URI. CI/CD should update task definition revisions later."
  type        = string
  default     = "public.ecr.aws/docker/library/nginx:stable"
}

variable "worker_image" {
  description = "Initial worker image URI. CI/CD should update task definition revisions later."
  type        = string
  default     = "public.ecr.aws/docker/library/busybox:stable"
}
