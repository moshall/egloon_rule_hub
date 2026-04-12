# egloon_rule_hub Architecture

本文件面向 agent 和维护者。

它不是给普通规则使用者看的快速上手文档。普通使用方式、目录引用方式、GitHub Actions 行为请优先看 [README.md](../README.md)。本文件只解释工程结构、生成链路、关键约束，以及后续二次开发时不要破坏的设计边界。

如果你是新接手这个仓库的 agent，开始改代码前先读完本文件，再读 [catalog/services.yaml](../catalog/services.yaml) 和 [src/egloon_rule_hub/build.py](../src/egloon_rule_hub/build.py)。

## 1. 系统定位

这个仓库的目标不是“收集最多规则”，而是把一组明确选定的服务规则，稳定地发布为多个客户端可直接引用的目录结构。

核心思路是：

1. 上游规则只是输入，不直接决定最终目录结构。
2. 仓库内部先把不同来源解析成统一 `Rule(type, value)` 中间模型。
3. 再按目标客户端重新发射为 `Egern / Loon / Clash / QuantumultX / Shadowrocket` 各自的规则文件。
4. 同时为每个输出目录生成 README、上游追踪信息、图标和 manifest。

最终发布目录固定落在：

```text
Rule/<Target>/<Service>/
Rule/<Target>/<Bundle>/
```

## 2. 关键目录职责

- [catalog/](../catalog)
  - 仓库的声明式配置层。
  - `sources.yaml` 定义上游仓库或远程源。
  - `targets.yaml` 定义目标客户端与输出扩展名。
  - `services.yaml` 定义服务、目标来源、fallback 关系。
  - `bundles.yaml` 定义合并包。

- [src/egloon_rule_hub/](../src/egloon_rule_hub)
  - 主逻辑实现。
  - `model/` 是配置模型和发布模型。
  - `sources/` 负责把 `SourceRef` 解析成真实 URL。
  - `parsers/` 把各种上游格式转成统一 `Rule`。
  - `normalize/` 负责合并和去重。
  - `emitters/` 把统一 `Rule` 输出为目标客户端格式。
  - `docs/` 负责生成各规则目录 README。
  - `icons/` 负责图标同步。
  - `upstream_docs/` 负责抓取上游 README 并生成追踪清单。

- [Source/TXT/](../Source/TXT)
  - 自维护规则输入源。
  - 这里的 TXT 会被当成一等输入源，自动参与后续转换和发布。

- [Rule/](../Rule)
  - 最终发布产物。
  - 这里的文件原则上都视为生成物，不应手改。

- [dist/](../dist)
  - 生成出来的追踪信息和 manifest。
  - 包括 `services.json`、`upstream_docs.json`、图标清单、抓取到的上游 README 快照等。

## 3. 运行主链路

命令入口在 [cli.py](../src/egloon_rule_hub/cli.py)。

最重要的命令是：

```bash
python -m egloon_rule_hub bootstrap
```

`bootstrap` 当前执行顺序是：

1. `load_catalog()` 读取 `catalog/`
2. `build_all_target_artifacts()` 构建所有服务的目标产物
3. `render_target_artifacts()` 写入 `Rule/`
4. `_render_manifests()` 写入 `dist/manifests/`
5. `build_upstream_docs()` 刷新上游 README 追踪
6. `sync_service_icons()` 刷新图标
7. `write_markdown_docs()` 重建 `Rule/*/*/README.md`

如果你只想验证配置是否成立，用：

```bash
python -m egloon_rule_hub validate-catalog
```

如果你改动了规则构建逻辑，默认以 `bootstrap` 作为最终验证命令。

## 4. 统一数据模型

整个仓库的核心中间模型是 [Rule](../src/egloon_rule_hub/model/rules.py)：

```python
Rule(type: str, value: str)
```

只要进入这个模型，后面的合并、去重、转写、README 生成都会基于它运行。

发布层模型在 [publish.py](../src/egloon_rule_hub/model/publish.py)：

- `TargetArtifact`
- `TargetArtifactVariant`
- `SelectedSourceEntry`

这里记录了：

- 这个目标最终选中了哪个来源家族
- 它是不是 native
- 它是不是转换产物
- 当前服务有哪些已发布变体
- 每个变体对应哪些真实上游文件

README 生成和产物追踪都依赖这些对象。

## 5. 不能破坏的设计约束

### 5.1 目标优先，不是上游优先

这个仓库最终按目标客户端组织产物，而不是按上游仓库组织。

所以不要把“上游目录结构”直接映射成仓库最终目录结构。上游只是输入。

### 5.2 每个目标只选择一个来源家族

当前默认优先级是：

```text
native -> shadowrocket -> clash
```

约束是：

1. 命中第一个非空家族后停止。
2. 只在该家族内部做合并和去重。
3. 不跨家族混拼。

这条约束是为了避免把语义不同的规则源硬拼在一起，导致 README 和使用说明失真。

### 5.3 Bundle 只聚合已存在服务

`AI`、`ChinaBank` 之类的 Bundle 不是独立来源，而是对已定义服务的再聚合。

Bundle 的职责只有：

1. 读取各服务已构建好的规则流
2. 合并
3. 去重
4. 输出为 `Rule/<Target>/<Bundle>/`

不要为 Bundle 单独重新发明来源逻辑。

### 5.4 `Rule/` 和 `dist/` 默认视为生成物

如果你需要改输出，请改：

- `catalog/`
- `src/egloon_rule_hub/`
- `Source/TXT/`

不要直接手改 `Rule/` 或 `dist/` 里的内容，然后把它当成长期正确状态。

## 6. 自动发现上游变体

这是当前架构里最重要的新能力之一。

历史上，像 `Google` 这种服务曾经手写过多个 target variant。现在已经改成全局自动发现，不再鼓励为单个服务写特判。

核心逻辑在 [build.py](../src/egloon_rule_hub/build.py)：

- `_fetch_repo_tree()`
- `_discover_source_ref_variants()`
- `_auto_discovered_target_variants()`

工作方式是：

1. 先按目标的 fallback 规则选出本次实际使用的来源家族。
2. 如果该 target 在 `catalog/services.yaml` 里已经显式声明了 `variants`，则完全尊重显式配置，不做自动发现。
3. 如果没有显式 `variants`，则从当前选中的来源家族里取出 `SourceRef`。
4. 对支持 GitHub tree API 的来源，读取整个仓库 tree。
5. 在“同目录、同后缀、同服务名前缀”的条件下查找变体文件。

当前匹配规则是：

- 目录相同
- 文件后缀相同
- 文件 stem 匹配：

```text
^ServiceName(?:[_.-].+)?$
```

例如以 `Google` 为基准，可能发现：

- `Google`
- `Google_Resolve`
- `Google_No_Resolve`

例如以 `ChinaMax` 为基准，可能发现：

- `ChinaMax`
- `ChinaMax_Domain`
- `ChinaMax_IP`
- `ChinaMax_Classical_No_Resolve`

自动发现后的约束：

- 与当前选中的来源家族保持一致
- 主变体优先使用与服务名完全相同的文件
- 其余变体作为同目录下的附加发布文件

这套能力是在提交 `ac16d0e` 引入并跑通的。以后如果出现“某个服务只有一个文件被发布，但上游其实有多个文件”，优先检查这条链路，而不是直接给该服务补手写 case。

## 7. 原生裸项解析规则

自动发现变体之后，不能再假设上游所有文件都已经是 `TYPE,value` 形式。

真实上游里存在这些原生写法：

- 裸精确域名
  - 例如 `books.itunes.apple.com`
- 裸后缀域名
  - 例如 `.apple.com`
  - 例如 `+.cn`
- 裸 CIDR
  - 例如 `17.0.0.0/8`
  - 例如 `2403:300::/32`
- 裸 ASN
  - 例如 `132203`

统一解析逻辑放在 [parsers/common.py](../src/egloon_rule_hub/parsers/common.py) 的 `parse_standard_or_raw_rule()`。

当前归一化规则是：

- `TYPE,value` -> 原样解析
- 裸精确域名 -> `DOMAIN`
- `.example.com` / `+.example.com` / `+.cn` -> `DOMAIN-SUFFIX`
- 裸 IPv4/IPv6 CIDR -> `IP-CIDR` / `IP-CIDR6`
- 裸数字 -> `IP-ASN`

这套共享逻辑已经接到：

- [parsers/clash.py](../src/egloon_rule_hub/parsers/clash.py)
- [parsers/loon.py](../src/egloon_rule_hub/parsers/loon.py)
- [parsers/shadowrocket.py](../src/egloon_rule_hub/parsers/shadowrocket.py)

后续如果遇到新的上游原生写法，应优先在 `parsers/common.py` 做泛化支持，而不是只修某一个 parser，或者只修某一个服务。

## 8. README、图标、追踪信息的边界

### README

每个 `Rule/<Target>/<Service>/README.md` 都是生成的。

README 的职责不是“自己发明使用说明”，而是：

1. 说明当前目录的目标客户端和服务
2. 说明当前目录发布了哪些变体
3. 记录每个变体最终选择了哪个上游文件
4. 尽可能保留上游 README 原文和来源链接

因此 README 很长是正常的，不应把它当成人手维护文档。

### 图标

图标同步逻辑在 [icons/sync.py](../src/egloon_rule_hub/icons/sync.py)。

当前策略是严格匹配，不猜测：

- 找到严格匹配则写入 `icon.png`
- 找不到则在 README / manifest 里标记 unavailable

### 上游 README 追踪

相关逻辑在：

- [upstream_docs/build.py](../src/egloon_rule_hub/upstream_docs/build.py)
- [upstream_docs/fetch.py](../src/egloon_rule_hub/upstream_docs/fetch.py)

产物主要落在：

- [dist/manifests/upstream_docs.json](../dist/manifests/upstream_docs.json)
- [dist/upstream-readmes/](../dist/upstream-readmes)

如果 README 追踪表现异常，先查这里，不要先怀疑规则生成逻辑。

## 9. 自维护 TXT 的边界

`Source/TXT/` 是一等输入源，但它和远程上游不同。

约束是：

1. TXT 文件名决定服务名。
2. TXT 内容会被解析为统一 `Rule`。
3. 这些服务的 `origin.kind` 会标记为 `self_maintained`。
4. 这类服务不依赖远程上游 tree 自动发现变体，除非以后显式扩展这项能力。

当前这条链路主要由这些模块负责：

- [txt_sources/manual.py](../src/egloon_rule_hub/txt_sources/manual.py)
- [txt_sources/feishu.py](../src/egloon_rule_hub/txt_sources/feishu.py)
- [model/catalog.py](../src/egloon_rule_hub/model/catalog.py)

如果你要增强 TXT 输入能力，优先从 `txt_sources/` 层扩展，不要把 TXT 特殊逻辑散落到 `build.py` 里。

## 10. 二次开发建议

### 10.1 优先做泛化，不要做单服务特判

如果一个问题只在 `Google` 上看起来最明显，也先假设别的服务迟早会遇到。

优先排查：

1. 变体发现规则是否过窄或过宽
2. parser 是否不支持某种上游原生格式
3. README 生成是否只展示了单一变体
4. emitter 是否丢失了某些 rule type

最后才考虑对单服务单独声明 `variants`

### 10.2 改配置和改机制的边界

这两类问题要分开：

- “这个服务来源填错了” -> 改 `catalog/services.yaml`
- “这一类服务都没正确发现多文件” -> 改 `build.py`
- “这一类原生规则都解析失败” -> 改 `parsers/common.py`
- “这一类目标输出格式不对” -> 改 `emitters/`

### 10.3 修改后至少做这三个验证

```bash
PYTHONPATH=src python3 -m egloon_rule_hub validate-catalog
PYTHONPATH=src python3 -m egloon_rule_hub bootstrap
git status --short
```

期望结果：

1. `validate-catalog` 成功
2. `bootstrap` 成功
3. 如果没有预期外改动，工作树应只包含你本次想要的生成变化

### 10.4 抽查代表性目录

涉及多文件或 parser 改动时，至少抽查这些目录：

- [Rule/Clash/Google](../Rule/Clash/Google)
- [Rule/Clash/China](../Rule/Clash/China)
- [Rule/Clash/ChinaMax](../Rule/Clash/ChinaMax)
- [Rule/Shadowrocket/Apple](../Rule/Shadowrocket/Apple)
- [Rule/Loon/Google](../Rule/Loon/Google)

这些目录能覆盖：

- 单服务双变体
- domain/classical/no-resolve 多形态
- 裸域名 / 裸 CIDR / 裸 ASN
- native 和 converted 两类输出

## 11. 给未来 agent 的一句话总结

这个仓库的本质是：

“把受控的服务清单，经过单一家族选择、统一规则模型、目标格式转写、文档追踪和图标同步，发布为稳定可引用的多客户端规则目录。”

如果你后续要继续迭代，请优先维护这几个事实：

1. 输出目录稳定
2. 来源选择可解释
3. README 和上游证据一致
4. 新能力尽量全局化，不把系统重新做回单服务特判集合
