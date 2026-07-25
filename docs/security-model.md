# Security model

RSM Link 1.0 provides no authentication or encryption, and its CRC detects corruption rather than authenticating a peer. Broker roles are convenience authorization, not secure identity. Services bind to loopback by default; remote use requires an isolated trusted network today and TLS plus authenticated, authorized identities in a future protocol revision. Screen documents are declarative JSON and cannot execute scripts. Examples contain no credentials.
