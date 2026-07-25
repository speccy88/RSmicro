# ADR: Force overlay model

**Status:** Accepted

## Decision

Forces change effective reads and outputs without replacing underlying values.

## Consequences

The rule is testable on hosted and freestanding-like C99 targets and keeps platform policy outside the instruction engine.
