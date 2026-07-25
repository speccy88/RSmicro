# ADR: Monotonic timer time

**Status:** Accepted

## Decision

TON accumulation uses unsigned differences of HAL monotonic microseconds.

## Consequences

The rule is testable on hosted and freestanding-like C99 targets and keeps platform policy outside the instruction engine.
