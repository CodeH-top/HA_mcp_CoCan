# 参考来源与许可

2026-11-04 对照以下资料实现 HA 原生组件。没有打包或启动 macOS 应用，也没有安装 AI skill。

- [KangCharge](https://github.com/LeiZiKang/KangCharge)：五口功率图、模式与屏幕控制布局参考。MIT；保留全文于 `licenses/KangCharge-MIT.txt`。
- [CoCanBar](https://github.com/yangyihang96/CoCanBar)：局域网读数、设备身份核验、云端回退、PD 单位与曲线展示设计参考。MIT；保留全文于 `licenses/CoCanBar-MIT.txt`。
- [官方 AI 接入说明](https://thecandysign.com/cocan/zh/ai-integration/)：MCP、SSE/Streamable HTTP、Prometheus/JSON 能力边界。
- [官方 MQTT 参考](https://thecandysign.com/cocan/zh/mqtt/reference/)：主题、Protobuf 消息、端口控制、设备电源及 OTA 契约。
- [IonBridge 开源固件](https://github.com/ifanrx/IonBridge)：核对主题十进制命令号与公开 schema。其许可与本项目 GPL 不同，本项目不复制、再分发固件源码或生成的 protobuf 文件；MQTT 协议编解码按公开字段独立实现。

本项目仍采用原作者 GPL-3.0 许可；界面为独立编写的 HA Web Component，未复制 SwiftUI 界面源码、图标或截图。KangCharge 与 CoCanBar 的署名和 MIT 全文一并保留，发布包也包含引用与许可说明。

## 本次读取的参考版本

- KangCharge: `160ed114df6a3e704498cc9acb626a7572f979ee`
- CoCanBar: `b5ab1625d67e0c692d15cbc83e29135b8665c6f8`
- IonBridge: `2372580e728ab4309634594cc38bda38b8d2d362`

## 概览卡片的具体界面参考（0.4.1b7）

参考版本与上列 commit 相同。本轮重新阅读 KangCharge 的 `App/DashboardView.swift`、`App/PortViews.swift`、`Shared/CableDiagram.swift`，以及 CoCanBar 的 `Sources/CoCanBar/PanelView.swift`、`PowerDiagram.swift`、`PortChart.swift`。采用五口数字卡、线缆汇入充电器机身、奶油底色与橙色强调、紧凑端口行及点选详情的交互结构，独立实现为三张 HA Lovelace 卡片。SVG 机身与线缆为本项目绘制，没有复制项目图片、SwiftUI 代码或素材。

## MQTT 数据补全（0.4.1b9）

`mqtt_data.py` 的 USB VID 厂商名称表改编自 CoCanBar `Sources/CoCanKit/PortIdentity.swift`（同上 commit，MIT，Copyright (c) 2026 yangyihang96）。保留文件内署名及 licenses/CoCanBar-MIT.txt；线缆电压/USB速度编号参照该文件的USB规格映射。只按厂商ID给品牌和规格标签，不复制云端产品库、不猜设备型号。其余协议字段独立实现。
