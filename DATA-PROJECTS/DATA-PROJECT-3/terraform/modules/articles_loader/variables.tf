variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
}

variable "repository_name_articles_loader" {
  description = "Artifact Registry repository ID for the articles-loader API"
  type        = string
  default     = "articles-loader-repo"
}

variable "job_name_articles_loader" {
  description = "Name of the Cloud Run service for the articles-loader API"
  type        = string
  default     = "articles-loader"
}

variable "bucket_name" {
  description = "Bucket name for GCS"
  type        = string
  default = "medical-articles-dataproject3"
}

variable "source_folder_path" {
  description = "source folder path"
  type        = string
  default = "/app/articles"
}


