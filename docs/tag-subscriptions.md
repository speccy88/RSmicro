# Tag subscriptions

Sessions may request all tags or bounded ID/UUID sets with initial values, force/quality fields, numeric deadband, and minimum interval. Updates are change-driven and sequence numbered. Outgoing queues are bounded and may coalesce superseded tag updates, but never silently discard request responses. An overrun requires resynchronization. Program activation invalidates subscriptions and runtime-ID mappings; clients explicitly retrieve the new manifest and resubscribe.
