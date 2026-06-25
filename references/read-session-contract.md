# 普通读取交接契约

本文件定义普通读取模式下的最小可交接记录结构。

三层文件：_read_item.json -> read-session.json -> material_inventory.json

read-session.json 路径：<work-dir>/.material-reading/read-session.json

核心规则：
1. 每种读取路径都必须先输出统一的 _read_item.json
2. update-read-session.py 只合并 _read_item.json
3. 普通读取没有 read-session.json，不得向下游声称已完成可交接读取

## _read_item.json schema

schema_version: read-item/1.0
file, file_hash, type, page_count, processed_pages, unprocessed_pages, read_status, reader_used, extracted_text_ref, raw_text_ref, archive_ref, postprocess_applied, postprocess_log_ref, needs_visual_review, warnings, api_error, cache_key

archive_ref、raw_text_ref、postprocess_log_ref 全部 optional。

## 汇总规则

update-read-session.py 只做三件事：读取 _read_item.json、校验字段和枚举值、追加合并到 read-session.json

合并规则：
- 同 file + 同 file_hash：更新同一条记录
- 同 file 但 file_hash 变化：旧记录标记 superseded
- 同 file_hash 但路径不同：记录 aliases

## 向正式门禁升级

字段等级：required_explicit / required_if_applicable / optional

任何缺少 required_explicit 字段的 read-session 记录，不得升级为 material_inventory。

存在 unprocessed_pages 时，下游只能做初步事实梳理，不得输出确定结论。
