# Usage

This repository is designed to publish both per-service and per-bundle artifacts.

Each per-service target publishes a directory under `Rule/<TargetDir>/<Service>/` that pairs the target artifact with a README describing the selected source family and any conversion path.

Expected artifact layout:

- `Rule/Clash/OpenAI/OpenAI.yaml`
- `Rule/Loon/OpenAI/OpenAI.lsr`
- `Rule/Egern/OpenAI/OpenAI.yaml`
- `Rule/QuantumultX/OpenAI/OpenAI.list`
- `Rule/Shadowrocket/OpenAI/OpenAI.list`
- `Rule/Clash/AI/AI.yaml`
- `Rule/Loon/AI/AI.lsr`
- `Rule/QuantumultX/ChinaBank/ChinaBank.list`

Example raw URL pattern after publishing the repository:

```text
https://raw.githubusercontent.com/<owner>/<repo>/<branch>/Rule/Clash/OpenAI/OpenAI.yaml
https://raw.githubusercontent.com/<owner>/<repo>/<branch>/Rule/Loon/OpenAI/OpenAI.lsr
https://raw.githubusercontent.com/<owner>/<repo>/<branch>/Rule/Loon/AI/AI.lsr
```

Selection policy: choose the first non-empty family in `native -> shadowrocket -> clash`, then merge only within that selected family.
Bundle policy: merge only the primary published variant from each member service, then normalize and deduplicate the combined stream.

Current bundles: ai, china, china-bank, commerce, gaming, google, social, streaming

Use `python -m egloon_rule_hub render-rules` to refresh rule artifacts only.

Use `python -m egloon_rule_hub bootstrap` after catalog changes to refresh rules, docs, and manifests together.
