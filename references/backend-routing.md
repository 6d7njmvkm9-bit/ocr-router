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
调用外部 OCR 前检查文件路径、大小、格式、页数、引擎凭证、文件哈希与缓存。

## 2. 格式路由
- direct-ocr：普通扫描件、截图、票据、图片型 PDF，优先 PaddleOCR
- complex-parse：复杂版面、长文档、强表格、Office、远程网页，优先 MinerU

## 7. read-session 记录
每次读取路径完成后，都必须输出 _read_item.json；随后调用 update-read-session.py 合并到 read-session.json。不得只生成 Markdown 或口头报告后跳过 read-session。
