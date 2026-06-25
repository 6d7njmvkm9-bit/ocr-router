# ocr-router

法律材料 OCR 统一读取入口与门禁系统。

## 为什么做这个

做诉讼的同行都经历过：一个案子几百页材料，OCR 跑一遍很快，但跑完你敢直接用吗？你不知道它漏了哪一页、哪一页是乱码、哪个表格被拆成了碎片。更麻烦的是，日常只是想看个大概和正式写诉状是两个完全不同的需求——前者要快，后者要准。但市面上没有工具能同时满足这两个场景。

ocr-router 就是填这个缺口的：日常读取时给你一个轻量的交接文件，告诉下游"我读了 X 页，第 Y 页有问题，第 Z 页需要人看"；到了写诉状、做证据目录这种正式场景，从轻量记录按映射表升级成完整的材料门禁，校验通过再放行。不重读。

核心设计只有一句话：**普通模式不建门禁，但必须留文件；正式模式不重读一切，只在普通记录上补齐。**

## 为什么用两个 OCR 引擎

PaddleOCR 和 MinerU 各有所长：

- **PaddleOCR**：常规的法律 PDF/图片识别效果稳定，支持异步大批量，自带法律场景的版面分析。中文长篇文书的日常首选。
- **MinerU**：对复杂表格、多层版面、Office 文档和网页 URL 的结构化提取远强于 PaddleOCR。碰到那种拆出几十个碎片的复杂合同结构，丢给 MinerU 就能还原成一个完整的 Markdown。

一个引擎跑所有场景的想法很美好，但实际办案中，你手里的材料是乱七八糟的——有扫描版判决书、有手机拍的借条、有财务导出的 Excel、有政府网站的公告。双引擎自动路由的代价只是一行配置，收益是不用每次自己判断"这个该用哪个读"。

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

五级 scope：`inventory` -> `preliminary` -> `legal-research` -> `strategy` -> `formal-document`。高风险输出前必须显式指定 `strategy` 或 `formal-document`。

## 架构

```
用户提交材料
  -> 判断读取路径（direct-ocr / complex-parse / 直接文本 / 视觉复核）
  -> legal-ocr-engine 执行转换（PaddleOCR + MinerU 双后端自动路由）
  -> _read_item.json -> read-session.json（普通交接）
  -> 按映射表升级 -> material_inventory.json -> validate -> gate-result.json（正式门禁）
  -> 下游技能
```

## 运行测试

```bash
python3 scripts/test_update_read_session.py       # 25 项
python3 scripts/test_validate_material_reading.py  # 8 项
```

## 许可

MIT License。

## 反馈

有问题或建议，欢迎提 Issue 或 Pull Request。
