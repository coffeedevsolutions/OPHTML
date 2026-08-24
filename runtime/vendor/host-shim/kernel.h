/* Host stand-in for PS2SDK's <kernel.h> -- the two cache syscalls the
 * runtime and the vendored gsKit headers reference. The stub gives
 * SyncDCache a recording body so tests can assert writeback coverage;
 * FlushCache is declared for completeness (gsKit's sources call it,
 * its headers do not). */
#ifndef KERNEL_H
#define KERNEL_H

void SyncDCache(void *start, void *end);
void FlushCache(int operation);

#endif
