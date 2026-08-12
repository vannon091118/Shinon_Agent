# Releases

ShinonLLM uses Semantic Versioning and a tag-driven GitHub Release workflow.

Start here:

- Versioning policy: [docs/releases/VERSIONING.md](./docs/releases/VERSIONING.md)
- Release checklist: [docs/releases/RELEASE_PROCESS.md](./docs/releases/RELEASE_PROCESS.md)
- Changelog: [CHANGELOG.md](./CHANGELOG.md)

Operational rule:

- Creating and pushing a tag `vMAJOR.MINOR.PATCH` triggers `.github/workflows/release.yml` and publishes a GitHub Release.
- Release notes are extracted from the matching section in `CHANGELOG.md`.

