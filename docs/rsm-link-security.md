# RSM Link security

RSM Link 1.0 has **no authentication and no encryption**. CRC32C is corruption detection, not authentication, integrity against an attacker, or encryption. Use only loopback or a trusted isolated network. The node defaults to `127.0.0.1` and emits a visible warning for an explicitly selected non-loopback address.

Writes and forces are dangerous engineering operations and need authorization before remote deployment. Implementations bound frames, clients, queues, images, chunks, transfers, manifests, snapshots, and outgoing updates. Invalid frames close a session; stale generations reject mutation. Clients cannot provide filesystem paths, execute shells, or dynamically load code. A future release may layer RSM Link over TLS or another authenticated secure channel; it must not invent custom encryption.
