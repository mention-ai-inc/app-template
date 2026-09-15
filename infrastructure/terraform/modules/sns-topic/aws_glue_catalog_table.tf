resource "aws_glue_catalog_table" "analytics" {
  count = var.analytics_subscriber ? 1 : 0

  name          = local.table_name
  database_name = var.glue_database_name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification = "json"
    "projection.enabled" : "true"
    "projection.publish_date.type" : "date",
    "projection.publish_date.format" : "yyyy-MM-dd",
    "projection.publish_date.range" : "2024-01-01,NOW",
    "projection.publish_date.interval" : "1",
    "projection.publish_date.interval.unit" : "DAYS",
    "storage.location.template" : "s3://${replace(var.archive_bucket_arn, "arn:aws:s3:::", "")}/${local.archive_prefix}publish_date=$${publish_date}/"
  }

  partition_keys {
    name = "publish_date"
    type = "string"
  }

  storage_descriptor {
    location      = "s3://${replace(var.archive_bucket_arn, "arn:aws:s3:::", "")}/${local.archive_prefix}"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.openx.data.jsonserde.JsonSerDe"
    }

    columns {
      name = "messageid"
      type = "string"
    }

    columns {
      name = "timestamp"
      type = "string"
    }

    columns {
      name = "topicarn"
      type = "string"
    }

    columns {
      name = "messageattributes"
      type = "string"
    }

    columns {
      name = "message"
      type = "string"
    }
  }
}
