variable "region" {
  description = "GCP region for resources"
  type        = string
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "firestore_collection" {
  description = "Firestore collection name"
  type        = string
  default ="patients-db-dp3"
}

variable "bq_dataset" {
  description = "Firestore collection name"
  type        = string
  default ="patients_dataset"
}
variable "bq_table" {
  description = "Firestore collection name"
  type        = string
  default ="patients_table"
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