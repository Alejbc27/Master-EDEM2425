resource "google_storage_bucket" "bucket" {
  name     = "etl-fs-to-bq-dp3" 
  location = var.region
  force_destroy = true
}

resource "google_storage_bucket_object" "source_zip" {
  name   = "firestore-to-bq-etl.zip"         
  bucket = google_storage_bucket.bucket.name
  source = "${path.module}/cloud_function.zip"    
}


resource "google_service_account" "account" {
  account_id   = "cloud-functions-dp3-sa"          
  display_name = "Service Account de cloud-functions-dp3-sa"
}

resource "google_cloudfunctions2_function" "firestore_to_bq" {
  name     = "firestore-sql-to-bq-etl"
  location = var.region

  build_config {
    runtime     = "python310"
    entry_point = "firestore_sql_to_bq"

    source {
      storage_source {
        bucket = google_storage_bucket.bucket.name
        object = google_storage_bucket_object.source_zip.name
      }
    }
  }

  service_config {
    ingress_settings    = "ALLOW_ALL"
    available_memory    = "256M"
    timeout_seconds     = 300

    environment_variables = {
      FIRESTORE_COLLECTION = var.firestore_collection
      BQ_PROJECT           = var.project_id
      BQ_DATASET           = var.bq_dataset
      BQ_TABLE             = var.bq_table
      DB_HOST            = var.db_host
      DB_USER            = var.db_user
      DB_NAME            = var.db_name
      DB_PASSWORD        = var.db_password
    }
  }
}

# Ya tienes este binding para tu service account; mantenlo si lo necesitas:
resource "google_cloudfunctions2_function_iam_member" "invoker" {
  project        = var.project_id
  location       = google_cloudfunctions2_function.firestore_to_bq.location
  cloud_function = google_cloudfunctions2_function.firestore_to_bq.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.account.email}"
}

# Añade este para permitir a cualquiera invocar tu función (public):
resource "google_cloudfunctions2_function_iam_member" "invoker_public" {
  project        = var.project_id
  location       = google_cloudfunctions2_function.firestore_to_bq.location
  cloud_function = google_cloudfunctions2_function.firestore_to_bq.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

# Y lo mismo para el IAM de Cloud Run (que también protege tu función v2):
resource "google_cloud_run_service_iam_member" "cloud_run_invoker" {
  project  = var.project_id
  location = google_cloudfunctions2_function.firestore_to_bq.location
  service  = google_cloudfunctions2_function.firestore_to_bq.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.account.email}"
}

resource "google_cloud_run_service_iam_member" "cloud_run_invoker_public" {
  project  = var.project_id
  location = google_cloudfunctions2_function.firestore_to_bq.location
  service  = google_cloudfunctions2_function.firestore_to_bq.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_scheduler_job" "invoke_cloud_function" {
  name        = "invoke-gcf-function"
  description = "Schedule the HTTPS trigger for cloud function"
  schedule = "0 */4 * * *"
    time_zone = "Europe/Madrid"
  project     = var.project_id
  region      = google_cloudfunctions2_function.firestore_to_bq.location

  http_target {
    uri         = google_cloudfunctions2_function.firestore_to_bq.service_config[0].uri
    http_method = "GET"
    oidc_token {
      audience              = "${google_cloudfunctions2_function.firestore_to_bq.service_config[0].uri}/"
      service_account_email = google_service_account.account.email
    }
  }
}