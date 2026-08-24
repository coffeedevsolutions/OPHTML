# Vendored gsKit headers

`gsKit/` contains verbatim copies of the public headers from
[ps2dev/gsKit](https://github.com/ps2dev/gsKit) at commit
`43122eb96289167975b56caa45beb71eb8684fa2`
(`ee/gs/include/*.h` and `ee/dma/include/*.h`), licensed under the
Academic Free License version 2.0 — see the notice each file carries.

They exist so the HOST test suite compiles `ps2ui.c` and the sample
against gsKit's real declarations instead of a hand-written stub. The
hand-written model produced two shipped bugs in one day: it declared a
`GSTEXTURE::Function` member gsKit does not have, and it omitted the
`TBW` member gsKit does — and in both cases every host check stayed
green because the stub was the only gsKit the checks could see. With
the real headers on the include path, a struct-shape or prototype
divergence is a compile error, not a bench session.

The console build never sees this directory: PS2SDK ships the same
headers, and only the host Makefiles put `vendor/` on the include path.

`host-shim/` contains two small hand-written headers standing in for
PS2SDK ones the vendored headers or the sample include (`tamtypes.h`,
`kernel.h`). They declare exactly what compiles here and nothing more.

`gsKit/src/gsTexture.c` is likewise verbatim from `ee/gs/src/`. The
host build compiles it with only `-DF_gsKit_texture_size` defined —
gsKit guards every function with a per-function `F_*` macro, so that
yields exactly one function: the real block-based texture-size
arithmetic. It is the one gsKit function whose VALUE the runtime's
VRAM preflight depends on, and the hand-written approximation it
replaces under-counted non-power-of-two widths — the direction that
walks a console into the manager's no-exit allocation loop.

## What this guarantee does and does not cover

A struct-shape or prototype divergence is now a host compile error.
Two classes stay console-only, on purpose:

- **Behaviour.** Headers carry declarations; transcribed behaviour in
  the stub (`vram_alloc` rounding, the TexManager model) is still a
  model, marked as such at each site.
- **Type widths and formats.** `host-shim/tamtypes.h` types `u32` from
  the host's `<stdint.h>`, so `uint32_t` is `unsigned int` here and
  `unsigned long` under newlib on the EE. A `printf` format that is
  wrong only on the EE (the `54c3abb` class) still surfaces only in
  the container's `-Werror=format`.

Known upstream wart, vendored as-is: the doc comment near
`gsInit.h:884` still recommends `gsKit_init_global(GS_MODE_NTSC)`;
the macro at `gsInit.h:1134` takes no arguments. Headers stay
verbatim, so it is noted here instead of edited there.

To update: copy the same files from a newer gsKit checkout, update the
commit hash above, and let `make -C runtime test` say what changed —
the eight pinned `gsKit_texture_size` values in `test_runtime.c` are
the tripwire for silent changes to the arithmetic.
