# SCADA screen format

`rsmicro-scada-screen` version 1 is deterministic JSON containing a stable screen UUID, dimensions, scaling, layers and objects. Objects have stable UUID, allow-listed type, geometry, style, stable tag UUID binding, quality behavior and an allow-listed action. No executable code or runtime tag IDs are permitted. Supported widgets are label, boolean indicator, pushbutton, numeric display/input, bar, gauge, bounded trend, alarm banner, connection/force indicators and navigation button.
