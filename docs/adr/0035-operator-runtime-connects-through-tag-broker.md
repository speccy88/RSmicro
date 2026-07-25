# ADR 0035: Operator data path

RSmicro SCADA connects exclusively to loopback rsmicro-tagd for values, writes, alarms and history. It never connects to rsm-node or SQLite directly.
