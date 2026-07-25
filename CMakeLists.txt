cmake_minimum_required(VERSION 3.16)
project(RSmicro LANGUAGES C)
include(CTest)
option(RSM_BUILD_TESTS "Build runtime tests" ON)
option(RSM_BUILD_SHARED "Build shared core" ON)
option(RSM_BUILD_NODE "Build the POSIX RSM Link node runtime" ON)
option(RSM_ENABLE_STRICT_WARNINGS "Enable strict warnings" ON)
option(RSM_ENABLE_SANITIZERS "Enable address/undefined sanitizers" OFF)

# Keep warning policy target-local and compiler-aware.  MSVC does not accept
# GCC/Clang warning switches, and consumers may use another C compiler.
function(rsm_enable_strict_warnings target)
  if(NOT RSM_ENABLE_STRICT_WARNINGS)
    return()
  endif()
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /WX)
  elseif(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang|AppleClang")
    target_compile_options(${target} PRIVATE
      -Wall -Wextra -Werror -Wpedantic -Wshadow -Wconversion
      -Wsign-conversion -Wstrict-prototypes -Wmissing-prototypes)
  endif()
endfunction()

if(RSM_ENABLE_SANITIZERS AND CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
  add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
  add_link_options(-fsanitize=address,undefined)
endif()
add_subdirectory(protocol)
add_subdirectory(runtime)
