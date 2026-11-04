# MQTT 与 MCP 实体逐项对照（0.4.1b9）

本表覆盖默认的 152 个 MCP 实体。MQTT 使用相同的 type/unique_id，在已迁移条目上保留 entity_id/device_id；不自动切设备 Broker。新增 32 个 MQTT 实体（整机电源、重启、三个版本、当前/剩余预算、五口原始计数及 VID/PID），合计 184 个。**实体数量不代表数据都能获得**：16 个共享字段缺公开定义，保持未知，其余也取决于固件和设备返回。

MQTT 只使用 HA MQTT 集成，无 HTTP、MCP 或私有云查询。新增数据含精确字段身份；固件版本仅诊断，不提供 OTA。此轮仅模拟协议验证，没有在用户设备上验证这些新增 MQTT 字段/控制。

| 实体 unique_id | 类型 | 当前实现 | 数据来源与限制 |
| --- | --- | --- | --- |
| `total_power` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_1_power` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_1_voltage` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_1_current` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_1_temp` | sensor | 保留身份，未知 | 公开 schema 没有温度/温度等级字段，不把未定义的 field 4 当温度 |
| `port_1_connected` | sensor | 已接入，依赖端口推送 | 30 秒内 STREAM_PORT_STATUS；不使用过期推送 |
| `port_1_protocol` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_1_session_mwh` | sensor | 保留身份，未知 | session_charge 单位未明确；另加原始计数实体，不冒充 mWh |
| `port_2_power` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_2_voltage` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_2_current` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_2_temp` | sensor | 保留身份，未知 | 公开 schema 没有温度/温度等级字段，不把未定义的 field 4 当温度 |
| `port_2_connected` | sensor | 已接入，依赖端口推送 | 30 秒内 STREAM_PORT_STATUS；不使用过期推送 |
| `port_2_protocol` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_2_session_mwh` | sensor | 保留身份，未知 | session_charge 单位未明确；另加原始计数实体，不冒充 mWh |
| `port_3_power` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_3_voltage` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_3_current` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_3_temp` | sensor | 保留身份，未知 | 公开 schema 没有温度/温度等级字段，不把未定义的 field 4 当温度 |
| `port_3_connected` | sensor | 已接入，依赖端口推送 | 30 秒内 STREAM_PORT_STATUS；不使用过期推送 |
| `port_3_protocol` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_3_session_mwh` | sensor | 保留身份，未知 | session_charge 单位未明确；另加原始计数实体，不冒充 mWh |
| `port_4_power` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_4_voltage` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_4_current` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_4_temp` | sensor | 保留身份，未知 | 公开 schema 没有温度/温度等级字段，不把未定义的 field 4 当温度 |
| `port_4_connected` | sensor | 已接入，依赖端口推送 | 30 秒内 STREAM_PORT_STATUS；不使用过期推送 |
| `port_4_protocol` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_4_session_mwh` | sensor | 保留身份，未知 | session_charge 单位未明确；另加原始计数实体，不冒充 mWh |
| `port_5_power` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_5_voltage` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_5_current` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_5_temp` | sensor | 保留身份，未知 | 公开 schema 没有温度/温度等级字段，不把未定义的 field 4 当温度 |
| `port_5_connected` | sensor | 已接入，依赖端口推送 | 30 秒内 STREAM_PORT_STATUS；不使用过期推送 |
| `port_5_protocol` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_5_session_mwh` | sensor | 保留身份，未知 | session_charge 单位未明确；另加原始计数实体，不冒充 mWh |
| `port_1_vin` | sensor | 已接入，依赖端口推送 | 30 秒内 STREAM_PORT_STATUS；不使用过期推送 |
| `port_2_vin` | sensor | 已接入，依赖端口推送 | 30 秒内 STREAM_PORT_STATUS；不使用过期推送 |
| `port_3_vin` | sensor | 已接入，依赖端口推送 | 30 秒内 STREAM_PORT_STATUS；不使用过期推送 |
| `port_4_vin` | sensor | 已接入，依赖端口推送 | 30 秒内 STREAM_PORT_STATUS；不使用过期推送 |
| `port_5_vin` | sensor | 已接入，依赖端口推送 | 30 秒内 STREAM_PORT_STATUS；不使用过期推送 |
| `port_1_charging` | switch | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_2_charging` | switch | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_3_charging` | switch | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_4_charging` | switch | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_5_charging` | switch | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `charging_strategy` | select | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `temperature_mode` | select | 已接入，依赖配置推送 | 30 秒内新鲜配置；整套写入须保留报时/旋转等参数；落花无对应值不提供 |
| `display_brightness` | select | 已接入 | 独立只读亮度命令或推送；HA 预设 0/25/50/100%，不声称与 MCP 阈值相同 |
| `display_mode` | select | 已接入，依赖配置推送 | 30 秒内新鲜配置；整套写入须保留报时/旋转等参数；落花无对应值不提供 |
| `idle_display` | select | 已接入，依赖配置推送 | 30 秒内新鲜配置；整套写入须保留报时/旋转等参数；落花无对应值不提供 |
| `hourly_chime` | switch | 已接入，依赖配置推送 | 30 秒内新鲜配置；整套写入须保留报时/旋转等参数；落花无对应值不提供 |
| `product_family` | sensor | 已接入 | 优先 boot 白名单 product_family，否则显示 GET_DEVICE_INFO 原始 model |
| `max_power_budget` | sensor | 保留身份，未知 | 当前动态预算不是硬件额定上限；另加当前/剩余预算实体 |
| `device_psn` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `firmware_version` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `wifi_ssid` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `wifi_bssid` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `wifi_channel` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `wifi_protocol` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `wifi_rssi` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_1_pd_device` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_2_pd_device` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_3_pd_device` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_4_pd_device` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_5_pd_device` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_1_pd_brand` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_2_pd_brand` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_3_pd_brand` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_4_pd_brand` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_5_pd_brand` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_1_pd_cable` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_2_pd_cable` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_3_pd_cable` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_4_pd_cable` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_5_pd_cable` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_1_pd_cable_brand` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_2_pd_cable_brand` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_3_pd_cable_brand` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_4_pd_cable_brand` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_5_pd_cable_brand` | sensor | 已接入，条件性标识 | 按 VID 厂商表/线缆规格显示；不识别具体产品型号，无 VID 保持未知 |
| `port_1_pd_cable_v` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_2_pd_cable_v` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_3_pd_cable_v` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_4_pd_cable_v` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_5_pd_cable_v` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_1_pd_emarker` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_2_pd_emarker` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_3_pd_emarker` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_4_pd_emarker` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_5_pd_emarker` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_1_pd_rev` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_2_pd_rev` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_3_pd_rev` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_4_pd_rev` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_5_pd_rev` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_1_pd_op_v` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_2_pd_op_v` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_3_pd_op_v` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_4_pd_op_v` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_5_pd_op_v` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_1_pd_op_a` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_2_pd_op_a` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_3_pd_op_a` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_4_pd_op_a` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_5_pd_op_a` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_1_pd_temp` | sensor | 保留身份，未知 | 公开 schema 没有温度/温度等级字段，不把未定义的 field 4 当温度 |
| `port_2_pd_temp` | sensor | 保留身份，未知 | 公开 schema 没有温度/温度等级字段，不把未定义的 field 4 当温度 |
| `port_3_pd_temp` | sensor | 保留身份，未知 | 公开 schema 没有温度/温度等级字段，不把未定义的 field 4 当温度 |
| `port_4_pd_temp` | sensor | 保留身份，未知 | 公开 schema 没有温度/温度等级字段，不把未定义的 field 4 当温度 |
| `port_5_pd_temp` | sensor | 保留身份，未知 | 公开 schema 没有温度/温度等级字段，不把未定义的 field 4 当温度 |
| `port_1_pd_pdo` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_2_pd_pdo` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_3_pd_pdo` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_4_pd_pdo` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_5_pd_pdo` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_1_pd_cable_active` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_2_pd_cable_active` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_3_pd_cable_active` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_4_pd_cable_active` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_5_pd_cable_active` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_1_pd_usb_speed` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_2_pd_usb_speed` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_3_pd_usb_speed` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_4_pd_usb_speed` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_5_pd_usb_speed` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_1_pd_dual_role` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_2_pd_dual_role` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_3_pd_dual_role` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_4_pd_dual_role` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_5_pd_dual_role` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_1_power_alloc` | number | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_2_power_alloc` | number | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_3_power_alloc` | number | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_4_power_alloc` | number | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_5_power_alloc` | number | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `total_allocated_power` | sensor | 已接入 | 公开 MQTT 字段/命令，沿用现有实体转换及 ID |
| `port_1_pd_power` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_2_pd_power` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_3_pd_power` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_4_pd_power` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_5_pd_power` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_1_pd_battery_pct` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_2_pd_battery_pct` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_3_pd_battery_pct` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_4_pd_battery_pct` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_5_pd_battery_pct` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_1_pd_battery` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_2_pd_battery` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_3_pd_battery` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_4_pd_battery` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
| `port_5_pd_battery` | sensor | 已接入，条件性 PD | 仅充电 PD 口；GET_PORT_PD_STATUS 或本轮新推送；不支持/失败只令该口字段未知 |
