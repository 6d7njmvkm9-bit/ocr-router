# 统一材料读取入口

## 一、核心规则

1. 先读材料，再做分析
2. 不做模式前置筛选
3. 按读取路径选工具：direct-ocr / complex-parse / 直接文本 / 视觉复核
4. 只有高风险输出才补门禁
5. 不把工具调用当完成
6. 不猜测
7. 读取不产生业务结论

## 二、术语边界

- 普通读取：读出材料，写入 read-session.json
- 普通分析：基于已读材料做事实梳理
- 高风险输出：确定责任、金额、策略等，需补门禁

普通读取交接、read-item/read-session schema、升级映射见 references/read-session-contract.md
