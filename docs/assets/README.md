# docs/assets

## The header logos, and why there is more than one

`ophtml-logo-releaseVersion<NNN>-plain-white-darkbg.png` is the image at
the top of `README.md`. It carries the release version **twice**: in the
filename, and rendered into the artwork. 1280x640 RGB, every one of them.

**Exactly one of these is referenced at a time.** The rest are exports
staged ahead of the releases that will use them, so that cutting a
release is an `<img src>` edit rather than a trip to the design file.
They are not dead files and they are not leftovers — do not tidy them
away.

`git log --follow` on any of them shows which release each was cut for.

## Which one the README should point at

`tools/check-versions.py` rule 10b decides, and it is **two-state**, the
same shape as rule 5's CHANGELOG heading and rule 10's tag:

| the tree carries | the README shows |
|---|---|
| a release (`0.7.0`) | that release — the version being cut |
| a prerelease (`0.7.0.dev0`) | the **last release** (`0.6.0`) |

The prerelease case is deliberate. During development the logo should
show the version people can actually install, and a rule demanding
`070` on a `0.7.0.dev0` tree would be wrong on `main` for the whole of a
development cycle. A fence that is wrong between releases gets an
exemption bolted onto it within a week.

So on `main` the newest staged logo is normally **not** the one in use.
That is the correct state, not drift.

## Adding the next one

Export from the design file at 1280x640, drop it here, and stop. Do not
touch `README.md`: the swap belongs to `docs/releasing.md` step 5 and
can only be correct on a release tree.

**Check the version in the artwork, not the filename.** Step 5 says so
in as many words, and it is the half a checker cannot hold — rule 10b
reads the filename, because that is what a regex can see. The two move
together only because whoever exports the file makes them.

## Deleting an old one

Step 5's last clause: delete the previous file once nothing references
it. `grep` the tree first — `README.md` has historically been the only
reference, but "historically" is not "currently".

An old asset that a published release still needs is kept by that
release's tag, so deleting it here does not break `v0.5.0`'s README.

**And delete a staged logo whose version never happens.** These are
staged against a guess at the sequence, not a commitment to it —
nothing in `docs/PLAN.md`, `CHANGELOG.md` or `README.md` says what
follows a given release. If `0.7.0` is followed by something other than
`0.8.0`, then `080` and `090` are dead files wearing a note above that
says they are not, which is the state this document exists to prevent,
one version along. Raised in review of the change that staged them.
