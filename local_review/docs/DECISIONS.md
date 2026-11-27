# Design choices

CrossBeam Review — implementation rationale and tradeoffs.

| Choice | Why it fits this project | Cost or boundary |
| --- | --- | --- |
| Separate attributed local extension | Preserve the original MIT cloud/AI project and clearly bound the new contribution. | Upstream cloud/model behavior is not established by local checks. |
| Text/page provenance and identity checks | Connect each review item to the imported document and source page. | Text extraction does not establish OCR, blueprint vision or legal compliance. |
| Human gates and draft-only exports | Keep missing information and professional judgment explicit. | No signatures, permit approvals or compliance certification are generated. |

## Evidence and scope

Contribution is the local review workflow; Mike Brown owns the original CrossBeam work. MIT fork extension of Mike Brown’s CrossBeam; examples are fictional and exports remain drafts.

Ownership: **Attributed fork extension**. Attribution and source notices remain in the [README](../../README.md).

See [architecture](ARCHITECTURE.md) and [portfolio notes](PORTFOLIO.md) for implementation details and existing evidence. This documentation update does not add a new benchmark or training run.
