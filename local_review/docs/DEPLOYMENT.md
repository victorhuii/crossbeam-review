# Deployment

## Current public demo

**Mode:** Recorded fictional review demo.

Package built and checked locally. Awaiting authenticated Cloudflare publishing; no live URL is claimed yet.

The Pages package is a **recorded-results demo**, not the full interactive application. It displays existing evidence and engineering choices. It has no API, uploads, new inference, live scans, trading or saved user state. The original local application remains available through the README.

## Cloudflare Pages settings

| Setting | Value |
| --- | --- |
| Repository | `victorhuii/crossbeam-review` |
| Production branch | `main` |
| Framework | None / custom |
| Root directory | Repository root |
| Build command | `python3 local_review/scripts/build_demo.py` |
| Output directory | `local_review/demo-site` |

Connect this repository in Workers & Pages, select Pages and import the Git repository. The committed `wrangler.jsonc` records the output directory; no credentials or account IDs are committed. Cloudflare supplies the deployed URL after a successful build. Do not add a guessed `pages.dev` URL to the profile.

For a direct upload after local checks:

```sh
python3 local_review/scripts/build_demo.py
python3 local_review/scripts/check_demo.py
npx wrangler pages project create crossbeam-review --production-branch main
npx wrangler pages deploy local_review/demo-site --project-name crossbeam-review
```

Run the project-create command only for a new Pages project. Use the actual returned deployment URL. Git-connected Pages builds automatically from subsequent pushes; direct uploads must be repeated after changes. The `demo package` workflow validates and uploads a download-only artifact; it does not deploy or store a Cloudflare token.

## Full application hosting

**Backend:** Python PDF/import/export and review API.

**Storage/jobs:** Private document storage plus persistent SQLite review state.

**Remaining public-service work:** The local extension needs tenant authorization, upload quotas, PDF worker isolation, private storage, backups and draft-export retention before public uploads. Do not deploy the unrelated upstream cloud system as if it were this extension.

Static Pages does not execute the existing Python HTTP server or native C++ binaries. Reusing the local server with a public bind address is not sufficient production hardening. Use a supervised/containerized service for those runtimes, keep any secrets server-side, and enforce application-specific input/work limits. A Workers port would be a separate implementation and validation effort, not an automatic setting.

## Release checks

- Build/check the exact output directory; deploy only that directory.
- Preserve ownership, source credits and historical/synthetic labels.
- Verify returned HTTPS URL, expected assets, security headers and actual user paths after publishing.
- For API-backed demos, test health, a real data request, exact-origin CORS and visible network errors.
- Keep model artifacts, databases, raw datasets, credentials and private uploads outside the public static bundle.
- Browser visual/audio/device QA was unavailable in this session. Automated checks do not establish that testing.

References: [Cloudflare static HTML](https://developers.cloudflare.com/pages/framework-guides/deploy-anything/), [build settings](https://developers.cloudflare.com/pages/configuration/build-configuration/), [headers](https://developers.cloudflare.com/pages/configuration/headers/), [asset limits](https://developers.cloudflare.com/pages/platform/limits/).
