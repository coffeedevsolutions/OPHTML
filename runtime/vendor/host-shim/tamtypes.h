/* Host stand-in for PS2SDK's <tamtypes.h> -- just the fixed-width
 * aliases the vendored gsKit headers use. The real header refuses to
 * compile off-target (#error unless _EE/_IOP); these typedefs match
 * the EE's LP64-visible widths so struct layouts agree in the fields'
 * meanings, though not necessarily in ABI -- nothing host-side ever
 * crosses an ABI boundary with a console. */
#ifndef TAMTYPES_H
#define TAMTYPES_H

#include <stdint.h>

typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int8_t   s8;
typedef int16_t  s16;
typedef int32_t  s32;
typedef int64_t  s64;
typedef unsigned int u128 __attribute__((mode(TI)));

#endif
