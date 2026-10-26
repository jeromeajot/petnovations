# CatGenie extraction kit (Apple Silicon Mac)

You are logged into the CatGenie app on your Mac. That login provisioned your
account's signing secret into the app. This procedure pulls out the three things
our integration needs:

1. **The signing key** — via Frida, hooking the HMAC call (`frida_dump_key.js`).
2. **The login request shape** — via a proxy, by watching a real login.
3. **The refresh request shape** — via the same proxy, by watching a token refresh.

Do part A (key) and part B (traffic) in either order. Part B is the reliable one;
part A is the one with platform risk, noted below.

---

## Part A — Dump the signing key with Frida

### 1. Install Frida

```bash
python3 -m pip install --user frida-tools
# or: pipx install frida-tools
frida --version
```

You need a Frida new enough to support arm64 macOS (17.x+).

### 2. Find the app's process name

With the CatGenie app running and logged in:

```bash
frida-ps | grep -i -E 'cat|genie|petnov'
```

Note the exact process name it prints (call it `CatGenie` below).

### 3. Attach the dumper

```bash
frida -n CatGenie -l frida_dump_key.js
```

### 4. Trigger a signed request

In the app, do something that hits the network: pull-to-refresh the device
list, or open the device screen. Watch the terminal. You want the block:

```
[CCHmac] HMAC-SHA256 key observed:
  ascii="Yt................x3"  len=30  hex=...
```

**That `ascii="..."` value (about 30 characters) is your signing key.** Copy it.
If several distinct keys show up, the signing key is the one that is ~30 chars of
printable text and recurs on every request; ignore short or binary ones.

### Risk / fallback for Part A

iOS-apps-on-Mac run with hardened runtime and library validation, which can stop
Frida from injecting. Symptoms: `Failed to attach: ...` or no hooks firing.
If that happens, in order of preference:

- Try `sudo frida -n CatGenie -l frida_dump_key.js`.
- If still blocked, the usual workaround is to disable AMFI library validation
  (boot into recovery, `csrutil` / `nvram boot-args`). This weakens system
  security; only do it knowingly and revert afterward. Tell me if you reach this
  point and I'll give exact commands.
- If Frida is a dead end, Part B's proxy still gives us the tokens and request
  shapes, and we can get the key instead by hooking `crypto-js` in the JS bundle
  or dumping the app container keychain. We'll pick that up only if needed.

---

## Part B — Capture login and refresh traffic with a proxy

Use **Proxyman** (easiest on macOS) or mitmproxy.

### 1. Set up TLS interception

- Install and trust the proxy's root certificate (Proxyman walks you through it).
- Enable SSL proxying for the host `iot.petnovations.com`.

### 2. Capture a login

Log out of the CatGenie app, then log back in with your phone number + SMS code.
In the proxy you should see, in order:

- `POST ums/v1/users/generateLoginCode/v2`  — sends the SMS.
- `POST ums/v1/users/loginByPhoneNumber/v2` — returns your tokens.

### 3. Capture a refresh (optional but valuable)

Leave the app open for an hour, or quit and reopen it, until it silently fetches
a new token. Look for a request whose response contains a fresh `token`.

### Cert pinning note

If the proxy shows TLS handshake failures for `iot.petnovations.com`, the app
pins its certificate. Tell me — there is a small Frida script that disables
pinning, and we run it alongside the capture.

---

## What to send back to me

For the key:

- The `ascii="..."` signing key from Part A. This is account-sensitive; treat it
  like a password. You can paste it to me to bake into the config, or keep it and
  enter it in Home Assistant yourself.

For each captured request (login code, login, refresh, and one `device/device/v2`),
copy the **request method + URL**, the **request body JSON**, and the
**response JSON**. You may redact the actual token *values* and your phone number;
I need the field **names** and structure, for example:

```
POST ums/v1/users/loginByPhoneNumber/v2
request:  {"phoneNumber":"<redacted>","countryCode":"1","code":"123456", ...}
response: {"token":"<jwt>","refreshToken":"<rt>", "accountId":"...", ...}
```

With the key plus those shapes, I finalize the client and config flow, and the
`verify_catgenie.py` tool will confirm it end to end on your machine before we
touch Home Assistant.
```
