# Ladder editor

The Qt Graphics editor renders rails, serial wires, comments and structured boxes for all instructions present in RSM-LOGIX-CORE-1 metadata (bit, timer/counter, compare, move/math). Canonical branch nodes are retained and may be rendered as parallel/nested paths. Selection edits use undo commands and stable UUIDs. Online overlays must distinguish energized, de-energized, forced, stale/bad, unavailable and fault states without colour alone. Actual execution and trace state always comes from rsmcore/RSM Link.
