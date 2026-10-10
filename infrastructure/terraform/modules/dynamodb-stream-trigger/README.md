# DynamoDB Stream Trigger

The change-feed counterpart of the Eventarc Firestore trigger. An EventBridge pipe reads the table's
stream, keeps only the records whose partition key belongs to this service's collection, and puts
them on a queue the service's trigger pool polls.

Two differences follow from the AWS model. There is one stream for the whole table rather than one
trigger per collection, so the collection filter lives in the pipe rather than in the trigger's own
subscription. And a stream record is not an event envelope: the pipe delivers the raw `NewImage` and
`OldImage`, so the trigger handler reads DynamoDB shapes where its GCP counterpart reads a Firestore
document.
