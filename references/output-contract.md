# 输出 Schema 与下游契约

本文件只用于完整可追溯、正式交付或高风险输出前的材料清单契约。

## 升级映射

从 read-session.json 升级到 material_inventory.json 时：
- required_explicit 字段必须显式存在
- required_if_applicable 按材料类型判断
- optional 字段存在就传递

详见 references/read-session-contract.md
