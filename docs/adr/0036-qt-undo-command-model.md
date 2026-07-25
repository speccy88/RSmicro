# ADR 0036: Undo model

Offline edits use QUndoStack/QUndoCommand and preserve UUIDs. External writes, downloads, forces, modes and alarm acknowledgements are intentionally never undo commands.
