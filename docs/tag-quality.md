# Tag quality

Quality severity is GOOD < UNCERTAIN < STALE < BAD and includes reason, UTC timestamp, source and optional message. Reasons cover live, forced, substituted, initialization, program changes, hold-last, configuration/type/controller/write/manifest failures, and controller/tag/consumed staleness. Loss retains the last value and changes quality; presence of a numeric value never implies GOOD.
