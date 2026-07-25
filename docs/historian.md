# SQLite historian

Schema version 1 uses WAL, foreign keys, a busy timeout, migrations, typed nullable BOOL/DINT/REAL columns, and normalized tag member series. Sampling policy supports ON_CHANGE, PERIODIC and ON_CHANGE_WITH_HEARTBEAT with absolute/percentage deadband, minimum/maximum intervals, quality and force transitions. A bounded async queue and batched transactions isolate controller reads from disk. Queries require time bounds and cap raw points at 10,000. Retention deletes by age; vacuum is manual. Back up SQLite using its backup API or a WAL-aware procedure.
