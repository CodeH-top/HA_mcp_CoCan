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


## 五口平铺与功率分组（0.4.1b18，2026-11-06）

再次核对 GitHub main：KangCharge `160ed114df6a3e704498cc9acb626a7572f979ee`、CoCanBar `b5ab1625d67e0c692d15cbc83e29135b8665c6f8`，与前述参考版本一致。阅读 KangCharge 的 `App/DashboardView.swift`、`App/PortViews.swift`、`Shared/Theme.swift`，CoCanBar 的 `Sources/CoCanBar/PanelView.swift`、`PowerDiagram.swift`、`Theme.swift`。借鉴总功率/模式的视觉层级、紧凑端口标识与读数分组；独立实现 HA 主题化功率分布条、全部端口平铺、供电开关和响应式分栏。C1/C2/C3/C4/A 为用户指定的显示顺序，协议与实体身份不变。未复制 SwiftUI 源码、图标或截图，既有署名与 MIT 许可继续随包分发。


## 官方小程序视觉参考（0.4.1b19，2026-11-06）

用户提供 7 张官方小程序截图，涵盖管家、电控、模式、设置；并明确授权检查本机微信小程序资源。通过本机缓存中小电拼设备包（缓存版本 298）的编译页面样式核对：背景 `#F8F5EC`、卡片 `#FFFFFF`、文字 `#121212`、强调 `#FF4600` / `#FF4719`、模式强调 `#FFA51E`。参考大号功率、白色圆角分区、橙色柱形图与模式选中态，独立实现 HA 原生卡片。

本机缓存是编译产物，不等于官方完整开发源码。官方小程序不在本仓库采用的开源许可之内；本仓库及发布包未复制或分发其源码、编译包、图片、图标、字体或业务资源，也未读取微信聊天记录或复制微信登录数据。这里记录设计参考与来源，不将官方素材声明为本项目资产。
