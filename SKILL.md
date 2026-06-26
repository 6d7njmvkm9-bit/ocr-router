---
name: ocr-router
description: 统一材料读取入口。用户提交 PDF、Word、Excel、PPT、图片、扫描件、截图、票据、签章、手写或照片并要求读取、整理、摘要、分析或审查时使用；默认先读取材料并报告读取质量，再按用户目标交给案件分析、合同审查或其他下游。不要用于法律检索、事实分析或实体结论。
---

# 统一材料读取入口

## 一、核心规则

1. **先读材料，再做分析**：收到附件后只先做普通读取；用户要求案件分析、合同审查、摘要或整理时，才把已读取内容交给下游。
2. **不做模式前置筛选**：不得先判断材料或案件属于哪种模式。普通读取只做必要登记：文件名、页数、读取方式、未读页和待复核点。
3. **PaddleOCR 优先，按路径控制复杂度**：能直接读文本的材料必须直接读；需要 OCR 或文档解析时，凡 PaddleOCR 支持的 PDF、图片、截图、票据、扫描件等输入，必须先用 PaddleOCR；只有 PaddleOCR 不支持该格式、当前协议不能提交该来源，或返回失败、空结果、缺页、乱码时，才切换 MinerU 等后端。读取路径仍需区分：普通扫描/图片文字识别走 `direct-ocr`，复杂版面、长文档结构化或强表格结构走 `complex-parse`；只有 OCR/文本结果不足以确认当前任务所需的版式、上下文、签章/手写或照片场景时，才做 Read 看图。
4. **只有高风险输出才补门禁**：普通读取和普通分析不得创建完整 `material_inventory` 或运行校验器；只有高风险输出、正式交付或用户明确要求完整可追溯时，才补完整材料门禁。
5. **不把工具调用当完成**：普通读取只能说"已读取/部分读取/无法读取"；只有完整门禁通过后，才能说"覆盖完整"。
6. **不猜测**：无法确认的内容标记 `partially_read` 或 `needs_human_review`，不得补全人名、金额、日期、主体、聊天方向或图片内容。
7. **读取不产生业务结论**：读取通过只证明材料可用；法律判断、合同审查、策略和正式文书由下游完成。

## 二、术语边界

- **普通读取**：读出用户提交材料，说明已读内容、读取方式、未读页和待复核点；不得创建完整 `material_inventory`，不得运行校验器。
- **普通分析**：基于已读材料做事实梳理、争议焦点、初步风险和证据缺口；待核实内容只能限制对应结论，不得阻断已读部分分析。
- **高风险输出**：确定责任、金额、时效、主体结论、胜诉/策略、正式证据目录、正式或可提交文书；只有此类输出才补完整材料门禁。

## 三、执行流程

### 1. 确定工作区

- 持续任务：使用对应任务目录。
- 一次性附件：使用临时目录，例如 `<tmp>/workbuddy-reading-<session-id>/`。
- 只处理用户本次指定的文件或目录；指定目录时递归读取其中支持的文件类型，不扩展到未指定路径、上级目录或无关目录。
- 不在源材料目录创建管理文件，不移动、不重命名、不修改原件。

### 2. 必要登记

普通读取只登记本次用户提交或指定的文件，不递归扫描无关目录。记录：

```text
file, type, page_count, read_status, reader_used,
unprocessed_pages, needs_visual_review, warnings
```

最终状态只能是：`read`、`partially_read`、`failed`、`needs_human_review`。

普通读取不创建完整 `material_inventory`，不运行校验器；但必须写入 `<work-dir>/.material-reading/read-session.json`。没有 `read-session.json`，不得向下游声称"已完成可交接读取"。

只有高风险输出、正式交付或用户明确要求完整可追溯时，才递归扫描 `source_roots`、计算哈希并写入完整 `material_inventory`。

普通读取交接、read-item/read-session schema、升级映射见 [references/read-session-contract.md](references/read-session-contract.md)。

### 3. 分派读取

| 材料特征 | 首选路径 | 必要复核 |
|---|---|---|
| TXT / MD / CSV | 直接读取 | 完整读取，记录异常和关键字段 |
| Word / Excel / PPT 等 Office 文件 | 默认走文档读取器；如本地稳定读取器不可用、结构复杂或需要统一 Markdown，走 complex-parse；Office 输入不属于 PaddleOCR 支持格式时才走 MinerU | 表格、图表、页眉页脚、签章按需看图 |
| PDF | 文字版 PDF 先直接提取文本；扫描版、图片型 PDF 必须走 direct-ocr；用户明确要求 OCR 时，即使有文字层也优先走 direct-ocr；复杂版面、长文档结构化或强表格结构才走 complex-parse | 逐页覆盖，关键页对原文/原图 |
| 扫描件、低质量文字层、复杂表格/版面 | 普通文字识别走直接 OCR；复杂表格/版面和结构化提取走复杂文档解析 | 关键字段对原页，必要时看图 |
| 图片、截图、票据、签章、手写、照片 | OCR 优先；必要时 Read 看图 | 影响法律判断的版式、上下文和视觉要素需复核 |
| OCR 全部失败 | pypdfium2 渲染 → 本地 OCR/Read | 渲染本身不算读取成功 |

法律材料不得用抽查代替读取。少量页面预检只用于判断读取工具，不能作为内容已读、事实已核实或法律结论的依据。

选择读取器、文字层质量判断、大文件拆分和命令细节见 [references/backend-routing.md](references/backend-routing.md)。

### 4. 按输出需要补门禁

普通读取和普通分析不得创建门禁文件。只有以下场景才补完整清单和门禁：

- 将要生成正式证据目录、正式提交材料，或用户明确要求确认多文件材料无漏读；
- 用户明确要求持续办案、正式建案、多人协作或完整模式；
- 用户明确要求完整读取、全量盘点、覆盖率校验或可追溯材料清单；
- 将要输出策略/胜诉评估、正式或可提交文书；
- 将要就金额、主体、期限、签章、付款、发票或聊天发言人归属输出确定结论。

升级后必须创建：

```text
<work-dir>/.material-reading/material-inventory.json
```

顶层至少包含：

```json
{
  "schema_version": "1.0",
  "source_roots": ["本次实际附件路径"],
  "material_inventory": [],
  "unreadable_items": [],
  "needs_followup_review": [],
  "api_failures": []
}
```

然后实际运行：

```bash
python3 ~/.workbuddy/legal-skills/ocr-router/scripts/validate-material-reading.py \
  --case-dir "<work-dir>" \
  --require-scope inventory
```

按输出类型选择 `--require-scope`：`inventory` 只用于材料盘点，`strategy` 用于诉讼策略/胜诉评估，`formal-document` 用于正式或可提交文书。高风险输出前必须显式指定 `strategy` 或 `formal-document`，不得依赖默认 `inventory`。

门禁语义：

| 结果 | 含义 | 下游权限 |
|---|---|---|
| `FULL_PASS` | 文件、页码、产物和必要视觉复核均通过 | 可按用户目标进入下游 |
| `LIMITED_PASS` | 已登记但仍有未处理、待复核或失败项 | 只能做初步整理和缺口提示 |
| `BLOCKED` | 漏登、哈希变化、页码矛盾、产物缺失或结构错误 | 只报告错误和修复路径 |

校验器、scope 和状态细节见 [references/material-reading-gate.md](references/material-reading-gate.md)；字段契约见 [references/output-contract.md](references/output-contract.md)。

### 5. 质量核验

按材料类型和用户目标核验关键项，不默认拉满固定清单。只核对会影响当前读取、事实整理或下游法律判断的内容：

- 主体身份、金额、日期、期限、案号等基础事实；
- 签章、签名、指印、手写、原件/复印件等证据形态；
- 聊天、付款、票据、表格等依赖版式或上下文的关键信息。

材料中不存在或与当前任务无关的字段不强制核验。不确定项写入 `warnings`、`critical_unverified_pages` 或 `needs_followup_review`。

### 6. 对用户报告

只报告可证明的状态：

```text
已读取：<文件名>，共 <页数> 页。
读取方式：本地文本提取 / OCR / Read 看图 / 混合。
读取状态：read / partially_read / failed / needs_human_review。
未处理或待复核：<文件和页码>。
下一步：案件分析 / 合同审查 / 仅交付提取文本。
```

只有实际运行完整门禁时，才报告 `FULL_PASS / LIMITED_PASS / BLOCKED`。

## 四、授权与失败

- 用户主动提交附件并要求读取、整理、摘要、分析或审查时，视为授权读取；但按最短可用路径执行，不并列调用所有后端：能直接读文本就直接读，明确 OCR 或扫描/图片型材料就直接 OCR，Read 看图和渲染只在 OCR/文本结果不足以支撑当前任务时补充。
- 只要求"盘点文件/看看有哪些文件"时，只读取元数据，不读正文。
- 不得把材料发送给与读取无关的外部服务。
- MinerU、PaddleOCR、pypdfium2、PDF/Office 读取器和 Read 都是后端，不是独立自然语言入口。
- 所选 OCR/文档解析后端失败后，切换已授权后端；认证失败不盲目重试，限流和瞬态网络错误按策略重试。
- 单个文件失败不影响已完成文件，但必须进入 `api_failures`、`unreadable_items`、降级路径或人工复核之一。
- 所有 OCR 均失败时保留已完成结果，列出未读文件/页码和下一步，不自动安装新工具。

恢复、缓存、并发和任务状态见 [references/api-recovery.md](references/api-recovery.md)。

## 五、按需加载

| 场景 | 读取 |
|---|---|
| 普通读取交接、read-item/read-session schema、升级映射 | [references/read-session-contract.md](references/read-session-contract.md) |
| 需要选择读取器、执行命令、判断文字层质量或处理大文件时 | [references/backend-routing.md](references/backend-routing.md) |
| 发生 API 认证、异步任务、错误分类、重试、缓存、并发或降级问题时 | [references/api-recovery.md](references/api-recovery.md) |
| 高风险输出、正式交付或全量可追溯时的清单 Schema、质量字段和字段映射 | [references/output-contract.md](references/output-contract.md) |
| 高风险输出、正式交付或用户要求完整门禁时，运行校验器、理解 scope、状态和退出码 | [references/material-reading-gate.md](references/material-reading-gate.md) |