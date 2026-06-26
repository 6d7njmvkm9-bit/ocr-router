# 变更日志

## [1.0.4] - 2026-06-26

### 调整

- OCR 后端统一改为 PaddleOCR 优先：凡 PaddleOCR 支持的 PDF、图片、扫描件、截图、票据等输入，`direct-ocr` 和 `complex-parse` 均按 PaddleOCR -> MinerU 回退。
- Office、远程网页、当前 PaddleOCR 协议不能提交的远程 URL 仍走 MinerU，不再表述为 MinerU 优先规则。
- 本地 PDF/图片在双后端可用时不再报错要求声明路径；文档层只保留 `direct-ocr` 与 `complex-parse` 两条明示读取路径。

### 验证

- 更新路由测试：`direct-ocr`、`complex-parse` 本地 PDF 均为 PaddleOCR -> MinerU；Office 文件仍为 MinerU；显式后端不被改写。

## [1.0.3] - 2026-06-25

### 新增
- 新增普通读取 read-session 交接契约文档 `references/read-session-contract.md`。
- 新增 `_read_item.json` fragment 作为各读取路径统一输出格式。
- 新增 `scripts/update-read-session.py` 汇总器，只合并 `_read_item.json`，不解析后端内部格式。
- 新增 `scripts/test_update_read_session.py` 测试（10 个用例，25 项断言全部通过）。

### 调整
- 普通读取不跑完整门禁，但必须写入 `read-session.json`；无此文件不得向下游声称"已完成可交接读取"。
- 高风险输出前必须显式指定 `--require-scope strategy` 或 `--require-scope formal-document`，不得依赖校验器默认 scope。
- 明确 `read-session.json` 到 `material_inventory.json` 的升级映射（10 字段直接复用、6 字段补齐），缺 `required_explicit` 字段阻断升级。
- 修正 PDF 读取路径表述歧义：扫描版/图片型必须走 direct-ocr，用户要求 OCR 独立于材料类型。
- 修正 Office 路径表述：默认走文档读取器，不可用或需统一 Markdown 时走 complex-parse。
- 修正工作区范围：指定目录时递归读取支持的文件类型，不扩展到无关路径。

## [1.0.2] - 2026-06-25

### 调整

- 路由顺序当时改为路径优先；现已由 1.0.4 的 PaddleOCR 优先规则覆盖。
- 普通读取和普通分析不得默认触发完整 `material_inventory`、校验器或逐页视觉复核；高风险输出、正式交付或用户明确要求完整可追溯时才补门禁。
- Read 看图只作为 OCR/文本不足以确认当前任务所需视觉事实时的复核步骤，不再作为图片、截图、票据、签章、手写或照片的默认必经步骤。

### 验证

- 当时更新了路径优先测试；现已由 1.0.4 的 PaddleOCR 优先测试覆盖。

## [1.0.1] - 2026-06-22

### 修复

- 全面移除免 Token 提取路径，统一使用 MinerU extract Token API。
- 当时的统一 OCR 入口曾采用 MinerU Token `extract` 到 PaddleOCR 的回退顺序；现已由 1.0.2 的路径优先规则覆盖。
- 未配置 MinerU Token 时不再静默使用轻量接口。
- PaddleOCR 默认模型升级为 `PaddleOCR-VL-1.6`（保留旧版 1.5 兼容，用户可通过 `PADDLEOCR_MODEL` 降级）。
- PaddleOCR 凭证读取兼容三种环境变量及常见钥匙串账户/服务名组合。
- 材料门禁强制聊天截图、付款截图、票据等视觉材料逐页登记视觉复核。
- 已登记视觉复核完成页时，强制要求存在非空 `visual_review_ref` 产物。

### 验证

- 当时增加了旧路由顺序测试；现已由 1.0.2 的路径优先测试覆盖。
- 增加视觉材料不可规避复核及视觉产物存在性测试。

## [1.0.0] - 2026-06-21

### 新增

- 将 `legal-ocr` 整合为 `ocr-router` 的内部 OCR 执行后端，不新增自然语言入口。
- 支持 MinerU 与 PaddleOCR 后端执行、失败分类和候选后端切换。
- 支持瞬态网络错误指数退避、PaddleOCR 队列限流重试和完整 traceback。
- 支持 PaddleOCR 返回页数完整性校验，避免缺页结果被误判为成功。
- 保存原始 Markdown、处理后 Markdown、后端响应、路由记录和调用元数据。
- 增加保守型法律术语修正与 OCR 硬换行整理，并保留处理日志。
- OCR 归档默认写入 `~/.workbuddy-ocr-archive/`，避免增加 Skill 扫描目录噪声。

### 保留

- `ocr-router` 仍是案件材料读取的唯一入口。
- 保留 MinerU 按页分段、缓存、日志和断点续跑能力。
- 保留 PaddleOCR-VL-1.6 与 macOS 钥匙串 Token 读取。
- OCR 仅负责文字和版面提取，不能替代视觉审阅及材料读取门禁。

### 验证

- 全部 Python 脚本与 Shell 入口通过静态检查。
- 材料读取门禁回归测试 4 项全部通过。
- 内部 OCR 引擎完成离线导入检查；真实 API 调用待网络可用时验证。