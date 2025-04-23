variable "region" {
  description = "Region to deploy the Cloud Run service"
  type        = string
  default     = "asia-southeast1"
}

variable "mongodb_username" {
  description = "MongoDB username"
  type        = string
  default     = "hung"
}

variable "mongodb_password" {
  description = "MongoDB password"
  type        = string
  sensitive   = true
}

variable "mongodb_cluster" {
  description = "MongoDB cluster address"
  type        = string
  default     = "cluster0.vn2lqaa.mongodb.net"
}

variable "mongodb_database" {
  description = "MongoDB database name"
  type        = string
  default     = "quizapp"
} 