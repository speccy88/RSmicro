# ADR 0014: Stable UUID mapping

Accepted. Runtime IDs are image-local. UUID/name convenience calls use the compiler debug map only after its manifest image hash is verified. Names must resolve uniquely; missing metadata never causes guessing.
