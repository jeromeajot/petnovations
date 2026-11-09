# Credits and provenance

This integration builds on the work of others.

## Original integration

[`PrimeAutomation/petnovations`](https://github.com/PrimeAutomation/petnovations)
by @bensoae87 and contributors. This repository is a fork. The original
established the Home Assistant integration (the `petnovations` domain, the
coordinator/sensor structure) and, importantly, mapped the CatGenie device
payload: the `thingList` shape, the `operationStatus` state codes, the cartridge
and timing fields. That data-model knowledge is reused here.

## Signing-scheme reverse engineering

[`Rukongai/CatDjinni`](https://github.com/Rukongai/CatDjinni) documented the
reworked API's request-signing algorithm (the HMAC header scheme, the AES
`x-pm-en-dec` header, and the key-derivation method). This project's
`signing.py` is an independent implementation of that documented algorithm,
verified against genuine captured traffic from the author's own account.

## What is new here

The signing layer (`signing.py`), the async client and token refresh (`api.py`,
`tokenutil.py`), the binary sensors, the config/options/reauth flow, the sane
poll interval, the tests, and the extraction/verification tooling were written
for this fork.

## Licensing

The upstream repository does not declare a license. Reuse here is via GitHub's
fork mechanism. Reverse-engineered algorithms and API field names are facts, not
copyrightable expression. If you are the upstream author and would like a
specific license applied, please open an issue.
