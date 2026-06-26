# API 运行与失败恢复

## 目录

1. 任务状态
2. 错误分类
3. 重试和降级
4. 缓存
5. 并发与反馈

## 1. 任务状态

远端 OCR 按任务处理：

```text
queued -> processing -> done
                     -> failed
                     -> timed_out
```

只有 `done` 且产物、页数校验通过后才能写入成功状态。失败和超时必须写入 `api_failures`。

## 2. 错误分类

| error_type | 含义 | 默认动作 |
|---|---|---|
| `auth_failed` | 401/403或凭证失效 | 当前引擎停止；切换已授权后端并告知 |
| `rate_limited` | 429 | 等待60秒后重试1次；必要时降低并发 |
| `network_error` | 瞬态网络失败 | 等待30秒后重试1次 |
| `timeout` | 任务超时 | 检查外层超时；再降级 |
| `file_too_large` | 文件过大 | 分段后重试 |
| `unsupported_format` | 格式不支持 | 本地转换或渲染后重试 |
| `bad_result` | 空结果、乱码、页数错误 | 降级下一引擎 |
| `partial_result` | 只返回部分页 | 保留成功页，仅降级缺失页 |
| `file_not_found` | 路径不可访问 | 停止该文件并报告 |

## 3. 重试和降级

案件材料已授权时，必须按以下顺序选择最短可用路径：

```text
可可靠直接读文本 -> 本地提取
用户要求 OCR / 普通扫描件 / 图片型材料 / 低质量文字层 -> direct-ocr，优先 PaddleOCR，不得先送复杂文档解析
复杂版面、强表格结构、长文档结构化提取 -> complex-parse，PaddleOCR -> MinerU；Office、远程网页、当前 PaddleOCR 协议不能提交的远程 URL -> MinerU
当前引擎失败 -> 只切换一个适合当前材料的已授权后端
仍失败 -> 必要时渲染后再 OCR；只有 OCR/文本无法确认当前任务所需视觉事实时才 Read 看图
最终 -> partially_read / failed / needs_human_review
```

规则：

- 认证失败不重复撞同一凭证。
- 限流、网络错误最多按表中次数重试。
- 同一引擎重复运行不算独立交叉验证；不要为"完整流程"把 PaddleOCR 支持的材料先送 MinerU 再回到 OCR。complex-parse 仍可用 PaddleOCR 先处理，PaddleOCR 不支持该格式、当前协议不能提交该来源，或返回失败、空结果、缺页、乱码时再切换 MinerU。
- 不自动安装 EasyOCR 或其他新依赖。
- 已完成文件不因其他文件失败而回滚。
- 失败后必须保留实际错误、引擎、重试次数、最终降级和结果。

建议失败记录：

```json
{
  "file": "...",
  "engine": "mineru",
  "error_type": "timeout",
  "retry_count": 0,
  "final_fallback": "paddleocr",
  "fallback_success": true
}
```

## 4. 缓存

缓存键必须包含：

```text
file_hash::engine::engine_version::model::params_hash
```

参数至少覆盖模式、页码范围和DPI。文件、引擎版本、模型或参数任一变化时不得复用旧结果。

缓存命中时：

- 校验缓存产物仍存在且非空；
- `reader_used` 标注实际引擎和 cached；
- 不重新调用 API；
- 缓存不能替代高风险输出前的材料门禁校验。

缓存应位于明确的中间产物目录或 Skill 扫描目录之外，避免产生运行时发现噪音。

## 5. 并发与反馈

建议最大并发：

| 任务 | 并发 |
|---|---:|
| 本地元数据预检 | 可并行 |
| 本地文本提取 | 5 |
| MinerU | 2 |
| PaddleOCR | 2 |
| Read 看图 | 3 |
| pypdfium2 渲染 | 4 |

遇到限流时将对应引擎并发减半，最低为1。

批量任务只需在状态发生实质变化时反馈：

```text
发现 N 个文件；完成 X；处理中 Y；失败 Z；待视觉复核 W。
当前：<文件>（<引擎/阶段>）。
```

避免逐页刷屏，也不得长时间只显示"正在 OCR"。