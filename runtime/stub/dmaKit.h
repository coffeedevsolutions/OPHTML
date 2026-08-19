/* Shim so the sample's <dmaKit.h> resolves under `make syntax-check`.
 * The console build gets the real header from PS2SDK; -Istub only
 * ever precedes it on the host, where there is no PS2SDK at all. */
#include "dmakit_stub.h"
