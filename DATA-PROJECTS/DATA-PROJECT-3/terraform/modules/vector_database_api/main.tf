resource "google_artifact_registry_repository" "vector_database_api" {
  project  = var.project_id
  location = var.region
  repository_id = var.repository_name_vector_database_api
  description   = "Repositorio Docker API de appointments"
  format        = "DOCKER"
}

locals {
  image_name = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name_vector_database_api}/myimage:latest"
  pg_connection_string = format(
    "postgresql://%s:%s@%s:%d/%s",
    var.db_user,
    var.db_password,
    var.db_host,
    var.db_port,
    var.db_name,
  )
}

resource "null_resource" "build_push_image" {
  depends_on = [
    google_artifact_registry_repository.vector_database_api
  ]

    triggers = {
        image        = local.image_name
  }

  provisioner "local-exec" {
      command = <<EOT
      gcloud builds submit --region=${var.region} --project=${var.project_id} --tag=${local.image_name} ./modules/vector_database_api
  sleep 10
  EOT
    }
}

resource "google_cloud_run_service_iam_member" "invoker" {
  location = var.region
  project  = var.project_id
  service  = google_cloud_run_v2_service.vector_database_api.name
  role     = "roles/run.invoker"
  member   = "allUsers"  
}


resource "google_cloud_run_v2_service" "vector_database_api" {
  name     = var.job_name_vector_database_api
  location = var.region
  deletion_protection = false
  project  = var.project_id

  template {
    containers {
      image = local.image_name

      ports {
        container_port = 8080
      }

      env {
        name  = "PG_CONNECTION_STRING"
        value = local.pg_connection_string
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = var.gcs_bucket_name
      }
      env {
        name  = "GCS_PREFIX"
        value = var.gcs_prefix
      }
    }

  }

  traffic {
    percent         = 100
    type = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  depends_on = [
    null_resource.build_push_image,
    google_storage_bucket.articles
  ]
}


resource "google_storage_bucket" "articles" {
  name                        = var.gcs_bucket_name   
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy             = true

  versioning {
    enabled = true
  }
}

output "build_resource" {
  description = "Recurso que construye y sube la imagen Docker"
  value       = null_resource.build_push_image
}