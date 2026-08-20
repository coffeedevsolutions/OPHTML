/* The slice of dmaKit and kernel.h that runtime/sample/main.c uses,
 * so the sample can be syntax-checked on the host.
 *
 * The sample is the bring-up instrument: it is the ELF that goes on a
 * memory card and the one a bench session depends on. Until this
 * existed, nothing but the ps2dev container in CI ever compiled
 * main.c, so a change to it was a push-and-hope — and the telemetry
 * build shipped `asm volatile`, which strict C99 rejects, without any
 * local check saying so.
 *
 * This stubs declarations only. It never runs; `make syntax-check`
 * compiles with -fsyntax-only. Emulating the DMAC is not the point and
 * would be a second thing to keep true.
 */
#ifndef DMAKIT_STUB_H
#define DMAKIT_STUB_H

#include "gskit_stub.h"   /* u32 / u64 */

/* dmaKit_init's channel-control arguments. Values are irrelevant to a
 * syntax check; the names are what main.c spells. */
#define D_CTRL_RELE_OFF   0
#define D_CTRL_MFD_OFF    0
#define D_CTRL_STS_UNSPEC 0
#define D_CTRL_STD_OFF    0
#define D_CTRL_RCYC_8     0
#define DMA_CHANNEL_GIF   2

void dmaKit_init(u32 rele, u32 mfd, u32 sts, u32 std, u32 rcyc, u32 chans);
void dmaKit_chan_init(u32 chan);

#endif /* DMAKIT_STUB_H */
