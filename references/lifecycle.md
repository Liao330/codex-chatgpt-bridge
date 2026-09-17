# Run Lifecycle

```text
draft
  -> authorized
  -> prepared
  -> committing
  -> committed
  -> generating
  -> complete | partial | incomplete | blocked | unknown
```

## Invariants

- `submission.count <= 1`.
- `committing` is entered before the Send click.
- `committed` is recorded only after an observable acknowledgement.
- An ambiguous acknowledgement becomes `unknown`, not `failed` and not `complete`.
- `partial` and `incomplete` are not accepted as final output.
- `blocked` preserves the blocker.
- Recovery always prefers the same conversation identity.
- A new send requires explicit user confirmation and a new run.
- Work is not a valid route.

## Completion

Completion requires all of:

- no active generation;
- terminal signal observed;
- complete final response captured;
- no required artifact that is missing;
- raw response hash recorded.

Deep Research may run for a long time. The same invariants apply, but reconnection and waiting windows are longer.
