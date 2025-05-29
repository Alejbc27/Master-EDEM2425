variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
}

variable "repository_name_metabase" {
  description = "Artifact Registry repository ID for metabase"
  type        = string
  default     = "metabase-repo"
}

variable "job_name_metabase" {
  description = "Name of the Cloud Run service for metabase"
  type        = string
  default     = "metabase"
}

variable "mb_db_type" {
  description = "Database type for Metabase (e.g., 'postgres', 'mysql')"
  type        = string
  default = "postgres"
}

variable "mb_db_dbname" {
  description = "Database name"
  type        = string
  default = "metabase"
}

 variable "mb_db_port" {
   description = "Database port"
   type        = string
   default = "5432"
 }

variable "mb_db_user" {
  description = "Database username"
  type        = string
  default = "postgres"
}

variable "mb_db_pass" {
  description = "Database password"
  type        = string
  sensitive   = true
  default = "postgres"
}


variable "mb_sql_instance" {
  description = "Database password"
  type        = string
  default = "data-project-3-457210:europe-west1:clinic-postgres"
}


