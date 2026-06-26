# 后端路由与读取命令

## 目录

1. 本地预检
2. 格式路由
3. PDF 文字层质量
4. OCR 命令
5. 视觉审阅
6. 大文件拆分
7. read-session 记录

## 1. 本地预检

调用外部 OCR 前检查：

| 检查 | 目的 |
|---|---|
| `ls` / `stat` / `file` | 确认路径、大小和真实格式 |
| PDF 页数 | 决定覆盖范围和是否拆分 |
| 必要时预览前3页、中间页、末页 | 仅判断是否可直接读文本；用户已指定 OCR 或文件明显为扫描/图片型时可跳过 |
| 在线引擎凭证 | 只阻断不可用引擎 |
| 文件哈希与缓存 | 避免重复 API |

单次网络探测失败不等于 API 不可用。认证错误直接标记；限流和网络错误按恢复规则处理。

## 2. 格式路由

### 本地读取

后端优先级必须明确：凡 PaddleOCR 支持的输入，先用 PaddleOCR；只有 PaddleOCR 不支持该格式、当前协议不能提交该来源，或返回失败、空结果、缺页、乱码时，才切换 MinerU。读取路径只决定任务复杂度，不改变 PaddleOCR 优先原则：

- `direct-ocr`：普通扫描件、截图、票据、图片型 PDF 或用户明确要求 OCR，PaddleOCR -> MinerU。
- `complex-parse`：复杂版面、长文档结构化或强表格结构，PaddleOCR -> MinerU；Office、远程网页、当前 PaddleOCR 协议不能提交的远程 URL，直接 MinerU。

- TXT、MD、CSV：直接读取。
- PDF：文字版直接文本提取；用户明确要求 OCR，或预览显示为扫描版、图片型、乱码、页码不全、复杂版式时，直接按 direct-ocr 或 complex-parse 路径处理，不先绕文本提取。
- Word、Excel、PPT、RTF 等 Office 文件：调用可用文档读取器；表格、图表、页眉页脚、签章等影响事实判断时再做原文/原图复核。
- 本地读取器不可用或结果明显不可靠时，标记失败或升级 OCR/视觉复核，不静默改用无依据方案。

### 图片和视觉材料

图片、截图、票据、签章、手写和照片默认先走 OCR 或文字提取。出现以下情况时，再做 Read 看图复核：

- OCR 无法稳定识别金额、日期、主体、账号、案号等关键字段；
- 聊天截图需要确认发言人、气泡归属、相邻上下文或时间顺序；
- 付款截图、票据、表格需要确认版式关系、抬头、收付款方向或跨行关系；
- 签章、签名、指印、手写、照片场景或物品状态会影响证明目的；
- 表单、流程图、组织图和其他空间关系会影响事实理解。

图片超过10张时优先批量 OCR，标记低置信度页和关键页，再分批做必要的 Read 看图复核。用户明确要求快速预览时，必须标记未覆盖图片或页码，且不得据此输出确定法律结论。

## 3. PDF 文字层质量

仅在无法判断是否应直接 OCR 时，预览前3页、中间页和末页的文字层质量：

- 有效中文字符比例低于约30%；
- 乱码符号比例高于约15%；
- 页均有效字符明显过少；
- 大量 `<!-- image -->`；
- 表格页只得到零散字段，缺少行列关系；
- 多栏、图文混排或复杂版面明显丢失。

出现上述情况时，不因"存在文字层"而直接标记读取成功，按 direct-ocr 或 complex-parse 路径处理；PaddleOCR 支持的输入仍先用 PaddleOCR；PaddleOCR 不支持该格式、当前协议不能提交该来源，或返回失败、空结果、缺页、乱码时再用 MinerU。该预检只用于选择读取路径；正式读取仍按页覆盖并报告未读页、待复核页和关键不确定项。

## 4. OCR 命令

直接 OCR 路径：

```bash
bash ~/.workbuddy/legal-skills/ocr-router/scripts/run-legal-ocr-engine.sh \
  "<file>" --route-path direct-ocr --output "<output.md>"
```

复杂文档解析路径：

```bash
bash ~/.workbuddy/legal-skills/ocr-router/scripts/run-legal-ocr-engine.sh \
  "<file>" --route-path complex-parse --output "<output.md>"
```

显式指定后端只用于用户指定或故障排查；指定后按指定后端执行：

```bash
bash ~/.workbuddy/legal-skills/ocr-router/scripts/run-legal-ocr-engine.sh \
  "<file>" --backend paddle --output "<output.md>"
```

普通读取只使用 `--route-path direct-ocr` 或 `--route-path complex-parse`。后端按 PaddleOCR 优先执行；PaddleOCR 不支持该格式、当前协议不能提交该来源，或返回失败、空结果、缺页、乱码时，再切换 MinerU。

OCR 完成条件同时满足：

1. 进程退出码为0；
2. 最终输出存在且非空；
3. 返回页数与预期处理页数一致。

视觉复核是按需补充步骤，不作为普通 OCR 出结果的前置条件。OCR 已完成但仍需看图的页面，标记为待复核并继续交付已识别文本。

"已提交""已接受"或仍在轮询时只能标记 `processing`。

### pypdfium2 边界

pypdfium2 只负责页数统计、渲染和预处理，不负责 OCR 或内容理解。仅完成渲染时不得标记 `read`。

### Read 看图边界

Read 看图是按需视觉复核，记录为 `reader_used=read_image` 或与其他读取器组合后的 `reader_used=mixed`。不得把 Read 看图称为 OCR；也不得在 OCR 已能稳定识别文字时，把看图作为默认必经步骤。

## 5. 视觉审阅

视觉结果至少记录：

- 文件和页码；
- 能确认的客观内容；
- 聊天发言方向、时间和相邻上下文；
- 金额、日期、主体与版式位置；
- 签章/手写是否存在及清晰度；
- 无法确认的内容。

视觉模型不能鉴定签名、印章或指印真伪，只能描述其存在、位置和清晰度。

不得因时间、token 或相邻页内容相似而跳过中间页。需要节省成本时，只能在清单中把未处理页保留为 `unprocessed_pages`，并向用户报告部分读取状态。

## 6. 大文件拆分

建议：

- MinerU：50页以内单任务；更长文件按约40–50页分段。
- PaddleOCR：约20页一段。
- 超过200页时优先40页一段。

每段独立保存结果和页码范围；只重试失败段。合并后再次核对完整页码覆盖。

## 7. read-session 记录

**每次读取路径完成后，都必须输出 `_read_item.json`**；随后调用 `update-read-session.py` 合并到 `read-session.json`。不得只生成 Markdown 或口头报告后跳过 read-session。

```bash
python3 ~/.workbuddy/legal-skills/ocr-router/scripts/update-read-session.py \
  --work-dir "<work-dir>" \
  --source-scope "<用户指定路径>" \
  --read-item "<output>/_read_item.json"
```

支持多个 `--read-item`。

`_read_item.json` schema、合并规则和升级映射见 [references/read-session-contract.md](read-session-contract.md)。