# Facts files

One file per page, written by the page's agent before the page itself.
The page is what a reader sees; the facts file is the audit trail and the
handoff to dependent pages. Path: `_facts/<page-id>.md`.

```markdown
# facts: authoring/dynamic-text

| id | fact | source | verified by | status |
|---|---|---|---|---|
| slot.capacity.default | data-slot-capacity defaults to 63 | packages/layout/src/box.js:212 | compiled a slot with no capacity; ir.slots[0].capacity == 63 | verified |
| slot.lookup.global | ps2ui_slot_set resolves over the whole blob | runtime/ps2ui.c:1398 | runtime/tests/test_runtime.c "dynamic text (F2)" | verified |
```

| status | meaning |
|---|---|
| verified | a command or test run in the session proved it |
| code-only | read in source; nothing executable exists; the row says why |
| contradicts-readme | verified, and README.md says otherwise; the row cites the README line |

Fact ids are dotted, lowercase and stable. Each brief under `_prompts/`
names the ids its page must emit and the parent facts files it reads.

A child that finds a parent fact wrong appends this and stops:

```markdown
## disputes

| id | parent | evidence |
|---|---|---|
| focus.wrap | authoring/focus-and-navigation | compiled a 2x3 grid with --focus-wrap; right off tile 3 lands on tile 4, not tile 1; see focus.js wrap() |
```

The orchestrator reruns the parent with the dispute appended to its brief,
then the child.
