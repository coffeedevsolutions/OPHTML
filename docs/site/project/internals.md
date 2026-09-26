---
id: project/internals
title: Internals
description: The repository documents behind this site, the seven testing-failure shapes, and the findings graph that tracks what still holds.
section: project
order: 75
version: 0.10.0
sources: [docs/site/ARCHITECTURE.md, docs/architecture.md, docs/PLAN.md, docs/method.md, docs/findings.md, docs/findings.yaml, docs/bench-phase1.md, docs/bench-phase2.md, docs/bench-runbook.md, docs/bringup.md, docs/design-bringup-3-to-9.md, docs/design-p3b-theming.md, docs/design-v6-resource-model.md, docs/releasing.md, tools/check-findings.py, docs/site/reference/uib-format.md, docs/site/runtime/first-boot.md, docs/site/authoring/theming.md, docs/site/runtime/frame-loop.md]
---

# Internals

The site documents how to use ps2ui. The repository under `docs/` documents
why it is built this way, what has been proven on hardware, and how the
project catches its own mistakes. This page names each of those documents,
who reads which one, and where it lives. Read the linked document itself
for the argument. Nothing here is a copy of it.

## Decisions

[architecture.md](repo:docs/architecture.md#L1) is the scaffolding record:
the three-stage pipeline, the decisions that settle most design questions,
and the bugs found while building, each held down by a regression test.
Read it first, once, to orient to the shape of the codebase. It lives at
`docs/architecture.md`.

[PLAN.md](repo:docs/PLAN.md#L1) is the sequencing authority: the phases,
their gates, and which gate is open. Every gate is a measurement with a
falsifier in `docs/findings.yaml`, not a checkbox. Read it before deciding
what to build next or before asking whether a phase is done. It lives at
`docs/PLAN.md`.

## Method

[method.md](repo:docs/method.md#L1) catalogues the ways a check can pass
without the property it claims holding. The seven shapes it names are:

| shape | name |
|---|---|
| 1 | The guard that skips |
| 2 | The check sourced from what it checks |
| 3 | The instrument blind to its own hypothesis |
| 4 | The fixture where two quantities coincide |
| 5 | The check that never executed |
| 6 | Written down instead of tested |
| 7 | The rule whose coverage is narrower than its purpose |

Read it before writing a test, a lint rule, or a bench instrument in this
repository. It lives at `docs/method.md`.

[findings.md](repo:docs/findings.md#L1) is generated prose; the data is
`docs/findings.yaml`. Each finding names a falsifier, a status, and the
findings it depends on. `tools/check-findings.py` walks that graph: it
refuses a cycle, a confirmed finding that depends on an overturned one, and
a document that cites an overturned finding without marking the citation
`:historical`, then renders `docs/findings.yaml` into `docs/findings.md`.
Read `docs/findings.md` for the current state of a claim and
`docs/findings.yaml` before editing one. Both live under `docs/`.

## Hardware

[bringup.md](repo:docs/bringup.md#L1) is the ordered bring-up procedure and
the reasoning behind each step's verdict. Its Hardware log records what has
actually run on silicon, console by console, and is never edited away when
a later step regresses. Read it when a bench reading fails and the reason
matters, or before touching a step that a fix already closed. It lives at
`docs/bringup.md`. The steps it walks are the same ten steps on
[First boot](page:runtime/first-boot#steps-1-10).

[bench-runbook.md](repo:docs/bench-runbook.md#L1),
[bench-phase1.md](repo:docs/bench-phase1.md#L1) and
[bench-phase2.md](repo:docs/bench-phase2.md#L1) are the runbooks carried to
the console itself: one sitting each, no reasoning, only which ELF to boot,
what a cell should show, and the verdict table. Read the one for the phase
under test, and nothing else, while at the bench. They live at
`docs/bench-runbook.md`, `docs/bench-phase1.md` and `docs/bench-phase2.md`.

[design-bringup-3-to-9.md](repo:docs/design-bringup-3-to-9.md#L1) is the
design for the single ELF and single probe screen that bring-up steps 3
through 9 share, written before it was built so the argument could be
attacked while still cheap. Read it before changing the probe screen or
adding a bring-up step. It lives at `docs/design-bringup-3-to-9.md`.

## Designs

[design-v6-resource-model.md](repo:docs/design-v6-resource-model.md#L1) is
the design for the arena, texture slots and the composition contract.
Sections already shipped are marked `[implemented]` in place rather than
rewritten, so a disagreement that lost stays on the page next to the one
that won. Read it before changing how the runtime sizes or fills the arena.
It lives at `docs/design-v6-resource-model.md`. The arena it introduces is
what [The frame loop](page:runtime/frame-loop#sizing-the-arena) prints a
figure for.

[design-p3b-theming.md](repo:docs/design-p3b-theming.md#L1) is the design
document for theming: the tint table, the CLUT swap it cannot reach, and
the role-keyed authoring model. It disagrees with `PLAN.md` about the scope
of its own phase on purpose, and later revisions mark which answers are
historical. Read it before adding a themed property or a new tint role. It
lives at `docs/design-p3b-theming.md`, and its shipped mechanism is what
[Theming](page:authoring/theming#what-it-is) documents for authors.

## Releasing

[releasing.md](repo:docs/releasing.md#L1) is the procedure for cutting a
release: what a prerelease protects, the steps from version bump to tag to
publish, and what is still done by hand. Read it before bumping a version
or cutting a tag. It lives at `docs/releasing.md`. A struct-layout change
that forces a release also breaks the format
[pledge](page:reference/uib-format#the-pledge), and the release notes say
so.

## Related pages

| page | relation |
|---|---|
| [First boot](page:runtime/first-boot#steps-1-10) | the ten-step checklist this page's Hardware section explains the reasoning behind |
| [Theming](page:authoring/theming#what-it-is) | the authoring guide for the mechanism `design-p3b-theming.md` designs |
| [The frame loop](page:runtime/frame-loop#sizing-the-arena) | the arena `design-v6-resource-model.md` sizes |
| [.uib](page:reference/uib-format#the-pledge) | the format pledge a release must not break without a version bump |
