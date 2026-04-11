# Manual TXT Sources

This directory stores TXT source inputs used for future conversion into client-specific rule artifacts.

Current usage:

- Manually maintained TXT sources can live here when no suitable upstream rule source exists.
- Generated TXT sources can also live here when an official web page needs to be snapshotted into rule lines.
- One platform or service per `.txt` file; only files with a `.txt` suffix are autodiscovered.

Current examples:

- `IyfTv.txt`: manually maintained source file.
- `Feishu.txt`: generated from the official Feishu help-center whitelist article via `python -m egloon_rule_hub refresh-txt-sources`.

Current line style:

- Comments can describe sections or metadata. Metadata comments follow the `# @key: value` pattern and are captured for the service snapshot.
- Rule lines may already include canonical providers such as `DOMAIN-SUFFIX,...` or `IP-CIDR,...`.
- Relaxed shorthand is supported: a bare domain like `example.com` converts to `DOMAIN-SUFFIX,example.com`, and a bare CIDR like `1.2.3.0/24` converts to `IP-CIDR,1.2.3.0/24`.
