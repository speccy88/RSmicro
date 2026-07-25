# Produced and consumed tags

Routes use stable UUIDs and propagate source quality. Cyclic graphs are rejected. Policies are HOLD_LAST_UNCERTAIN, HOLD_LAST_STALE, SUBSTITUTE and BAD_NO_WRITE; control routes require an explicit policy. Timeout SUBSTITUTE writes quality-good false, stale true, optional bad state, then the safe substitute value through RSM Link. Writes share a group UUID but are not atomic; partial failure makes the route bad. Recovery waits for synchronized manifests and a fresh source update.
