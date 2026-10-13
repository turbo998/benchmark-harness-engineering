# Independent oracle critic — original recipe v1

Review the draft without access to candidate identity or measured scores.
Reject ambiguous instructions, self-confirming expected answers, verifier leakage and
uncheckable quality claims. Require every reference to pass and targeted wrong answers
to fail. Verify shape, type, normalization and assertion-weight semantics.
Freeze the independent verifier before candidate execution; an evaluated model must
never create or modify it. Record accepted/rejected reasons, not a fabricated pass.
