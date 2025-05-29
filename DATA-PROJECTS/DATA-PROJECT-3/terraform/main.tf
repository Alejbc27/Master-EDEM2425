module "appointment_api" {
    source = "./modules/appointment_api"
    db_host = module.postgres.db_host
    project_id = var.project_id
    region = var.region

    depends_on = [module.postgres, module.data_generator_clinic.build_resource]
}

module "postgres" {
    source = "./modules/bbdd"
    region = var.region
    project_id = var.project_id
}

output "postgres_ip" {
  description = "IP pública de la instancia Postgres"
  value       = module.postgres.db_host
}


module "data_generator_clinic" {
    source = "./modules/data_generator_clinic"
    db_host = module.postgres.db_host
    project_id = var.project_id
    region = var.region

    depends_on = [module.postgres]
}

module "vector_database_api" {
    source = "./modules/vector_database_api"
    db_host = module.postgres.db_host
    project_id = var.project_id
    region = var.region

    depends_on = [module.postgres, module.data_generator_clinic.build_resource, module.appointment_api.build_resource]
}

module "articles_loader" {
    source = "./modules/articles_loader"
    project_id = var.project_id
    region = var.region

    depends_on = [module.data_generator_clinic.build_resource, module.appointment_api.build_resource, module.vector_database_api.build_resource]
}

module "cloud_functions" {
    source = "./modules/cloud_functions"
    project_id = var.project_id
    region = var.region
    db_host = module.postgres.db_host

    depends_on = [module.postgres]
}

module "metabase" {
    source = "./modules/metabase"
    project_id = var.project_id
    region = var.region

    depends_on = [module.postgres,module.data_generator_clinic.build_resource, module.appointment_api.build_resource, module.vector_database_api.build_resource, module.articles_loader.build_resource]
}