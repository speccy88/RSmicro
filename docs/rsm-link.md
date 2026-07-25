# RSM Link 1.0

RSM Link is the bounded binary engineering protocol between a compiler/client and an autonomous controller node. It does not contain ladder semantics. Versions are protocol 1.0, frame 1, and schema 1; a major mismatch is fatal while optional minor additions require capability negotiation.

Frames are little-endian: `RSML` magic (4), frame version (1), protocol major/minor (1 each), header flags (1), message type (2), message flags (2), request ID (4), sequence (4), payload length (4), payload, and CRC32C (4). CRC covers header and payload and detects corruption only. Minimum size is 28 bytes, maximum is 1 MiB, and maximum payload is 1,048,548 bytes. There are no alignment assumptions and decoders read individual fields safely.

Payloads use a deterministic length-delimited binary field map, never native structure dumps or Python serialization. Request IDs correlate responses; sequence numbers order events. Unknown required messages fail, while explicitly optional messages may be ignored. A malformed frame, invalid CRC, impossible length, or partial close terminates the session; decoders do not scan indefinitely for magic.

The schema enumerates connection, program transfer, mode, manifest, typed tag, simulation input, force, subscription, snapshot, diagnostics, heartbeat, ACK and ERROR messages. Runtime tag IDs are compact session identifiers; clients must cache stable tag UUIDs and invalidate IDs whenever program hash/generation changes.

RSM Link is transport-independent. TCP handling belongs to the node/client, not `rsmcore`. SCADA, historian, alarms, Studio, routing, and physical hardware support are future work.
