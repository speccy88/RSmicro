# RSmicro project format v1

Canonical files use UTF-8 JSON, format `rsmicro-project`, version 1, and UUID identity. Editable names are never identity. A project owns target-neutral controllers and separate deployments, plus SCADA screens, alarm definitions, historian placeholders, and extension metadata.

Controllers contain typed tags (`BOOL`, `DINT`, `REAL`, `TIMER`, `COUNTER`), programs, routines, ordered rungs, and a deterministic cyclic-task program order. Logic is an explicit tree of instruction nodes and branch nodes; branch lanes may contain nested branches. Operands are literals, UUID tag references, or UUID tag/member references. Composite member spelling is uppercase (`PRE`, `ACC`, timer `EN/TT/DN`, and counter `CU/CD/DN/OV/UN`). Produced tags identify a source tag. Consumed tags identify the destination, remote controller and produced tag, timing, stale-value, substitution, and quality policies.

Deployments identify a target platform and controller and contain drivers/devices, typed directional endpoints, addresses, safe values, polarity and quality placeholders, and UUID tag-to-endpoint bindings. Thus logical source contains no board pins or serial paths.

Serialization has fixed field order, two-space indentation, a final newline, no generated timestamps, and atomic replacement. Semantic list order is preserved. Schemas using JSON Schema draft 2020-12 live in `schemas/*.schema.json`; installed copies are resources in `rsmicro.schemas`.

## Compilation profile

Controllers may select `RSM-LOGIX-CORE-1`. Compiler operands resolve tag UUIDs, composite members serialize uppercase, and aliases are diagnosed before canonical GE/LE lowering. The source project remains JSON; deployed execution input is the bounded binary RSM1 image.
