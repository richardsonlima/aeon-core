# Release guide

**Nothing has been published.** No tag exists for 0.5.0, the PyPI and TestPyPI projects are not created, the GitHub environments are not configured, and no container image has been pushed. Every step below is done by the maintainer. Tagging and pushing are manual.

## One-time setup

### 1. PyPI and TestPyPI: pending trusted publishers

No API tokens are used. Create a pending publisher on each index before the first release.

PyPI (<https://pypi.org/manage/account/publishing/>), "Add a new pending publisher":

| Field | Value |
|---|---|
| PyPI project name | `aeon-core` |
| Owner | `richardsonlima` |
| Repository name | `aeon-core` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

TestPyPI (<https://test.pypi.org/manage/account/publishing/>): same values, environment name `testpypi`.

### 2. GitHub environments

Repository Settings > Environments:

1. Create `testpypi` and `pypi`.
2. On each, enable "Required reviewers" and add `richardsonlima`.
3. On `pypi`, restrict "Deployment branches and tags" to tag pattern `v*`.

### 3. Docs hosting (pick one)

The public site is `richardsonlima.com.br/aeon/docs`, served from the `richardsonlima.github.io` repository. `docs.yml` always builds with `mkdocs build --strict` and uploads the site as an artifact. Deployment has two options.

**Option A: Pages of this repository (wired in `docs.yml`).** Settings > Pages > Source: GitHub Actions. The job `deploy` runs on pushes to `main` and publishes to `https://richardsonlima.github.io/aeon-core/`. Link to it from the public site. Caveat: the URL differs from `/aeon/docs` and `site_url` in `mkdocs.yml` must match whichever option you use. If you do not want Pages, leave the setting off and the `deploy` job fails harmlessly (the build job still validates the docs).

**Option B: push the built site into `richardsonlima.github.io/aeon/docs` (manual, not enabled).**

1. Generate a deploy key pair: `ssh-keygen -t ed25519 -f aeon-docs-deploy -N ""`.
2. Add the public key to `richardsonlima.github.io` (Settings > Deploy keys, write access).
3. Add the private key to this repository as an environment secret `DOCS_DEPLOY_KEY` in a new environment `docs-site` with a required reviewer.
4. Add a job that checks out `richardsonlima.github.io` over SSH, replaces `aeon/docs/` with the contents of the `docs-site` artifact, commits and pushes. Not written here on purpose: enable it only after you accept a CI job having write access to the other repository.

## Cut a release

1. Make sure `main` is green and the branch is merged.
2. Set the version in `src/aeon/_version.py` (for example `0.5.0`).
3. In `CHANGELOG.md`, rename `Unreleased` to `## [0.5.0] - YYYY-MM-DD` and add a fresh empty `Unreleased`. The release job fails if the section for the tag is missing (`python scripts/release_notes.py v0.5.0` shows what will be attached).
4. Commit, then tag and push, yourself:
   ```bash
   git tag -a v0.5.0 -m "v0.5.0"
   git push origin main v0.5.0
   ```
5. The `Release` workflow runs: build, twine check, SBOM, provenance attestation. It then waits for your approval on `testpypi`, then on `pypi`, then creates the GitHub release with wheel, sdist and SBOM.

A dry run without a tag: Actions > Release > Run workflow, `target: testpypi`.

The build job refuses a tag that does not match `src/aeon/_version.py`.

## Verify a release

```bash
python -m venv /tmp/aeon-verify && . /tmp/aeon-verify/bin/activate
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ aeon-core==0.5.0
aeon version
aeon doctor
```

Provenance of a downloaded wheel:

```bash
pip download aeon-core==0.5.0 --no-deps -d /tmp/aeon-dl
gh attestation verify /tmp/aeon-dl/aeon_core-0.5.0-py3-none-any.whl --repo richardsonlima/aeon-core
```

The SBOM (`aeon-core.cdx.json`, CycloneDX) is attached to the GitHub release.

## Rollback

PyPI does not allow replacing or reusing a version. To pull a bad release:

1. On pypi.org, project `aeon-core` > Manage > the release > "Yank". Installs that pin the exact version still work; resolvers skip it.
2. Fix forward: bump to the next patch version and release again.
3. Edit the GitHub release to say it is yanked and why, and add the entry to `CHANGELOG.md` and `docs/known-limits.md` if users are affected.

Do not delete the tag after PyPI accepted the upload.

## Container image

`Dockerfile` and `compose.yaml` build locally. No image is pushed anywhere by CI. The image sets `AEON_RUNTIME_ALLOW_REMOTE=1` because the process must bind `0.0.0.0` inside the container; `compose.yaml` publishes the port on `127.0.0.1` only and expects the token in `aeon.env`.
