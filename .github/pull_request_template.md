<!-- Keep it to one topic. See CONTRIBUTING.md and AGENTS.md. -->

## What this changes

<!-- And why. Link the issue if there is one: Fixes #123 -->

## How it was verified

<!-- Which of these you ran, and anything you exercised by hand. -->

- [ ] `make check` (or the backend/frontend halves of it)
- [ ] Exercised in the UI against the mock server or a real stack

## Checklist

- [ ] New behaviour has a test; a bug fix has the test that fails without it
- [ ] `CHANGELOG.md` updated under `Unreleased`
- [ ] If the API changed: `openapi.yaml`, backend schemas, `make codegen` and the mock server agree
- [ ] If the schema changed: a reviewed migration is included and applies on SQLite and Postgres
- [ ] If UI strings changed: both `en` and `ru` have the key
- [ ] The README configuration tables are updated (if an environment variable was added)

## Anything a reviewer should look at closely

<!-- Trade-offs, things you were unsure about, anything you want a second opinion on. -->
