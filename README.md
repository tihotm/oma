# OMA

OMA is a deterministic acceptance/control core for agent-driven software work.

This repository begins with a deliberately small implementation slice derived from the prior TEST_CONFIRMED verification model. It does **not** claim benchmark improvement.

## Current implementation slice

- evidence is bound to `subject_id` and `subject_state_id`;
- evidence is bound to `verification_context_id` and `policy_bundle_id`;
- unknown, duplicate, or mismatched evidence fails closed with `BLOCK`;
- incomplete required obligations produce `NOT_DONE`;
- `ACCEPT` requires every required obligation to have one correctly-bound `PASS` evidence record.

Precedence in this slice is:

`BLOCK > NOT_DONE > ACCEPT`

## Scientific status

The historical adversarial/property model (items 29–47, invariants I29–I204) remains `TEST_CONFIRMED` only. This code is the beginning of implementation confrontation, not proof that all invariants are implemented and not a product benchmark.

## Tests

```bash
python -m pytest
```
