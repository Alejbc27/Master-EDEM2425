
resource "google_artifact_registry_repository" "metabase" {
     project  = var.project_id
     location = var.region
     repository_id = var.repository_name_metabase
     description   = "Repositorio de Metabase"
     format        = "DOCKER"
   }

locals {
  image_name = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name_metabase}/myimage:latest"
  }

resource "null_resource" "build_push_image" {
     depends_on = [
       google_artifact_registry_repository.metabase
     ]

      triggers = {
       image        = local.image_name
       docker_hash = filesha1("${path.module}/Dockerfile")
     }

     provisioner "local-exec" {
         command = <<EOT
         gcloud builds submit --region=${var.region} --project=${var.project_id} --tag=${local.image_name} ./modules/metabase
     sleep 10
     EOT
       }
   }

resource "google_cloud_run_service_iam_member" "invoker" {
  location = var.region
  project  = var.project_id
  service  = google_cloud_run_v2_service.metabase.name
  role     = "roles/run.invoker"
  member   = "allUsers"  
}

resource "google_cloud_run_v2_service" "metabase" {
  name     = var.job_name_metabase
  location = var.region
  deletion_protection = false
  project  = var.project_id
  template {
    containers {
      image = local.image_name

      resources {
        limits = {
            memory = "2Gi"
        }
      }
      

      env {
        name  = "MB_DB_TYPE"
        value = var.mb_db_type
      }

       env {
         name  = "MB_DB_DBNAME"
         value = var.mb_db_dbname
       }

       env {
         name  = "MB_DB_USER"
         value = var.mb_db_user
       }

       env {
         name  = "MB_DB_PASS"
         value = var.mb_db_pass
       }

        env {
          name  = "MB_DB_PORT"
          value = var.mb_db_port
        }

        env {
          name = "MB_SQL_INSTANCE"
         value = var.mb_sql_instance
        }


      

      ports {
        container_port = 8080
      }

       volume_mounts {
        mount_path = "/cloudsql"
        name       = "cloudsql"
      }

      

      

    }
      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [var.mb_sql_instance]
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

#  output "build_resource" {
#    description = "Recurso que construye y sube la imagen Docker"
#    value       = null_resource.build_push_image
#  }