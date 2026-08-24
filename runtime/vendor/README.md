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

To update: copy the same files from a newer gsKit checkout, update the
commit hash above, and let `make -C runtime test` say what changed.
