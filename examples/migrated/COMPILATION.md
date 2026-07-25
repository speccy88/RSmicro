# Migrated example compilation index

`demo_program.rsmproj` uses the mandatory subset but its migrated TON carries the legacy two-operand `(timer, preset)` form; the profile requires PRE in the TIMER tag, so it is diagnosed `RSM-E102`. Other migrated hardware examples retain legacy forms and are validation candidates rather than silently lowered. `examples/compiler_demo/project.rsmproj` is the nontrivial canonical compilation example and includes serial logic, a parallel branch, comparison, arithmetic, TIMER and COUNTER tags.
