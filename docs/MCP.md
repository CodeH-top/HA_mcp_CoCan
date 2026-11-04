# 官方 MCP 接口核对

入口说明：[官方 AI 集成](https://thecandysign.com/cocan/zh/ai-integration/)。设备地址由 App 的“设置 → 龙虾服务 → 其他”提供，访问路径本身含密钥；不要把实际地址提交到仓库。无需安装本地 AI skill。

2026-11-04 用设备专属 Streamable HTTP 地址实际完成 initialize、tools/list 和只读 tools/call，工具共 18 个。服务能力可能随厂商版本变化，运行时以 tools/list 为准。

| 工具 | 参数 | 用途 |
| --- | --- | --- |
| get_charging_status | 无 | 充电位图，不能视为端口启用状态 |
| get_device_info | 无 | 序列号、版本与网络信息 |
| get_display_config | 无 | 屏幕配置 |
| get_machine_facts | 无 | 型号与功率限制 |
| get_port_details | 无 | 五口基础遥测 |
| get_port_pd_status | 无 | PD、线缆和电池状态 |
| get_port_stats | port | 单口状态 |
| get_temperature_mode | 无 | 温控模式 |
| set_charging_strategy | strategy | 0/1/6/7/8，包含 MCP 的小家电模式 |
| set_display_intensity | level | 关/低/中/高 |
| set_hourly_chime | enabled | 整点报时 |
| set_idle_display | idle_display | 待机动画 |
| set_port_power_allocation | power_allocation | 完整五口预算数组 |
| set_status_display_mode | mode | 屏幕模式 |
| set_temperature_mode | mode | 0 性能优先 / 1 温控优先 |
| set_usba_charging_mode | 无 | 小家电/模拟 A 口模式 |
| turn_off_port | ports | 关闭指定端口，MCP 编号 1–5 |
| turn_on_port | ports | 开启指定端口，MCP 编号 1–5 |

没有公开返回整机电源、重启、OTA、最新固件、当前充电策略读取工具。MCP 的小家电策略 6 与 MQTT 官网页面枚举不同，不能假设两套协议完全等价。

## 客户端处理

- 一个轮询周期复用一次已初始化 session，而不是每个传感器新建会话。
- 同时接受 JSON 和 HTTP POST SSE 响应，匹配 JSON-RPC 请求 ID，支持工具列表分页。
- 官方 `/sse` 链接规范化到同设备 `/mcp`；不声称支持任意服务器的旧式 GET SSE 双通道实现。
- 设置总超时、连接超时和 1 MiB 响应上限；拒绝跳转，不把设备访问密钥发送到重定向目的地。
- MCP JSON-RPC error、isError、结构化失败结果必须向 HA 报错；控制失败不会显示为成功。
- 不向前端暴露私有 URL/认证头，不在错误文本中输出响应全文和访问密钥。

只读核对并未执行真实供电切换、功率分配或屏幕控制。
