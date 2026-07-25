# RSmicro Studio

Install the desktop extra dependencies and run `rsmicro-studio [project.rsmproj]`. Studio provides the project tree, structured ladder graphics, docked diagnostics/online views, undo/redo, atomic project lifecycle and recovery autosaves. Compiler, native simulation and network operations are services rather than ladder semantics in widgets. Offline editing remains available when rsmcore is absent. Use `--verify --offscreen` for bounded CI startup. The legacy `plc-ascii` Tkinter IDE remains supported during migration.

Studio is engineering software, not safety software. Current Task 7 limitations include basic property editing and no physical-hardware validation; Task 8 owns final integrated validation and polish.
