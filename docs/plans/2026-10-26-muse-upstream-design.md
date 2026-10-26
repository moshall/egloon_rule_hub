# Muse 上游调查与自动更新设计

调查日期：2026-10-26，Asia/Singapore。用户选择以一份 Muse 规则覆盖整个 Meta 系。实现采用 v2fly 的完整 Meta 域名分类，复用现有递归解析、多客户端转换和每日同步流程。

## 上游调查结果

| 上游 | 已确认的内容 | 接入选择 |
| --- | --- | --- |
| [v2fly data/meta](https://github.com/v2fly/domain-list-community/blob/master/data/meta) | 根分类列出 Meta 域名，并引用 Facebook、开发者工具、Instagram、Messenger、Oculus、Threads、WhatsApp 分类 | 作为唯一规则主源，递归更新 |
| [v2fly AI 分类](https://github.com/v2fly/domain-list-community/blob/master/data/category-ai-!cn) | 收录 meta.ai、metaaivm.com、muse.ai | 用于交叉核对；整份 AI 分类包含其他厂商，不直接导入 |
| [blackmatrix7 Facebook](https://github.com/blackmatrix7/ios_rule_script/blob/master/rule/Clash/Facebook/Facebook.yaml) | 包含 Meta 社交与共享 CDN 等宽泛规则；仓库树未发现独立 Muse 或 MetaAI 分类 | 保留原 Facebook 服务，Muse 不拼接该来源 |
| [MetaCubeX Meta 产物](https://github.com/MetaCubeX/meta-rules-dat/blob/meta/geo/geosite/meta.yaml) | 已有完整 Meta 分类；AI 分类也包含上述三个 AI 域名 | 用作交叉核对；其构建工作流已拉取 v2fly，并非完全独立的另一份证据 |
| [metamuse-rules](https://github.com/kkykkky/metamuse-rules) | 有 Muse 专用域名和 IP 文件，域名注释记录账号、Graph 等连接线索 | 作为依赖排查线索，不作为自动更新主源 |

v2fly 使用 [MIT License](https://github.com/v2fly/domain-list-community/blob/master/LICENSE)。MetaCubeX 的[构建工作流](https://github.com/MetaCubeX/meta-rules-dat/blob/master/.github/workflows/run.yml)会拉取 v2fly；同时收录二者会增加重复来源。

metamuse-rules 的 README 声称由作者本机 launchd 每天更新，公开树只包含 README 和两份产物，没有维护脚本。其 IP 文件说明这些地址与其他 Meta 产品共享；不能把 DNS 解析得到的地址当成 Muse 专属地址。

## 官方域名证据

[Meta 官方 Muse 公告](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/)链接到 muse.ai，并介绍 Muse Secure VM。[Meta Model API 官方文档](https://dev.meta.ai/docs/overview)明确使用 `https://api.meta.ai/v1`，Muse Code 安装入口也位于 dev.meta.ai。

这些官方链接支持纳入 muse.ai 与 meta.ai；metaaivm.com 的归类依据是 v2fly 的 Meta 和 AI 两份分类，不能把它表述为官方公开的完整网络白名单。账号、Graph、CDN 等依赖在全 Meta 域名范围内统一分流，无需逐个猜测 AI 专属端点。

## 实现范围

`catalog/services.yaml` 注册 Muse，启用全部七个客户端；`catalog/supplements.yaml` 指向 `v2fly_domain_list` 的 `data/meta`。这里的 supplement 是已有构建接口名称，Muse 没有其他主源，因此该入口直接提供整份规范规则。

当前递归读取 8 个文件：meta、facebook、facebook-dev、instagram、messenger、oculus、threads、whatsapp。抓取并去重后得到 555 条域名规则，类型为 DOMAIN 和 DOMAIN-SUFFIX。产物位于 `Rule/<Target>/Muse/`，每个目录包含规则及来源说明。

该范围包括账号、社交、开发者与 CDN 等上游收录的域名。它不是 Meta 官方所有资产的穷尽清单，也不包含 Meta ASN 或共享 IP 网段。上游未来新增 `include:` 会由现有解析器递归展开；新域名和删除也会在下次成功构建时反映。

## 自动更新与使用

现有 `.github/workflows/sync-rules.yml` 每日 19:30 UTC，即新加坡和北京时间次日 03:30，执行 bootstrap 并提交生成产物。Muse 会与其他服务一起更新，无需本机常驻任务。修改仍需推送到 GitHub 默认分支，远端定时任务才会使用新配置。

独立 Muse 未加入 AI bundle，以免已有 AI 订阅因此接管整个 Meta 社交网络。需要同一出口时，订阅 Muse 并将其放在 Facebook、Instagram、WhatsApp 等重叠规则之前。域名分流不改变服务端的账号和地区资格判断。

## 验证与仓库现状

目录配置校验通过；现有 15 个单元测试通过。使用真实上游构建全部七个目标，每个目标均得到 555 条规则，并检查 meta.ai、muse.ai、metaaivm.com、Facebook、Instagram、Messenger、WhatsApp、Threads、Oculus 等代表域名。

本地未执行全仓 bootstrap，避免为此次接入重写无关服务；Muse 使用现有构建器和渲染器定向生成。现有工作流会在 GitHub 对全仓执行 bootstrap。真实账号登录、对话及所有 App 功能仍需通过实际客户端流量验证。

上游仓库同时跟踪 ESPN 和 Espn 目录，当前 Mac 的文件系统发生大小写碰撞，克隆后已有 8 处差异。本次保留这些原始差异，未修复或提交它们。
