variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
}

variable "repository_name_data_generator_clinic" {
  description = "Artifact Registry repository ID for the appointment API"
  type        = string
  default     = "data-generator-clinic-repo"
}

variable "job_name_data_generator_clinic" {
  description = "Name of the Cloud Run service for the appointment API"
  type        = string
  default     = "data-generator-clinic"
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

