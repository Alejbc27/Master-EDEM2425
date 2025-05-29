variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
}

variable "repository_name_vector_database_api" {
  description = "Artifact Registry repository ID for the vector database API"
  type        = string
  default     = "vector-database-api-repo"
}

variable "job_name_vector_database_api" {
  description = "Name of the Cloud Run service for the vector database API"
  type        = string
  default     = "vector-database-api"
}

variable "db_name" {
  description = "Database name to connect to"
  type        = string
  default = "clinics"
}

variable "db_user" {
  description = "Database username"
  type        = string
  default = "postgres"
}

variable "db_port" {
  description = "Database username"
  type        = string
  default = "5432"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
  default = "postgres"
}

variable "db_host" {
  description = "Database host address or connection name"
  type        = string
}

variable "gcs_bucket_name" {
  type        = string
  description = "Nombre del bucket GCS donde están tus JSON"
  default = "medical-articles-dataproject3"
}

variable "gcs_prefix" {
  type        = string
  description = "Prefijo (carpeta) dentro del bucket GCS"
  default     = "articles/"
}
