# Logix-inspired compatibility subset

This is a defined RSmicro subset; full Studio 5000, Allen-Bradley, Rockwell, or Logix compatibility is not claimed. Hardware runtime implementation is Task 3, and conformance is incomplete until that C runtime passes the language-neutral fixtures. Official 1756-RM003 metadata and interpretation notes accompany every instruction.

|Instruction|Supported|Opcode|Types|Lifecycle|Fixtures|Known limitation|
|---|---|---:|---|---|---|---|
|XIC|Yes|1|Profile-defined|Yes|Yes|C runtime pending|
|XIO|Yes|2|Profile-defined|Yes|Yes|C runtime pending|
|OTE|Yes|3|Profile-defined|Yes|Yes|C runtime pending|
|OTL|Yes|4|Profile-defined|Yes|Yes|C runtime pending|
|OTU|Yes|5|Profile-defined|Yes|Yes|C runtime pending|
|ONS|Yes|6|Profile-defined|Yes|Yes|C runtime pending|
|TON|Yes|16|Profile-defined|Yes|Yes|C runtime pending|
|CTU|Yes|17|Profile-defined|Yes|Yes|C runtime pending|
|CTD|Yes|18|Profile-defined|Yes|Yes|C runtime pending|
|RES|Yes|19|Profile-defined|Yes|Yes|C runtime pending|
|EQ|Yes|32|Profile-defined|Yes|Yes|C runtime pending|
|NE|Yes|33|Profile-defined|Yes|Yes|C runtime pending|
|GT|Yes|34|Profile-defined|Yes|Yes|C runtime pending|
|GE|Yes|35|Profile-defined|Yes|Yes|C runtime pending|
|LT|Yes|36|Profile-defined|Yes|Yes|C runtime pending|
|LE|Yes|37|Profile-defined|Yes|Yes|C runtime pending|
|MOV|Yes|48|Profile-defined|Yes|Yes|C runtime pending|
|CLR|Yes|49|Profile-defined|Yes|Yes|C runtime pending|
|ADD|Yes|50|Profile-defined|Yes|Yes|C runtime pending|
|SUB|Yes|51|Profile-defined|Yes|Yes|C runtime pending|
|MUL|Yes|52|Profile-defined|Yes|Yes|C runtime pending|
|DIV|Yes|53|Profile-defined|Yes|Yes|C runtime pending|
|NEG|Yes|54|Profile-defined|Yes|Yes|C runtime pending|
|ABS|Yes|55|Profile-defined|Yes|Yes|C runtime pending|

## C99 core status

All 24 CORE-1 mnemonics are dispatched by the C runtime with fixed-width numeric checks, per-instruction state, monotonic TON timing, and force overlays. Unit and fixture-catalogue checks cover the complete opcode registry. Parallel source branches remain represented by Task 2's deterministic flattened stream; richer branch merge bytecode is a known future image evolution. Full Studio 5000 compatibility, physical target validation, and safety certification are not claimed.
