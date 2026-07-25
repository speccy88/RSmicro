# SCADA security

The local API has no secure authentication or encryption. Client-selected roles are policy hints, not identity. Keep it loopback-only or behind a future authenticated secure layer. Operator writes and engineering forces carry different risk. Requests cannot choose files or execute shells. RSmicro is not safety-rated.
