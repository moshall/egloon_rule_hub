# Online compatibility providers for Mihomo / FlClash

These providers convert the public sources used by the Egern 261112 profile.
They contain routing/DNS matching data only; no proxy subscription links,
WireGuard credentials, complete user profiles, or other secrets are published.

Use `type: http`, `behavior: classical`, `format: yaml`, and an update interval
of 86400 seconds. Raw URLs use this directory on the `main` branch.

| File | Meaning |
| --- | --- |
| route_06.yaml | Pico routing conditions from the original public, revision-pinned gist |
| route_31.yaml | GMOogway direct module, supported domain/IP conditions only |
| route_32.yaml | Repcz LAN routing conditions |
| dns_forward_0.yaml | LAN domain conditions for system DNS |
| dns_forward_1.yaml | Repcz China domain conditions for domestic DNS |
| dns_forward_2.yaml | Original `*.icloud.com` wildcard condition |
| dns_forward_3.yaml | Original `*.goog` wildcard condition |
| dns_forward_4.yaml | Repcz Global domain conditions for overseas DNS |

The workflow runs after converter changes, manually, and daily at 04:00
Asia/Shanghai. FlClash fetches updates on its own interval. If fetching or
conversion fails, no new revision of these providers is committed; the last
successful version remains available. `manifest.json` records sources,
rule counts, exclusions, and output hashes.

Unsupported URL-REGEX rules are omitted rather than expanded into broader
whole-domain rules. DNS providers use domain conditions only. The Pico gist
retains the original fixed revision, so changing its contents requires updating
the configured source revision explicitly.

Regenerate with `python tools/sync_mihomo_online_compat.py` (requires PyYAML).
