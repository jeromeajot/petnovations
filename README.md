# CatGenie A.I. (Petnovations) for Home Assistant

Monitor a CatGenie A.I. self-washing litter box in Home Assistant: know when a
cleaning cycle starts, when there's a problem, how much cartridge solution is
left, and when it last ran.

Petnovations reworked their cloud API so every request must be cryptographically
signed, which broke the earlier integration. This fork restores it: it signs
requests correctly and refreshes tokens against the current `/v2` endpoint. The
signing was **verified against real captured traffic** — the signer reproduces
genuine request signatures exactly.

This is a fork of
[`PrimeAutomation/petnovations`](https://github.com/PrimeAutomation/petnovations);
see [`NOTICE.md`](NOTICE.md) for credits to it and to the
[CatDjinni](https://github.com/Rukongai/CatDjinni) reverse-engineering work.

## What you need

Two values, extracted once from the official CatGenie app:

1. **Signing key** — the 32-character key, or the 84-character secret it derives
   from (`key = "Yt" + secret[56:84] + "x3"`).
2. **Refresh token** — long-lived. The integration mints access tokens from it,
   so there is no repeated login.

Both are account credentials: treat them like passwords. How to obtain them (on
an Apple-Silicon Mac, via Keychain Access and an HTTPS proxy) is written up in
[`tools/EXTRACTION.md`](tools/EXTRACTION.md).

## Try it before installing

Confirm everything works against your account with the standalone checker (only
needs system Python and openssl):

```bash
python3 tools/verify_catgenie.py \
  --key "<your-32-char-signing-key>" \
  --refresh-token "<your-refresh-token>"
```

It refreshes a token and prints your CatGenie's cycle state, any error,
cartridge level, and last-clean time.

## Install

### HACS (custom repository)

1. HACS → three-dot menu → Custom repositories.
2. Add `https://github.com/jeromeajot/petnovations`, category **Integration**.
3. Install "CatGenie A.I. by Petnovations", then restart Home Assistant.

### Manual

Copy `custom_components/petnovations/` into your Home Assistant
`config/custom_components/` directory and restart.

### Configure

Settings → Devices & Services → Add Integration → **CatGenie**. Paste the
signing key (or 84-char secret) and the refresh token. The poll interval
defaults to 60 seconds and is adjustable in the integration's Options (minimum
30s).

## Entities

**Binary sensors** (ideal for automations):

- **Cleaning cycle** — on while a cycle is in progress.
- **Problem** — on when the device reports an operation error (the error is an
  attribute).
- **Online** — cloud reachability.

**Sensors:** cycle status, cycle progress %, operation error, cartridge
remaining, last clean (timestamp), firmware.

### Example automations

```yaml
automation:
  - alias: CatGenie cycle started
    trigger:
      - platform: state
        entity_id: binary_sensor.catgenie_cleaning_cycle
        to: "on"
    action:
      - service: notify.mobile_app_your_phone
        data:
          message: "CatGenie cleaning cycle started."

  - alias: CatGenie problem
    trigger:
      - platform: state
        entity_id: binary_sensor.catgenie_problem
        to: "on"
    action:
      - service: notify.mobile_app_your_phone
        data:
          message: >-
            CatGenie problem:
            {{ state_attr('binary_sensor.catgenie_problem', 'error') }}
```

## Scope and honesty

- **Monitoring only.** Reading device state and refreshing tokens are
  implemented and verified. Device control (starting a cycle, changing config)
  is intentionally not included.
- The refresh response's access-token field is read tolerantly. If a future API
  change renames it, `verify_catgenie.py` prints the response keys so it can be
  adjusted quickly.

## Development

```bash
make install   # ruff, pytest
make check     # lint + tests (what CI runs)
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Security policy and credential handling
are in [`SECURITY.md`](SECURITY.md).
