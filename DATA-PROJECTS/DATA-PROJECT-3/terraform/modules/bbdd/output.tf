output "db_host" {
  description = "IP o connection name de la instancia Postgres"
  value       = google_sql_database_instance.postgres.ip_address[0].ip_address
}

