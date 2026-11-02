# Releasing PyFreeRdpApp

Releases are built and published by `.github/workflows/release.yml` when a version tag is pushed.
Publishing uses PyPI **Trusted Publishing** (OIDC): no API token is stored anywhere, and every upload
gets PyPI attestations.

## One-time setup

1. **pyfreerdpnative must be on PyPI first.** PyFreeRdpApp depends on it, and PyPI does not accept
   direct-URL dependencies: published without it, `pip install PyFreeRdpApp` would fail for
   everyone. The workflow refuses to publish to PyPI until `pyfreerdpnative` can be installed from
   there (TestPyPI only warns).
2. **Trusted publishers.** On <https://pypi.org/manage/account/publishing/> add a *pending
   publisher* (the project does not exist yet): project `PyFreeRdpApp`, owner `Usama01TN`, your
   repository's name, workflow `release.yml`, environment `pypi`. Do the same on
   <https://test.pypi.org/manage/account/publishing/> with environment `testpypi`.
3. **Environments.** In the repository, *Settings > Environments*: create `testpypi` and `pypi`.
   Adding yourself as a *required reviewer* on `pypi` makes every PyPI upload wait for your click.
4. **Variables** (*Settings > Secrets and variables > Actions > Variables*), both optional:

   | variable | meaning |
   |---|---|
   | `PYPI_AUTO_TARGET` | where a pushed tag publishes: `testpypi` (the default), `pypi` or `none` |
   | `PYFREERDPNATIVE_TAG` | the PyFreeRdpNative release whose wheels CI tests against (default: the latest), used while pyfreerdpnative is not on PyPI |

## Each release

1. Set the same version in `pyproject.toml` (`version = "X.Y.Z"`) and
   `PyFreeRdpApp/metadata.py` (`__version__ = u'X.Y.Z'`), and commit.
2. Tag and push:

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

The workflow then:

| step | what it does |
|---|---|
| version | the tag, `pyproject.toml` and `metadata.py` must agree, or nothing happens |
| tests | the full suite (`ci.yml`) on Python 3.9-3.13, plus import/CLI checks on Windows and macOS |
| build | sdist and wheel; README images made absolute for PyPI; `twine check --strict`; wheel contents checked |
| verify | the built wheel installed fresh and run on Linux, Windows and macOS |
| publish | TestPyPI or PyPI, as `PYPI_AUTO_TARGET` says |
| GitHub Release | the tag's release, with the files, install instructions and generated notes |

A version like `X.Y.Zrc1`, `X.Y.Za1` or `X.Y.Zb1` becomes a GitHub *pre-release*.

## By hand

*Actions > Release > Run workflow* runs the same pipeline with a chosen target. From any branch,
target `none` is a dry run (tests, build, verify; nothing published). Publishing and GitHub
Releases need a tag: choose the tag in the *Use workflow from* list.

Re-running a release is safe: TestPyPI skips files it already has, and an existing GitHub Release
gets its files replaced. PyPI never accepts the same version twice: release a new version instead.
