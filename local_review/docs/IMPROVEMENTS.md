# Research and improvements

## Public source

[CrossBeam by Mike Brown](https://github.com/mikeOnBreeze/cc-crossbeam) is public and MIT licensed. Its README describes model-assisted ADU correction response and checklist workflows, with a cloud architecture. This fork preserves that source and separates new local functionality from the original author's work and original award.

## Implemented changes

| Problem | Added behavior |
| --- | --- |
| A plan-reading demo can depend on multiple paid/cloud accounts | A separate local Python/SQLite review workflow needs no model or cloud credentials |
| A plausible response may lack traceable evidence | Exact page-quote matching, document/page hashes, source labels, and original downloads |
| Text extraction can be mistaken for visual plan review | Explicit blank-page warnings and original-document inspection declarations |
| A review state can hide unresolved work | Required response/evidence checks, open-question blockers, and explicit human confirmation |
| Automated splitting can misrepresent a city letter | Editable working wording with retained original extracts and manual item creation |
| Evidence actions can overwrite unfinished writing | In-memory response drafts survive reloads and rejected saves |
| Multiple tabs can overwrite each other | Item/checklist revision checks reject stale writes |
| “Complete” can imply permit approval | Separate workflow completion and always-draft exports |
| Project artifacts can accidentally enter Git | Private runtime storage and fictional-only new examples/portfolio figures |

## Useful next improvements

1. Evaluate correction extraction against a licensed, independently labeled document set. Report omissions, incorrect splits, and OCR abstentions; no extraction-accuracy benchmark is claimed here.
2. Add isolated OCR and drawing-region review as optional stages with page/region provenance and clear uncertainty. Text quotes alone cannot verify dimensions, stamps, or design adequacy.
3. Add jurisdiction-specific, versioned source packs maintained by qualified reviewers. Record effective dates, source conflicts, and changes; do not silently reuse outdated checklist counts or numeric rules.
4. Add encrypted storage and authenticated access before any multi-user or hosted deployment. The current release is intentionally local and single-user.
5. Connect the retained original AI pipeline through an explicit opt-in, bounded-cost adapter only after its credentials, data-transmission scope, and outputs are reviewed. No paid model run was needed or performed here.

These are future recommendations, not completed features or claims of legal/engineering correctness.
