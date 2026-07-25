cmake_minimum_required(VERSION 3.16)
project(RSmicroCompilerNativeHarness LANGUAGES C)

foreach(required RSMICRO_SOURCE_DIR RSM_HARNESS_SOURCE RSM_IMAGE)
  if(NOT DEFINED ${required} OR "${${required}}" STREQUAL "")
    message(FATAL_ERROR "${required} is required")
  endif()
endforeach()

# This is intentionally a small consumer project: CMake selects the compiler,
# archive/import library, system libraries, executable suffix, and test runner.
# It is the canonical compiler-to-native harness, not a Unix-only subprocess.
set(RSM_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(RSM_BUILD_SHARED OFF CACHE BOOL "" FORCE)
set(RSM_BUILD_NODE OFF CACHE BOOL "" FORCE)
add_subdirectory("${RSMICRO_SOURCE_DIR}" rsmicro)

add_executable(canonical_native_harness "${RSM_HARNESS_SOURCE}")
target_link_libraries(canonical_native_harness PRIVATE rsmcore)
target_compile_features(canonical_native_harness PRIVATE c_std_99)
rsm_enable_strict_warnings(canonical_native_harness)

add_test(NAME canonical_native_harness COMMAND canonical_native_harness "${RSM_IMAGE}")
