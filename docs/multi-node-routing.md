# Multi-node routing

Routing is broker-mediated, not direct controller-to-controller. Safe ladder logic must require the consumed value AND quality-good AND NOT stale. On loss the order is quality-good false, stale true, then consumed false, so every intermediate state is safe. On recovery the value is written before stale false and quality-good true. Hard real-time behavior and physical hardware validation are not claimed.
