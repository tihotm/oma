# Trust Artifact Authenticity Audit

Baseline under test: `7c8d367316db75cb30b472ee9ee29916035f3ff7`

## Question

Can a caller fabricate a `SignedArtifact` that merely claims an existing trusted root and current epochs, then satisfy `trust_temporal` and reach durable terminal ACCEPT without any issuance/signature proof?

## Attack

The configured trust roots and policy bundle remain unchanged. The caller replaces the legitimate artifact with a newly constructed object using:

- a new caller-chosen artifact ID;
- the real root ID;
- current trust/authority/logical/state epochs;
- valid activation/expiry bounds.

There are no signature bytes, public keys or MAC verification in the current `SignedArtifact` contract.

Control: the same fabricated metadata with an unknown root ID must BLOCK.

## Interpretation

If the fabricated artifact claiming the real root produces `trust_temporal=ACCEPT`, global durable `ACCEPT`, and a terminal row, Item 41 authenticity is causally bypassable at the supported boundary.

No production fix is included in this audit branch. Implementation follows only if whole-repository CI confirms the attack.
