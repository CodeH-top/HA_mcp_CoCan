# 小电拼 Home Assistant · MQTT 实验分支


**当前检出 `mqtt`，版本 0.4.1b1。** 默认安装请使用 [main 正式版](https://github.com/CodeH-top/HA_mcp_CoCan)。本分支新增自建 MQTT 接入和整机电源/重启/配置目标固件更新实体；未实机切换 Broker 或 OTA。请先阅读 [实现范围、固件配置与验证边界](docs/MQTT.md)。

HACS 如需试用，请显示测试版并选择对应预发布版本；不要把测试分支当成完整小程序替代。下面主线 MCP 安装说明仍适用于选择 MCP 连接方式的情况。
[![Build and Release](https://github.com/CodeH-top/HA_mcp_CoCan/actions/workflows/release.yml/badge.svg)](https://github.com/CodeH-top/HA_mcp_CoCan/actions/workflows/release.yml)
[![Release](https://img.shields.io/github/v/release/CodeH-top/HA_mcp_CoCan)](https://github.com/CodeH-top/HA_mcp_CoCan/releases)

通过制糖工厂官方 MCP 云服务接入小电拼，支持官方 App 与 Home Assistant 共存，无需切换设备的 MQTT 接入方式，也无需设备与 HA 位于同一局域网。

本仓库是 [Adisonyao/HA_mcp_CoCan](https://github.com/Adisonyao/HA_mcp_CoCan) 的维护分支，基于上游 v0.3.6。当前版本 **0.4.0** 提供内置 Lovelace 控制卡、可选局域网只读遥测、152 个实体的原生中英文翻译，并修复配置向导 500、MCP 会话与数据单位等问题。保持原有实体身份和设备绑定，升级不需要删除设备。

主线通过官方 MCP 控制，局域网 HTTP 只用于读数。独立的 [`mqtt` 分支](https://github.com/CodeH-top/HA_mcp_CoCan/tree/mqtt) 用于自建 Broker 方案，能力和验证边界见 [MQTT 说明](docs/MQTT.md)。
## 使用 HACS 安装和更新

1. 在 **HACS → 右上角菜单 → 自定义存储库** 添加 `https://github.com/CodeH-top/HA_mcp_CoCan`，类别选择 **集成**。
2. 搜索 **小电拼 Home Assistant（中文增强版）**，下载最新正式版本，然后重启 HA。
3. 前往 **设置 → 设备与服务 → 添加集成**，搜索 **小电拼Home Assistant**。
4. 填写设备专属 MCP 地址，默认使用 **Streamable HTTP**，按需填写认证 Token。

后续更新由 HACS 跟踪本仓库的 GitHub Releases，并下载 GitHub Actions 构建的 `mcp_cocan.zip`。

### 从上游版或手动安装版迁移

不要删除已经添加的小电拼设备或配置条目。先备份当前 `custom_components/mcp_cocan/`；如果 HACS 已登记上游仓库，先从 HACS 的自定义仓库列表移除该登记，再添加本仓库。下载本仓库版本覆盖同一个集成目录，重启即可保留配置与实体。不要同时让两个仓库管理同一个 `mcp_cocan` 集成，也不要使用 HACS 的卸载操作删除正在使用的集成。

## 手动安装

从 [本仓库 Releases](https://github.com/CodeH-top/HA_mcp_CoCan/releases) 下载 `mcp_cocan.zip` 和 `mcp_cocan.zip.sha256`。校验 SHA256 后，将 ZIP **内容**解压到 `/config/custom_components/mcp_cocan/`，确保该目录下直接存在 `manifest.json`，然后重启 HA。

发布 ZIP 根目录直接包含集成文件，适配 HACS `zip_release` 安装；不要再额外套一层 `mcp_cocan` 文件夹。

## 获取与填写连接参数

在小电拼 App / 小程序中进入 **设置 → 龙虾服务 → 其他**，找到提供给智能体的文本，从中复制设备专属的完整 MCP 服务器地址。推荐使用以 `/mcp` 结尾的地址，传输类型选择 **Streamable HTTP**。

| 参数 | 说明 |
| --- | --- |
| MCP Server 地址 | App 提供的完整设备专属地址，不要使用 SKILL.md 地址 |
| 传输类型 | 推荐 Streamable HTTP；兼容选项 SSE 在当前客户端中也以 HTTP POST 请求实现，并非独立的旧式 SSE 客户端 |
| 认证 Token | 只有服务端要求时填写，否则留空 |
| 设备名称 | 自定义显示名称 |
| 轮询间隔 | 默认 15 秒，允许 5–300 秒 |

设备专属地址包含访问凭据，请勿提交到仓库、公开 Issue 或分享截图中。配置本 HA 集成无需安装任何本地 AI skill。

完整的实读工具表和连接处理说明见 [MCP 接口核对](docs/MCP.md)。

## 功能与端口

支持 5 端口小电拼 CP-02 / CP-02S，总功率预算 160W。Port A 为 USB-A（端口索引 1，最高 60W）；C1–C4 为 USB-C（索引 2–5，最高 140W，受整机总功率限制）。

- 端口充电开关、分配功率上限、输出功率/电压/电流、温度状态与累计电量。
- 充电策略、温控模式、屏幕亮度；CP-02S 另支持屏显模式、待机动画和整点报时。
- PD 协商、连接设备、线缆与电池信息，以及设备型号、固件和 Wi-Fi 诊断信息。
- 152 个默认实体名称和控制选项随 HA 语言显示中文或英文；协议原始状态、自定义名称及实体配置 JSON 中的字段不进行强制翻译。

### 为什么没有整机开关机？

官方 MCP 接口没有整机开机、关机或重启方法，只提供 `turn_on_port` / `turn_off_port` 控制充电输出。这两个方法接受端口数组，因此协议可一次操作全部 5 个端口，但当前集成仅提供逐端口开关实体。关闭全部端口不等于整机断电，设备的 Wi-Fi 与控制服务仍会运行。

## 内置控制面板

集成加载后会自动注册 `custom:cocan-card`。刷新浏览器，在仪表盘编辑器添加“小电拼控制面板”，或使用 YAML：

```yaml
type: custom:cocan-card
# 多设备时可指定配置条目 ID；也可通过卡片编辑器选择。
# entry_id: ...
```

面板包含五口功率图、端口状态与 PD 信息、充电/屏幕选项、完整五口临时功率分配，以及复用 HA Recorder 的最近两小时曲线。UI 参考 KangCharge、CoCanBar，并为 HA 独立实现，详见 [引用和许可](docs/REFERENCES.md)。无需额外安装前端仓库，也不向浏览器发送 MCP 地址或凭据。

## 局域网 metrics.json：可选读取与回退

在集成的“配置”中填写 **局域网主机**（仅 IPv4 或主机名，不带 `http://`、端口和路径）。建议给小电拼保留 DHCP 地址。HA 必须能访问设备的 HTTP 80 端口；留空继续纯 MCP 模式。

每轮先核对设备首页 `window.__INFOZ.psn` 与配置设备序列号，再读取 `/metrics.json`。核验失败、超时、重定向、非法字段时放弃本地读数并保留云端方案；两条路径均失败才报告不可用。有效的本地电压、电流和功率预算优先，PD、温度、累计电量等仍取本轮云端数据。不会把上轮云数据伪装成本轮读取。

该接口不是完整控制协议，也没有稳定公开的版本契约。`session_charge` 原始单位不明确，不换算成 mWh；缺少的数据显示未知，不补零。只允许解析到私有 IPv4 地址，限制响应大小和超时，并禁止重定向。本实现已做协议及回退模拟验证，真实设备 LAN 兼容性须以配置的 IP 与固件实际返回为准。

### 当前限制与修复

- MCP 无整机电源、重启、OTA、固件更新查询、当前策略读取；不把“全部端口关闭”称为整机关机。
- 充电策略显示本次集成运行期间上次成功设置值，外部 App 改动无法同步。
- 空闲端口的充电状态不代表端口是否被禁用；未连接的 PD/线缆/电池字段可能未知。
- 修正 PD 工作电压/电流单位为 10mV/10mA；温度等级作为状态而非摄氏度；PSN/BSSID 保留文本。
- 云端不返回完整功率预算时，单口滑块拒绝写入。可在卡片明确填写全部五口预算，合计不得超过 160W；不会把其它未知端口设为零。
- 局域网提供离线基础遥测，不提供离线 MCP 控制。CP-02 不支持 CP-02S 专属屏幕功能，可禁用不适用实体。
- 自定义实体配置保持兼容；历史版本未隔离不同设备的默认 unique ID，因此本版主要验证已有单设备升级，不承诺多设备身份迁移。

## 开发、构建和发布

源码位于 `custom_components/mcp_cocan/`。本地可运行：

```sh
python3 scripts/build_release.py --check
```

GitHub Actions 在 main 提交、Pull Request 和手动触发时校验 Python/JSON、前端 JavaScript 语法、实体身份重复与翻译覆盖，并生成可下载的构建附件。发布新版本时：

1. 修改 `custom_components/mcp_cocan/manifest.json` 的版本号，并更新说明。
2. 提交并推送 main。
3. 创建并推送对应的 `v<版本号>` 标签，例如 `v0.4.0`。
4. Actions 检查标签与 manifest 版本一致，构建 ZIP 和 SHA256，自动发布到 GitHub Releases；HACS 从正式 Release 获取更新。

汉化通过 HA 的 `translation_key` 与 `translations/en.json`、`zh.json`、`zh-Hans.json` 实现，保持实体 ID 与设备命令参数不变。下拉实体状态使用规范的英文键（如亮度 `low`、待机动画 `clock`），HA 界面按语言显示中文；服务调用同时接受新版状态键和旧版标签。依赖旧状态字符串的自动化条件需相应调整。配置选项兼容修复移除了对新版 HA 只读 `OptionsFlow.config_entry` 的手动赋值。

## 致谢与许可

原作者：[Adisonyao](https://github.com/Adisonyao)，原始项目：[HA_mcp_CoCan](https://github.com/Adisonyao/HA_mcp_CoCan)。本维护分支保留原作者署名，并按 [GNU GPL v3](LICENSE) 继续发布。UI 参考项目的 MIT 许可原文见 [licenses](licenses/)，源码及发布包保留署名与引用。厂商 MCP 协议与服务由制糖工厂提供；本项目为第三方开源集成，与厂商无隶属关系。
