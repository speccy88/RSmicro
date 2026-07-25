# ADR 0012: Native library discovery

Accepted. Search deterministically: explicit argument, `RSMICRO_CORE_LIBRARY`, repository build, package `native/lib`, then the OS loader. Existing concrete files win; a loaded library must pass ABI/profile/export checks. Names are `librsmcore.so`, `librsmcore.dylib`, and `rsmcore.dll`.
