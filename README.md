# egloon_rule_hub

面向 Egern、Loon、Clash、QuantumultX、Shadowrocket、Surfboard 和 sing-box 的目标优先代理规则仓库。

这个项目不追求“全网最全”，而是追求“我们真正会用、能持续自动更新、来源清晰可追踪”。

## 项目目标

- 只跟踪实际需要的服务规则，不做无边界收录
- 用统一的中间模型管理规则，而不是把某一个客户端格式写死
- 为每个服务和每个合并包发布稳定的规则目录与文件路径
- 每个 `目标客户端 + 服务目录` 只选择一个最终上游家族，避免来源混杂
- 把 `Source/TXT/` 下的自维护规则作为一等输入源
- 通过 GitHub Actions 执行同步、构建、校验，尽量不占用 VPS 资源

## 仓库定位

这是一个可公开发布的规则生成仓库。

- 上游引用统一记录在 [ATTRIBUTION.md](ATTRIBUTION.md)
- 上游 README 抓取结果记录在 [dist/manifests/upstream_docs.json](dist/manifests/upstream_docs.json) 和 `dist/upstream-readmes/`
- 图标同步结果记录在 [dist/manifests/icons.json](dist/manifests/icons.json)
- 如果上游 README 不可用，清单会标记 `status: missing`
- 如果上游图标没有严格匹配成功，清单会保留未匹配原因，而不是猜测性补图
- `dist/` 中的内容是由上游规则源或 `Source/TXT/` 自维护源转换得到的生成产物

## 核心设计

### 1. 目标客户端优先

发布结果不是按“抓了哪些上游仓库”来组织，而是按“用户最终要给哪个客户端使用”来组织。最终产物统一落在：

```text
Rule/<Target>/<Service>/
Rule/<Target>/<Bundle>/
```

例如：

- `Rule/Egern/OpenAI/OpenAI.yaml`
- `Rule/Loon/OpenAI/OpenAI.lsr`
- `Rule/Clash/OpenAI/OpenAI.yaml`
- `Rule/QuantumultX/OpenAI/OpenAI.list`
- `Rule/Surfboard/OpenAI/OpenAI.list`
- `Rule/SingBox/OpenAI/OpenAI.json`

每个目录下会同时放：

- 规则文件
- `README.md`
- `icon.png`（仅当严格匹配到上游图标时生成）

### 2. 上游选择是严格的

同一个服务在同一个目标客户端下，按固定优先级选择上游家族：

```text
native -> shadowrocket -> clash
```

规则是：

- 命中第一个非空家族后停止
- 只在该家族内部做合并和去重
- 不跨家族混拼，避免把语义不同的规则源硬凑在一起

这意味着仓库支持多上游，但每个最终发布目录的来源是单一且可解释的。

### 3. 自维护 TXT 规则是一等输入

除了远程上游，还支持在 `Source/TXT/<Service>.txt` 直接维护规则。

这类 TXT 源会：

- 作为服务的规范输入
- 自动参与各客户端目标格式转换
- 自动生成对应服务目录下的 `README.md`
- 在 GitHub Actions 定时任务中被重新处理和发布

当前这一路径已用于例如：

- `Source/TXT/Feishu.txt`
- `Source/TXT/IyfTv.txt`
- `Source/TXT/AppleIntelligence.txt`

### 4. Bundle 是合并产物，不是额外维护一套规则

如 `AI`、`ChinaBank` 这类合并包，内部是基于已定义服务做聚合、去重、再发布。

这样可以同时满足两类需求：

- 直接使用合并后的大包
- 继续按单个服务自由组合

## 当前支持的目标格式

- Egern `rule-set` YAML
- Loon `.lsr`（当前默认输出为 `.lsr`）
- Clash / mihomo classical rule-provider YAML
- QuantumultX `.list`
- Shadowrocket `.list`
- Surfboard remote `RULE-SET` `.list`
- sing-box source rule-set JSON（`version: 1`）

## Surfboard 使用

`Rule/Surfboard/` 中的文件是不带策略名称的远程规则集，可在 Surfboard 配置的 `[Rule]` 中引用：

```ini
RULE-SET,https://raw.githubusercontent.com/<owner>/<repo>/<branch>/Rule/Surfboard/OpenAI/OpenAI.list,Proxy
```

转换器会将 `HOST` / `HOST-SUFFIX` / `HOST-KEYWORD` / `IP6-CIDR` 归一化为 Surfboard 官方格式，并保留官方文档明确支持的规则类型。`DOMAIN-REGEX` 和 `IP-ASN` 无安全等价映射，因此不会写入 Surfboard 产物。

Surfboard 格式依据：

- RULE-SET：https://getsurfboard.com/docs/profile-format/rule/ruleset/
- Domain Rules：https://getsurfboard.com/docs/profile-format/rule/domain/
- IP Rules：https://getsurfboard.com/docs/profile-format/rule/ip/
- User-Agent Rules：https://getsurfboard.com/docs/profile-format/rule/user-agent/

## sing-box / NekoBox 使用

`Rule/SingBox/` 中的 JSON 是 sing-box source rule-set，可作为 `route.rule_set` 的本地或远程规则集。例如：

```json
{
  "type": "remote",
  "tag": "OpenAI",
  "format": "source",
  "url": "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/Rule/SingBox/OpenAI/OpenAI.json"
}
```

产物使用 `version: 1`，以兼容从 sing-box 1.8.0 开始的 rule-set 实现。当前映射 `DOMAIN`、`DOMAIN-SUFFIX`、`DOMAIN-KEYWORD`、`DOMAIN-REGEX`、`IP-CIDR` 和 `IP-CIDR6`；`USER-AGENT`、`IP-ASN` 和 `GEOIP` 无法在 source rule-set 内直接等价表达，因此不会写入。

sing-box 格式依据：

- Rule Set：https://sing-box.sagernet.org/configuration/rule-set/
- Source Format：https://sing-box.sagernet.org/configuration/rule-set/source-format/

## 目录说明

- `catalog/sources.yaml`：上游源定义
- `catalog/targets.yaml`：启用的目标客户端定义
- `catalog/services.yaml`：服务清单，按目标和来源策略组织
- `catalog/bundles.yaml`：合并包定义
- `Source/TXT/`：自维护 TXT 规则源
- `src/egloon_rule_hub/`：抓取、解析、归一化、转换、文档渲染主逻辑
- `Rule/`：最终发布给各客户端直接引用的规则目录
- `dist/`：构建清单、来源快照、追踪元数据

## 本地使用

安装：

```bash
pip install -e .
```

常用命令：

```bash
python -m egloon_rule_hub validate-catalog
python -m egloon_rule_hub render-rules
python -m egloon_rule_hub render-manifests
python -m egloon_rule_hub render-docs
python -m egloon_rule_hub refresh-txt-sources
python -m egloon_rule_hub bootstrap
```

命令说明：

- `validate-catalog`：校验目录配置是否完整、可解析
- `render-rules`：生成规则文件
- `render-manifests`：生成服务、目标、Bundle 等清单
- `render-docs`：只重建 README 和归属说明，不重建规则文件
- `refresh-txt-sources`：刷新 `Source/TXT/` 下的自动生成源，目前包含 Feishu 官方白名单抓取
- `bootstrap`：一键执行校验、规则生成、README 跟踪、图标同步、公共说明渲染

## 自动化更新

仓库当前使用两个 GitHub Actions 工作流：

- `.github/workflows/validate.yml`
  - 在 `push`、`pull_request`、手动触发时运行
  - 用于做基础校验和构建冒烟检查
- `.github/workflows/sync-rules.yml`
  - 支持手动触发
  - 每日北京时间 `03:30` 定时执行一次
  - 自动刷新 `Source/TXT/`
  - 自动执行 `bootstrap`
  - 自动提交 `README.md`、`ATTRIBUTION.md`、`Rule/`、`dist/`、`Source/TXT/` 的更新

## 当前状态

当前仓库已经具备这些真实能力：

- 已接入真实上游规则源，并以 `blackmatrix7` 为当前主来源
- 已支持目标客户端优先的发布目录结构
- 已支持 Bundle 规则输出
- 已支持上游 README 跟踪与归属记录
- 已支持严格图标匹配与同步
- 已支持自维护 TXT 规则源自动转写与发布

这意味着仓库已经能跑通“抓取上游 -> 归一化 -> 转换目标格式 -> 生成 README -> 发布目录 -> 定时自动更新”的完整链路。

## 引用与说明

- Egern 规则文档：https://egernapp.com/zh-CN/docs/configuration/rules/
- Loon 文档索引：https://nsloon.app/docs/category/%E8%A7%84%E5%88%99/
- Loon 订阅规则说明：https://nsloon.app/docs/Rule/sub_rule/
- mihomo rule-providers：https://wiki.metacubex.one/en/config/rule-providers/content/
- QuantumultX 仓库：https://github.com/kjfx/QuantumultX
- blackmatrix7 规则仓库：https://github.com/blackmatrix7/ios_rule_script/tree/master/rule
- 上游归属记录：[ATTRIBUTION.md](ATTRIBUTION.md)
