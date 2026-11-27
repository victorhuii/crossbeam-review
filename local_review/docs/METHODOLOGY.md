# Local review methodology

## What this extension does

The original CrossBeam combines model-assisted plan reading, code research, and cloud orchestration. This extension provides a separate deterministic local workspace for preparing and reviewing a response package. It retains the original code and attribution but does not substitute text extraction for vision or claim that its manual workflow automatically performs the original agent's legal analysis.

## Documents and correction candidates

PDF imports are capped at 8 MB and 100 pages. The parser uses pypdf with reduced stream/decompression/work limits, rejects encrypted or unreadable documents, and limits each page's content stream and extracted text. Whole-document extracted text is capped at 500,000 characters. Complex valid PDFs can be rejected; splitting or a clearly labeled manual-text import is the fallback.

PDF source bytes stay immutable in SQLite. Each document and extracted page has a SHA-256 digest. These hashes identify stored bytes/text; they do not authenticate a city's authorship or validate a drawing. The parser does not execute embedded PDF actions or perform OCR, measurements, image interpretation, stamp validation, or signature verification. [pypdf extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html), [security configuration](https://pypdf.readthedocs.io/en/stable/user/security.html).

UTF-8 text imports use form feeds to separate declared pages. They are labeled `manual_text`, with an explicit warning that the original PDF and page numbering are unauthenticated.

A line-based extractor recognizes common numbered/lettered correction starts. Continuation lines on the same page join the current candidate; a document without recognized starts falls back to page blocks. This is a candidate list, not semantic extraction. Bullets, tables, headers, footers, cross-page continuations, and complex numbering can cause omissions or incorrect grouping. Always check the original letter independently. Add manual items and edit working wording when needed; the original extract and audit remain.

## Evidence and review

Search ranks page candidates by keyword overlap, excluding the correction letter itself as evidence that its own requests were satisfied. It does not establish semantic support, regulatory applicability, or a successful design correction.

An attached quote must contain 8–1000 characters and match the selected page after whitespace normalization. The record stores the document/page identities, hashes, source type, exact entered quote, and an explicit original-context check flag. Cross-project document access and stale item revisions are rejected.

A reviewed item needs a response, at least one attached quote, every attached quote checked, no open question, and explicit human review confirmation. An optional legal/reference URL requires HTTPS and a separate applicability check when used. These are workflow constraints, not proof that the reviewer made a correct legal or engineering judgment. Changing evidence reopens a reviewed item as a draft.

Working correction wording can differ from the original extract. Exports label reviewer edits and retain the original text. Human notes and declarations are user-supplied statements; this app does not independently verify the person's credentials or inspection.

## Checklist and completion

Tasks cover identity/jurisdiction, site and floor/elevation review, structural and system coordination, visual signature/revision inspection, and current submission process. Conversion/JADU categories add an existing-condition review task. No changing numeric entitlement limit is hardcoded.

Each checked/not-applicable task requires a written basis. Local workflow completion requires reviewed items, a plans record, inspected-document declarations, and no pending checklist tasks. It is labeled ready for professional review, never permit-approved. A complete task list is not proof of a complete municipal checklist or compliance.

## Draft packages

PDF and Markdown exports include item states, working correction text, response drafts, open questions, evidence citations and hashes, document-inspection declarations, checklist status/bases, and official research entry points. Every PDF page carries a draft footer. The PDF embeds a Unicode font for supported characters; unsupported characters appear as explicit `[U+code]` escapes, while Markdown/JSON retain original Unicode.

Research JSON exports are snapshots including recent audit events and metadata, not restorable backups of every original document. Originals remain in the SQLite database. The application has no submission endpoint, recipient-address fields, automatic outreach, or external file upload.

## Official research sources

Entry links were checked November 27, 2026:

- [HCD ADU portal](https://www.hcd.ca.gov/building-standards/adu).
- [HCD ADU Handbook](https://www.hcd.ca.gov/building-standards/adu/handbook), whose landing page identifies the March 2026 update.
- [Placentia ADU/JADU resources](https://www.placentia.org/1133/Accessory-Dwelling-Units-ADUJADU), an example city source.
- [Placentia permit process](https://www.placentia.org/1053/PERMITS-ONLINE--SMARTGOV-CITIZENS-PORTAL), an example process source.

The pages can change. The app stores links and check dates, not authoritative legal text, and does not automatically reconcile differences between state guidance and local pages. Verify the current source and jurisdiction before relying on any rule. The fictional demo city has no actual applicable municipal code.

## Attribution and privacy

Mike Brown's MIT-licensed original supplies the retained CrossBeam cloud application. Victor Hui's contribution is the local review package, fictional fixtures, tests, and portfolio materials. New demo files contain no real city correspondence or client plans.

SQLite contains private imported content and should be handled as sensitive local data. The loopback server has Host/origin checks and bounded JSON writes but no accounts or encryption at rest. A local user who can edit the database can also edit the audit; it is not tamper-proof. No paid calls or cloud system were exercised in this release.
