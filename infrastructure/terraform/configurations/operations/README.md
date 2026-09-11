# Ops Project

This document outlines the manual steps required to re-create the Ops project such that its configuration can be successfully applied with a `terraform apply`.

## Initial Project Creation

1. Create a folder in the organization for projects.
1. Create an "operations" project in the folder.
1. Create a Cloud Storage bucket called `[project]--terraform-state`, where [project] is the name of the operations project.
   - Ensure it has 7 versions of object versioning.

## Terraform Service Account Setup

1. Create a service account in the operations project named `terraform`.
1. Give the terraform service account the following IAM roles:
   - At the folder level:
     - Folder Admin
     - Project Creator
     - Project Deleter
     - Project IAM Admin
     - Compute Shared VPC Admin
   - At the project level:
     - Owner
1. Add the Terraform service account as a Billing Account Administrator on the operations project.
1. Grant the Terraform service account `Service Account Token Creator` on itself.
1. For any users that need to execute commands as the Terraform service account, grant them the Service Account Token Creator role on the Terraform service account.
   - This permission should be removed as soon as setup is complete, as users should not ordinarily be able to act as Terraform.

## Enable APIs

Some APIs are required to be enabled in the Ops project via the console in order for a terraform apply to be successful:

- artifactregistry.googleapis.com
- cloudbilling.googleapis.com
- cloudresourcemanager.googleapis.com
- compute.googleapis.com
- domains.googleapis.com
- dns.googleapis.com
- iam.googleapis.com
- iamcredentials.googleapis.com
- identitytoolkit.googleapis.com
- secretmanager.googleapis.com
- servicenetworking.googleapis.com
