# ADR 0031: Qt Graphics ladder editor

Ladder source remains canonical model data. QGraphicsScene items render rails, wires, rungs and structured instruction boxes. QUndoCommand owns source edits. Rendering never evaluates ladder semantics; online state is supplied by rsmcore or RSM Link.
