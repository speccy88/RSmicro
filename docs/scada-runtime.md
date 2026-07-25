# Standalone SCADA runtime

Run `rsmicro-scada --project PROJECT --screen ID_OR_NAME --host 127.0.0.1 --port 7590`. Viewer is the default role and cannot write; `--no-write` enforces read-only operation. Fullscreen, windowed, kiosk and bounded offscreen verification modes are available. Process data, writes, alarm acknowledgement and trends go only through rsmicro-tagd. GOOD, UNCERTAIN, STALE and BAD are rendered as text as well as visual state; force is independent.

Alarm acknowledgement is not a safety reset. Operator buttons do not replace physical interlocks.
