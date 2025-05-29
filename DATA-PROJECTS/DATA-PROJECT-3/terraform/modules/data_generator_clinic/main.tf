resource "google_artifact_registry_repository" "data_generator_clinic" {
  project  = var.project_id
  location = var.region
  repository_id = var.repository_name_data_generator_clinic
  description   = "Repositorio Docker API de appointments"
  format        = "DOCKER"
}

locals {
  image_name = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name_data_generator_clinic}/myimage:latest"
}

resource "null_resource" "build_push_image" {
  depends_on = [
    google_artifact_registry_repository.data_generator_clinic
  ]

  triggers = {
    image        = local.image_name
  }

  provisioner "local-exec" {
      command = <<EOT
      gcloud builds submit --region=${var.region} --project=${var.project_id} --tag=${local.image_name} ./modules/data_generator_clinic
  sleep 10
  EOT
    }
}


resource "google_cloud_run_v2_job" "data_generator_clinic" {
  name     = var.job_name_data_generator_clinic
  location = var.region
  deletion_protection = false
  project  = var.project_id
  template {
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



      }
    }
  }

  depends_on = [
    null_resource.build_push_image
  ]
}

resource "null_resource" "execute_job" {
  depends_on = [
    google_cloud_run_v2_job.data_generator_clinic
  ]

  provisioner "local-exec" {
  command = "gcloud run jobs execute ${var.job_name_data_generator_clinic} --region=${var.region} --project=${var.project_id}"
}
}

output "build_resource" {
  description = "Recurso que construye y sube la imagen Docker"
  value       = null_resource.build_push_image
}