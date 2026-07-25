# Logix-inspired compatibility subset

This is a defined RSmicro subset; full Studio 5000, Allen-Bradley, Rockwell, or Logix compatibility is not claimed. The C99 runtime is the semantic authority and executes the language-neutral conformance fixtures. Instruction metadata links each mnemonic to the official Rockwell Automation *Logix 5000 Controllers General Instructions Reference* (publication 1756-RM003) source location; those references are explanatory inputs, not a claim of product certification.

|Instruction|Supported|Opcode|Types|Lifecycle|C fixture execution|
|---|---:|---:|---|---|---|
|XIC, XIO, OTE, OTL, OTU, ONS|Yes|1–6|Profile-defined|Yes|Yes|
|TON, CTU, CTD, RES|Yes|16–19|Profile-defined|Yes|Yes|
|EQ, NE, GT, GE, LT, LE|Yes|32–37|Profile-defined|Yes|Yes|
|MOV, CLR, ADD, SUB, MUL, DIV, NEG, ABS|Yes|48–55|Profile-defined|Yes|Yes|

## Lifecycle and branch semantics

Entering RUN/TEST from PROGRAM performs an explicit prescan; leaving RUN/TEST for PROGRAM performs postscan. Prescan de-energizes OTE destinations, initializes transition state, and sets ONS storage so an already-true rung does not generate a false startup one-shot. Postscan de-energizes OTE and clears non-retentive timing enable/timing state. ONS storage is instruction state associated with the compiled source instruction; legacy storage representations are not an alternate runtime semantic path. TON reads the monotonic clock; CTU/CTD are transition instructions; RES resets defined accumulated/status members while preserving PRE; CLR is scalar-only.

Parallel branches are encoded as explicit begin/lane/end bytecode and merge lane continuity deterministically. Conformance cases execute pre/post series logic, two/three lanes, A/B/neither, false input, nested lanes, and outputs in branch paths through C. Forces are effective-value overlays and snapshots are observational.

## Scope

All 24 CORE-1 mnemonics are dispatched by the C runtime with fixed-width numeric checks, per-instruction state, monotonic TON timing, and force overlays. The canonical compiler E2E builds a Project into an `.rsm`, checks debug/rung ID mappings and stripped-debug behavior, then loads/scans the image with a fresh C build. Full Studio 5000 compatibility, physical target validation, and safety certification are not claimed.
