# Project

This module wraps [terraform-google-modules/project-factory/google](https://registry.terraform.io/modules/terraform-google-modules/project-factory/google/latest/submodules/project_services).

## Purpose

The purpose of wrapping this module is to:

- Lock the version of the module being used across project configurations.
- Globally define the pattern of appending random characters to project IDs to create globally-unique projects without relying on naming conventions that invoke the name of our company.

## Resources

The resources of this module are equivalent to the resources of `terraform-google-modules/project-factory/google`.
