resource "google_sql_database_instance" "postgres" {
  name             = "clinic-postgres"
  region           = var.region
  database_version = "POSTGRES_15"
  settings {
    tier            = "db-f1-micro" 
    availability_type = "ZONAL"
    disk_size       = 100 # GB
    # deletion_protection = false

    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "public-access"
        value = "0.0.0.0/0"
      }
    }
  }
  lifecycle {
    prevent_destroy = false
  }

  deletion_protection = false
}

resource "google_sql_user" "postgres_user" {
  name     = "postgres"
  instance = google_sql_database_instance.postgres.name
  password = "postgres"

  lifecycle {
  prevent_destroy = true
  }

  depends_on = [google_sql_database_instance.postgres]
}

resource "google_sql_database" "clinics_db" {
  name     = "clinics"
  instance = google_sql_database_instance.postgres.name

  depends_on = [google_sql_database_instance.postgres]
}

resource "google_sql_database" "metabase" {
  name     = "metabase"
  instance = google_sql_database_instance.postgres.name

  depends_on = [google_sql_database_instance.postgres]
}


resource "google_bigquery_dataset" "dataset" {
  dataset_id = "patients_dataset"
  location = var.region
  project = var.project_id
}

resource "google_bigquery_table" "table" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id = "patients_table"
  project = var.project_id
  deletion_protection = false
}

resource "google_firestore_database" "database" {
  project = var.project_id
  name = "(default)"
  location_id = var.region
  type = "FIRESTORE_NATIVE"
  deletion_policy = "DELETE"
}