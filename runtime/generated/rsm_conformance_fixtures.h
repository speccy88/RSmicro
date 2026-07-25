#ifndef RSM_CONFORMANCE_FIXTURES_H
#define RSM_CONFORMANCE_FIXTURES_H
#include <stddef.h>
typedef struct {const char *instruction; const char *source;} rsm_conformance_fixture_t;
extern const rsm_conformance_fixture_t rsm_conformance_fixtures[];
extern const size_t rsm_conformance_fixture_count;
#endif
