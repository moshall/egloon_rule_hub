# Usage

This repository is designed to publish both per-service and per-bundle artifacts.

Expected artifact layout:

- `dist/egern/<Service>.yaml`
- `dist/loon/<Service>.list`
- `dist/clash/<Service>.yaml`
- `dist/quanx/<Service>.list`
- `dist/shadowrocket/<Service>.list`
- `dist/bundles/<bundle>/<target>.<ext>`

Example raw URL pattern after publishing the repository:

```text
https://raw.githubusercontent.com/<owner>/<repo>/<branch>/dist/loon/OpenAI.list
https://raw.githubusercontent.com/<owner>/<repo>/<branch>/dist/egern/OpenAI.yaml
https://raw.githubusercontent.com/<owner>/<repo>/<branch>/dist/bundles/ai/loon.list
```

Current bundles: ai, china, commerce, gaming, google, social, streaming

Use `python -m egloon_rule_hub render-rules` to refresh rule artifacts only.

Use `python -m egloon_rule_hub bootstrap` after catalog changes to refresh rules, docs, and manifests together.
