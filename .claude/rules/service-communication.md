## Services never call each other synchronously

Synchronous service-to-service communication is banned. No service may call another service's REST endpoints, gRPC methods, or any other request/response interface, and no service may import another service's package or client. This includes calls made with `httpx`, `requests`, `aiohttp`, a generated API client, or a hand-rolled HTTP wrapper, whether from a use case, an application service, an infrastructure service, a listener, an executor, a job, or a route.

The rule is unconditional. It applies even when the caller "only needs one value," when the other service "already has the endpoint," when the call would be "fast," or when the alternative means adding a new event, command, or read model. If you find yourself constructing a URL that points at another service, stop and pick one of the shapes below.

Services communicate in exactly two ways:

- **Commands** tell another service to do something. The caller saves a `CommandPayload` through `ICommandDispatcher`; the outbox dispatches it to the owning service's executor, and the outcome comes back as an `AcknowledgeCommandResult` event, never as a return value.
- **Events** tell everyone that something happened. The publisher saves an `EventPayload` through `IEventPublisher`; interested services consume it in a listener and update their own state.

Both payload types live in `library/library/domain/commands/` and `library/library/domain/events/`, and both are saved inside the same unit of work as the aggregate change that caused them, so they are delivered if and only if the change commits.

### Why

- A synchronous call couples two services' availability, latency, and deploy order. One slow or failing service takes the caller down with it, and the failure lands inside a transaction that then aborts.
- Commands and events go through the outbox, so they are durable, retried, and delivered exactly when the causing change commits. A REST call made mid-transaction is none of those things: the transaction can still fail after the remote side effect has happened.
- The service boundary is the ownership boundary. A service that reads another service's data over REST is reading a model it does not own and cannot version, migrate, or test against.

### What to do instead

| You want to | Do this |
| --- | --- |
| Make another service do something | Save a command through `ICommandDispatcher`; the owning service handles it in an executor. |
| Know that something happened elsewhere | Consume that service's event in a listener. |
| Read data another service owns | Consume its events into a read model in your own service, and query that. If no event carries the data, add one to the publishing service. |
| Return a result to the caller of a command | There is no return value. Publish an event from the handling service and listen for it. |
| Get user or organization data | `IUsersClient` is the identity provider, not a service, and is allowed. |
| Call a third-party API (LLM, storage, identity, payments) | An infrastructure service under `infrastructure/services/<name>/`. Third parties are not services and are not covered by this rule. |

Web, mobile, and MCP surfaces call service REST routes; that is client-to-service traffic and is expected. The ban is on one service calling another.

### Red flags

- `httpx`, `requests`, or `aiohttp` imported anywhere under `services/<svc>/` outside an `infrastructure/services/<name>/` third-party client. **Never correct.**
- A URL, host, or environment variable naming another service (`NOTES_SERVICE_URL`, `http://users-service`, an `x-invoking-service` header set by hand).
- A dependency in `presentation/dependencies/` that builds a client for another service.
- An `import` of another service's package (`from users_service...` inside `notes_service`).
- A use case that awaits a remote result before it can finish, when a command plus a later listener would express the same flow.
- A new REST route whose only consumer is another service. That route should be an executor, and its caller should dispatch a command.
