# Contributing

Thanks for helping out. This document covers how the project is organised and
what a good pull request looks like.

## Getting started

Requirements: Python 3.12+. A real CatGenie account is only needed for live
testing.

```bash
git clone https://github.com/jeromeajot/petnovations.git
cd petnovations
make install    # dev dependencies (ruff, pytest)
make check      # lint + tests (what CI runs)
make help       # every task
```

To test against your own device end to end, use `tools/verify_catgenie.py`
(see `README.md`). It needs your signing key and refresh token, which are
account credentials — never commit or paste them anywhere.

## Project layout

```
custom_components/petnovations/
  signing.py       Request signing (HMAC headers + AES x-pm-en-dec). No HA imports.
  tokenutil.py     Pure token-extraction helpers. No HA imports.
  api.py           Async cloud client: refresh + device read. Depends on signing/tokenutil.
  coordinator.py   DataUpdateCoordinator (sane poll interval, token persistence).
  entity.py        Shared device-bound base entity.
  sensor.py        Cycle status, progress, error, cartridge, last clean, firmware.
  binary_sensor.py Cleaning / Problem / Online.
  config_flow.py   Setup + reauth + options.
tests/             Pytest unit tests for the pure modules (no HA required).
tools/             Standalone verifier and extraction notes (not shipped to HA).
```

Rules that keep the integration safe and testable:

- **Credentials never get logged or committed.** The signing key, the 84-char
  secret, and tokens are account secrets. Keep them out of code, tests, logs,
  and issues. Tests use dummy vectors only.
- **`signing.py` and `tokenutil.py` import neither Home Assistant nor aiohttp.**
  That keeps them unit-testable in isolation; please keep it that way.
- **The API is monitoring-only today.** Device control (start a cycle, change
  config) is intentionally not implemented. Open an issue before adding writes.
- **Don't lower the poll interval below 30s.** The original integration hammered
  the cloud every 5 seconds; that is what we are fixing.

## Making changes

1. Branch from `main`. Keep the change focused.
2. Add or update unit tests for pure logic in `tests/`.
3. Run `make check` before pushing. CI runs the same, plus hassfest, HACS
   validation, and CodeQL.
4. Describe how you verified it in the PR (unit tests, and `verify_catgenie.py`
   against a real device where relevant).

### Commit messages

Commits and pull request titles follow
[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) **with a
required scope**:

```
type(scope): short summary in the imperative, lowercase, no trailing period

Optional body explaining why. Reference issues with `Fixes #123`.
```

Types: `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `build`, `ci`,
`chore`, `revert`. Scopes are listed in `.github/workflows/pr-title.yml` (for
example `signing`, `api`, `sensor`, `config-flow`, `ci`, `deps`). Add `!` after
the scope for a breaking change.
