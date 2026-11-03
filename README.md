# 小电拼 Home Assistant · 中文增强版

[![Build and Release](https://github.com/CodeH-top/HA_mcp_CoCan/actions/workflows/release.yml/badge.svg)](https://github.com/CodeH-top/HA_mcp_CoCan/actions/workflows/release.yml)
[![Release](https://img.shields.io/github/v/release/CodeH-top/HA_mcp_CoCan)](https://github.com/CodeH-top/HA_mcp_CoCan/releases)

通过制糖工厂官方 MCP 云服务接入小电拼，支持官方 App 与 Home Assistant 共存，无需切换设备的 MQTT 接入方式，也无需设备与 HA 位于同一局域网。

本仓库是 [Adisonyao/HA_mcp_CoCan](https://github.com/Adisonyao/HA_mcp_CoCan) 的维护分支，基于上游 v0.3.6。当前版本 **0.3.6.1** 补齐 152 个默认实体名称与 5 组控制选项的 HA 原生中英文翻译，并修复新版 Home Assistant 打开配置选项时的 500 错误。保留原有 domain、实体 unique ID 和设备绑定，不需要重新添加设备。用户自行设置的实体名称不会被翻译覆盖。

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

## 功能与端口

支持 5 端口小电拼 CP-02 / CP-02S，总功率预算 160W。Port A 为 USB-A（端口索引 1，最高 60W）；C1–C4 为 USB-C（索引 2–5，最高 140W，受整机总功率限制）。

- 端口充电开关、分配功率上限、输出功率/电压/电流、温度状态与累计电量。
- 充电策略、温控模式、屏幕亮度；CP-02S 另支持屏显模式、待机动画和整点报时。
- PD 协商、连接设备、线缆与电池信息，以及设备型号、固件和 Wi-Fi 诊断信息。
- 152 个默认实体名称和控制选项随 HA 语言显示中文或英文；协议原始状态、自定义名称及实体配置 JSON 中的字段不进行强制翻译。

### 为什么没有整机开关机？

官方 MCP 接口没有整机开机、关机或重启方法，只提供 `turn_on_port` / `turn_off_port` 控制充电输出。这两个方法接受端口数组，因此协议可一次操作全部 5 个端口，但当前集成仅提供逐端口开关实体。关闭全部端口不等于整机断电，设备的 Wi-Fi 与控制服务仍会运行。

### 当前限制

- 充电策略没有读取接口，初始状态可能为 `unknown`，外部 App 更改后无法自动同步。
- 未连接端口的 PD、线缆和电池字段显示未知属于正常情况。
- 上游仍有部分诊断字段类型或单位解析问题，例如 PD 状态温度、序列号/BSSID 格式、总分配功率；本次汉化未修复这些数据问题，不应将这些字段用于关键自动化。
- CP-02 不支持 CP-02S 专属屏幕功能；默认配置仍可能生成相应实体，可在实体设置中禁用。
- 总功率分配不得超过 160W；各端口滑块提交的是完整 5 端口数组。
- 当前通过云端轮询，依赖设备联网与厂商服务器，不提供本地离线控制。

## 开发、构建和发布

源码位于 `custom_components/mcp_cocan/`。本地可运行：

```sh
python3 scripts/build_release.py --check
```

GitHub Actions 在 main 提交、Pull Request 和手动触发时校验 Python/JSON、实体身份重复与翻译覆盖，并生成可下载的构建附件。发布新版本时：

1. 修改 `custom_components/mcp_cocan/manifest.json` 的版本号，并更新说明。
2. 提交并推送 main。
3. 创建并推送对应的 `v<版本号>` 标签，例如 `v0.3.6.1`。
4. Actions 检查标签与 manifest 版本一致，构建 ZIP 和 SHA256，自动发布到 GitHub Releases；HACS 从正式 Release 获取更新。

汉化通过 HA 的 `translation_key` 与 `translations/en.json`、`zh.json`、`zh-Hans.json` 实现，保持实体 ID 与设备命令参数不变。下拉实体状态使用规范的英文键（如亮度 `low`、待机动画 `clock`），HA 界面按语言显示中文；服务调用同时接受新版状态键和旧版标签。依赖旧状态字符串的自动化条件需相应调整。配置选项兼容修复移除了对新版 HA 只读 `OptionsFlow.config_entry` 的手动赋值。

## 致谢与许可

原作者：[Adisonyao](https://github.com/Adisonyao)，原始项目：[HA_mcp_CoCan](https://github.com/Adisonyao/HA_mcp_CoCan)。本维护分支保留原作者署名，并按 [GNU GPL v3](LICENSE) 继续发布。厂商 MCP 协议与服务由制糖工厂提供；本项目为第三方开源集成，与厂商无隶属关系。
