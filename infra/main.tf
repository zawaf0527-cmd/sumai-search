terraform {
  required_providers {
    google = { source = "hashicorp/google" }
  }
}

variable "project_id" {}
variable "region" { default = "asia-northeast1" }

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "apis" {
  for_each           = toset(["bigquery.googleapis.com", "storage.googleapis.com"])
  service            = each.key
  disable_on_destroy = false
}

resource "google_storage_bucket" "raw" {
  name                        = "${var.project_id}-raw"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  depends_on                  = [google_project_service.apis]
}

resource "google_bigquery_dataset" "layers" {
  for_each   = toset(["raw", "stg", "marts"])
  dataset_id = each.key
  location   = var.region
  depends_on = [google_project_service.apis]
}