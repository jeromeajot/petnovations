# Security policy

## Supported versions

Only the latest release receives fixes.

## Reporting a vulnerability

Please do not open a public issue for security problems. Use GitHub's private
vulnerability reporting on this repository ("Security" tab → "Report a
vulnerability"). You will get an acknowledgement within a few days.

## Credential handling

This integration authenticates to the Petnovations cloud with two account
secrets that you extract from the official app:

- a **signing key** (or the 84-character secret it derives from), and
- a long-lived **refresh token**.

Notes on how they are handled, and what you should do:

- They are stored in Home Assistant's config entry, like any other integration
  credential. Protect your Home Assistant instance accordingly.
- They are never written to logs by this integration. If you share logs or open
  an issue, redact anything that looks like a key or a `eyJ...` token.
- Rotating them is simple: sign out of the CatGenie app and back in, then
  re-extract and update the integration (it supports re-authentication).
- The static AES key used for one request header is a global app constant, not a
  secret of yours; it is included in the source. Your HMAC signing key is yours
  and is never committed here.

## Scope and provenance

The signing scheme was reverse engineered from the official app for
interoperability, so a device owner can read their own device. The integration
performs read-only polling; it implements no device-control endpoints.
