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
- **Whether an API is permitted at all.** This one is not a subtlety
  and it has already cost a build: **the shims make the host
  *compile*, not *conform*.** A shim describes an API; the container
  is the only thing that knows whether PS2SDK actually offers it, on
  what terms, and whether the port forbids it outright.

  Demonstrated rather than argued. The streaming bench first read its
  covers with `fioOpen`/`fioRead`/`fioClose`, and a
  `host-shim/fileio.h` declaring those three made `make syntax-check`
  green. ps2sdk's newlib port rejects them at the header:

  ```
  #error "Using fio/fileXio functions directly in the newlib port
          will lead to problems."
  #error "Use posix function calls instead."
  ```

  So `covers.elf` had never compiled for a target while every local
  suite passed. The shim did not merely fail to catch the problem — it
  *converted a build error into a green tick*, on the one check whose
  whole job is catching console-only breakage before a bench sitting.
  A shim for an API the target forbids is worse than no shim at all.

  It was deleted rather than corrected: `open`/`read`/`close` from
  `<fcntl.h>` and `<unistd.h>` exist for real on both sides, so the
  two now compile the same three functions instead of one side
  compiling a description of them.

  **Before adding a shim, ask whether the real header exists on the
  host.** If it does, use it. If it does not, the shim buys a host
  compile and nothing more, and `hw.yml`'s `elf` job stays the only
  thing that vouches for the console build.

  The two shims that remain are lower-risk than `fileio.h` was and are
  kept on that basis: `tamtypes.h` is types, and `kernel.h` declares
  `SyncDCache`/`FlushCache`, which gsKit itself calls — neither is an
  API the port refuses. They are still descriptions, and the container
  is still the arbiter.

Known upstream wart, vendored as-is: the doc comment near
`gsInit.h:884` still recommends `gsKit_init_global(GS_MODE_NTSC)`;
the macro at `gsInit.h:1134` takes no arguments. Headers stay
verbatim, so it is noted here instead of edited there.

To update: copy the same files from a newer gsKit checkout, update the
commit hash above, and let `make -C runtime test` say what changed —
the eight pinned `gsKit_texture_size` values in `test_runtime.c` are
the tripwire for silent changes to the arithmetic.
