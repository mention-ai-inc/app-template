# SNS Topic

One topic per event stream, mirroring the Pub/Sub topics of the GCP estate. Listeners do not
subscribe here directly: `sqs-listener-subscription` creates the queue and the filtered subscription
that connects it.

The two analytics subscribers differ from GCP. Pub/Sub writes straight into BigQuery and straight
into GCS; AWS has no streaming warehouse insert, so both land in S3 through a Kinesis Data Firehose
delivery stream and the "analytics" subscriber is a Glue catalog table over that same location, read
with Athena. Analytics therefore requires the archive; on GCP the two were independent.
