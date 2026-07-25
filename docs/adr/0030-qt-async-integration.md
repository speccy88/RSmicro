# ADR 0030: Qt asynchronous integration

**Decision:** use dedicated workers. GUI-neutral services run through `QThreadPool` tasks; long-lived asyncio controller and broker clients own an event loop in a dedicated worker thread. Only immutable results/errors cross into Qt through queued signals. Native runtime instances have one owning worker and are never called concurrently. Shutdown cancels work, closes clients with finite timeouts, stops loops, then joins workers. Tests inject synchronous fakes and assert completion/error signals without sockets or modal UI.
