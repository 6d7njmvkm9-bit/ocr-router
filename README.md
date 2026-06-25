# ocr-router

法律材料 OCR 统一读取入口与门禁系统。

## 解决的问题

做诉讼的，一个案子几百页材料，OCR 跑一遍很快——但跑完你敢直接用吗？你不知道它漏了哪一页、哪一页是乱码、表格拆没拆碎。

另一个矛盾：日常只是想翻翻材料，看看大概内容，和正式写诉状、做证据目录，是完全不同的需求。前者要快，后者要准。但现有的 OCR 工具没有中间地带——要么只跑转换不管质量，要么每次都要做完整盘点。

这个工具做了一件事：**把"读取"和"质量验收"拆成两层。**

- 日常：读完给你一个轻量记录文件，告诉下游读了 X 页、第 Y 页有问题、第 Z 页需要人看。不建门禁，不跑校验。
- 正式：从轻量记录升级成完整材料清单，补齐视觉复核和质量核验，按 scope 校验通过才放行。不重读。

## 两个 OCR 引擎

PaddleOCR 和 MinerU 各干各的活：

- **PaddleOCR**：法律 PDF/图片识别稳定，支持异步大批量翻页。中文长篇文书用它就够了。
- **MinerU**：表格、多层版面、Office 文档、网页 URL 的结构化提取比 PaddleOCR 强一截。手上那种拆出几十个碎片的复杂合同，它能还原成完整的 Markdown。

实际办案材料什么都有——扫描版判决书、手机拍借条、财务导出的 Excel、政府网站公告。两个引擎自动选，不用自己每次想"这个该用哪个读"。

## 两层模式

| | 普通模式 | 正式模式 |
|---|---|---|
| 产物 | read-session.json | material_inventory.json |
| 校验 | 文件级交接 | validate-material-reading.py |
| 用途 | 预览、初步分析、缺口提示 | 诉状、证据目录、策略评估 |
| 升级 | 可直接升级，不重读 | |

## 安装

```bash
git clone https://github.com/6d7njmvkm9-bit/ocr-router.git
cd ocr-router
cp backends/legal-ocr-engine/config/.env.example backends/legal-ocr-engine/config/.env
# 编辑 .env，填入 PaddleOCR 或 MinerU 的 API 凭证。至少配置一个。
cd backends/legal-ocr-engine
uv run scripts/convert.py checktoken
```

## 使用

日常读取：

```bash
python3 scripts/update-read-session.py --work-dir "工作目录" --source-scope "材料路径" --read-item "_read_item.json"
```

正式门禁：

```bash
python3 scripts/validate-material-reading.py --case-dir "案件目录" --require-scope strategy
```

五级 scope：`inventory` -> `preliminary` -> `legal-research` -> `strategy` -> `formal-document`。

## 架构

```
材料输入 -> 判断读取路径 -> 双引擎自动转换 -> _read_item.json -> read-session.json
           -> 按映射表升级 -> material_inventory.json -> validate -> gate-result.json
```

## 测试

```bash
python3 scripts/test_update_read_session.py       # 25 项
python3 scripts/test_validate_material_reading.py  # 8 项
```

## 许可

MIT。
