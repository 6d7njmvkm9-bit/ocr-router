# 变更日志

## [1.0.3] - 2026-06-25

### 新增
- 新增普通读取 read-session 交接契约文档
- 新增 _read_item.json fragment 作为各读取路径统一输出格式
- 新增 scripts/update-read-session.py 汇总器
- 新增 scripts/test_update_read_session.py 测试（10 个用例，25 项断言全部通过）

### 调整
- 普通读取不跑完整门禁，但必须写入 read-session.json
- 高风险输出前必须显式指定 --require-scope strategy 或 formal-document
- 明确 read-session.json 到 material_inventory.json 的升级映射
- 修正 PDF/Office 读取路径表述歧义
- validate-material-reading.py 的 --require-scope 改为 required

## [1.0.2] - 2026-06-25
- 路由顺序改为路径优先
- 普通读取不默认触发完整门禁
- Read 看图仅作为 OCR 不足时的复核步骤

## [1.0.1] - 2026-06-22
- 全面移除免 Token 提取路径
- PaddleOCR 默认模型升级为 PaddleOCR-VL-1.6

## [1.0.0] - 2026-06-21
- 将 legal-ocr 整合为 ocr-router 内部引擎
- 双后端执行、失败分类、重试
