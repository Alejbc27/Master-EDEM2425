resource "google_artifact_registry_repository" "appointment-api" {
  project  = var.project_id
  location = var.region
  repository_id = var.repository_name_appointment
  description   = "Repositorio Docker API de appointments"
  format        = "DOCKER"
}

locals {
  image_name = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name_appointment}/myimage:latest"
}

resource "null_resource" "build_push_image" {
  depends_on = [
    google_artifact_registry_repository.appointment-api
  ]

  triggers = {
    image        = local.image_name
  }

  provisioner "local-exec" {
      command = <<EOT
      gcloud builds submit --region=${var.region} --project=${var.project_id} --tag=${local.image_name} ./modules/appointment_api
  sleep 10
  EOT
    }
}

resource "google_cloud_run_service_iam_member" "invoker" {
  location = var.region
  project  = var.project_id
  service  = google_cloud_run_v2_service.appointment_api.name
  role     = "roles/run.invoker"
  member   = "allUsers"  
}

resource "google_cloud_run_v2_service" "appointment_api" {
  name     = var.job_name_appointment
  location = var.region
  deletion_protection = false
  project  = var.project_id
  template {
    containers {
      image = local.image_name

      env {
        name  = "DB_NAME"
        value = var.db_name
      }
      env {
      name  = "DB_USER"
        value = var.db_user
      }

      env {
        name = "DB_PASSWORD"
        value = var.db_password
      }

      env {
        name = "DB_HOST"
        value = var.db_host
      }

        env {
        name = "GOOGLE_CLIENT_SECRET"
        value = var.google_client_secret
      }

        env {
        name = "GOOGLE_TOKEN_FILE"
        value = var.google_token_file
      }

        env {
        name = "EMAIL_FROM"
        value = var.email_from
      }

        env {
        name = "EMAIL_BACKEND"
        value = var.email_backend
      }

    }
  }
  traffic {
    type = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
  depends_on = [
    null_resource.build_push_image
  ]
}

output "build_resource" {
  description = "Recurso que construye y sube la imagen Docker"
  value       = null_resource.build_push_image
}