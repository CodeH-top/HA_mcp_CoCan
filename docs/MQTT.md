# MQTT 能力与独立分支

MQTT 实现位于 `mqtt` 分支，主线仍用官方 MCP，不会自动修改设备的 Broker。MQTT 需要 HA 的 MQTT 集成和可访问的自建 Broker；设备切换接入方式可能影响官方 App 的部分云功能，请先阅读官方接入说明。

## 公开协议能做到什么

| 功能 | MCP | MQTT 公开协议 |
| --- | --- | --- |
| 基础遥测、端口输出控制 | 支持 | 支持 |
| 当前充电策略读取 | 不支持 | 支持 |
| 整机电源、重启 | 不支持 | 支持，区别于物理切断电源 |
| 屏幕、端口配置、PD、Wi-Fi 管理 | 部分 | 多类命令，随固件版本变化 |
| OTA 发起与升级状态 | 不支持 | START_OTA 与升级遥测 |
| 自动发现最新固件 | 不支持 | 未见公开的固件版本目录或查询命令 |
| 账号、订阅、素材授权、云统计 | 不支持 | 无法单靠设备 MQTT 复刻 |

因此不能声称完整复刻小程序。OTA 执行命令不等于更新检测；没有可信版本目录时必须显示未知，不能显示“已是最新”。不执行猜测版本的自动 OTA。

## 协议注意事项

官方请求 topic 为 `device/<psn>/enduser/request/<十进制命令号>`，响应为 `.../response/<十进制命令号>`，载荷为 protobuf。命令号与 CommandRequest 的 oneof 字段号不同。响应必须匹配设备、命令、请求 ID 与成功状态；不能使用 retained 响应完成新请求。

官网 schema 与开源固件的屏幕配置命令号、字段号有差异，不能盲目把不同版本混用。MCP 地址中的访问密钥不用于 MQTT 数据包，Broker 认证、TLS 和 ACL 在 HA MQTT 集成配置。

## 文档与许可

- [官方 MQTT 参考](https://thecandysign.com/cocan/zh/mqtt/reference/)
- [官方 AI/MCP 接入](https://thecandysign.com/cocan/zh/ai-integration/)
- [Command schema](https://thecandysign.com/cocan/proto/command.proto)
- [Data types](https://thecandysign.com/cocan/proto/data_types.proto)
- [Telemetry schema](https://thecandysign.com/cocan/proto/telemetry.proto)

协议字段独立实现；没有复制或分发 IonBridge 的固件源码或生成 protobuf，避免混用其硬件/商业许可。
