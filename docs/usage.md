# Usage

This repository is designed to publish both per-service and per-bundle artifacts.

Each per-service target publishes a directory under `Rule/<TargetDir>/<Service>/` that bundles the README with the native artifact.

Expected artifact layout:

- `Rule/Clash/OpenAI/OpenAI.yaml`
- `Rule/Loon/OpenAI/OpenAI.list`
- `Rule/Egern/OpenAI/OpenAI.yaml`
- `Rule/QuanX/OpenAI/OpenAI.list`
- `Rule/Shadowrocket/OpenAI/OpenAI.list`
- `dist/bundles/<bundle>/<target>.<ext>`

Example raw URL pattern after publishing the repository:

```text
https://raw.githubusercontent.com/<owner>/<repo>/<branch>/Rule/Clash/OpenAI/OpenAI.yaml
https://raw.githubusercontent.com/<owner>/<repo>/<branch>/Rule/Loon/OpenAI/OpenAI.list
https://raw.githubusercontent.com/<owner>/<repo>/<branch>/dist/bundles/ai/loon.list
```

Current bundles: ai, china, commerce, gaming, google, social, streaming

Use `python -m egloon_rule_hub render-rules` to refresh rule artifacts only.

Use `python -m egloon_rule_hub bootstrap` after catalog changes to refresh rules, docs, and manifests together.
