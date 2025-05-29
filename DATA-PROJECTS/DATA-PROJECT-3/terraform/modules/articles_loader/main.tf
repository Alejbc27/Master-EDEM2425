resource "google_artifact_registry_repository" "articles_loader" {
  project  = var.project_id
  location = var.region
  repository_id = var.repository_name_articles_loader
  description   = "Repositorio Docker API de articles_loader"
  format        = "DOCKER"
}

locals {
  image_name = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name_articles_loader}/myimage:latest"
}

resource "null_resource" "build_push_image" {
  depends_on = [
    google_artifact_registry_repository.articles_loader
  ]

  triggers = {
    image        = local.image_name
  }

  provisioner "local-exec" {
      command = <<EOT
      gcloud builds submit --region=${var.region} --project=${var.project_id} --tag=${local.image_name} ./modules/articles_loader
  sleep 10
  EOT
    }
}


resource "google_cloud_run_v2_job" "articles_loader" {
  name     = var.job_name_articles_loader
  location = var.region
  deletion_protection = false
  project  = var.project_id
  template {
    template {
    containers {
      image = local.image_name

      env {
        name  = "BUCKET_NAME"
        value = var.bucket_name
      }
      env {
      name  = "SOURCE_FOLDER_PATH"
        value = var.source_folder_path
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
    google_cloud_run_v2_job.articles_loader
  ]

  provisioner "local-exec" {
  command = "gcloud run jobs execute ${var.job_name_articles_loader} --region=${var.region} --project=${var.project_id}"
}
}


output "build_resource" {
  description = "Recurso que construye y sube la imagen Docker"
  value       = null_resource.build_push_image
}

