# Headless SCADA services

`rsmicro-tagd` supervises RSM Link controllers, generation-scopes manifests, owns the live UUID registry, and fans changes to bounded historian and local API paths. It never executes ladder logic or accesses the native runtime binding. Health progresses STARTING, HEALTHY/DEGRADED/UNHEALTHY, STOPPING, STOPPED. Shutdown closes the API and controllers before flushing SQLite.
