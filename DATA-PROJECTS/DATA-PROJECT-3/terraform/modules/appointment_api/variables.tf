variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
}

variable "repository_name_appointment" {
  description = "Artifact Registry repository ID for the appointment API"
  type        = string
  default     = "appointment-api-repo"
}

variable "job_name_appointment" {
  description = "Name of the Cloud Run service for the appointment API"
  type        = string
  default     = "appointment-api"
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

variable "google_client_secret" {
  description = "Path or content for Google client secret file"
  type        = string
  default = "C:/IA_Project3/api/bbdd/client_secret_710866946885-mrt7isos4sgnovpauf044ih0isek47l2.apps.googleusercontent.com.json"
}

variable "google_token_file" {
  description = "Path or content for Google OAuth token file"
  type        = string
  default = "C:/IA_Project3/api/bbdd/token.json"
}

variable "email_from" {
  description = "Default 'from' email address for sending emails"
  type        = string
  default = "Clinica DataProject3 <noreply@example.com>"
}

variable "email_backend" {
  description = "Email backend type (e.g., 'console', 'gmail')"
  type        = string
  default = "gmail"
}
