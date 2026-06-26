# ocr-router

法律材料 OCR 统一读取入口与门禁系统。

**解决问题**：法律工作中 OCR 有两个痛点——日常读取太慢（每次都要做完整盘点），正式出文书时又不敢信（不知道读到第几页、是否有漏页）。ocr-router 用两层模式解决这个矛盾：日常轻便交接，正式可追溯升级。

## 两层模式

| | 普通模式 | 正式模式 |
|---|---|---|
| 产物 | `read-session.json` | `material_inventory.json` |
| 校验 | 无（口头交接 → 文件级） | `validate-material-reading.py` |
| 用途 | 预览、初步分析、缺口提示 | 诉状、证据目录、策略评估 |
| 升级 | 可直接升级，不重读 | |

## 安装

```bash
git clone https://github.com/6d7njmvkm9-bit/ocr-router.git ~/.workbuddy/legal-skills/ocr-router
```

配置 OCR 后端：

```bash
cp backends/legal-ocr-engine/config/.env.example backends/legal-ocr-engine/config/.env
```

编辑 `.env`，填入 PaddleOCR 或 MinerU 的 API 凭证。至少配置一个后端。

```bash
cd backends/legal-ocr-engine
uv run scripts/convert.py checktoken
```

## 使用

**日常读取**——转换 PDF/图片为 Markdown，自动写入 `read-session.json` 供下游引用：

```bash
python3 scripts/update-read-session.py \
  --work-dir "<工作目录>" \
  --source-scope "<材料路径>" \
  --read-item "<_read_item.json>"
```

**正式门禁**——生成证据目录或诉状前，写入 `material_inventory.json` 后运行校验器：

```bash
python3 scripts/validate-material-reading.py \
  --case-dir "<案件目录>" \
  --require-scope strategy
```

五级 scope：`inventory` → `preliminary` → `legal-research` → `strategy` → `formal-document`。高风险输出前必须显式指定 `strategy` 或 `formal-document`。

## 架构

```
用户提交材料
  → 判断读取路径（direct-ocr / complex-parse / 直接文本 / 视觉复核）
  → legal-ocr-engine 执行转换（PaddleOCR + MinerU 双后端自动路由）
  → _read_item.json → update-read-session.py → read-session.json（普通交接）
  → 按映射表升级 → material_inventory.json → validate → gate-result.json（正式门禁）
  → 下游技能（fact-analysis / contract-copilot / trial-prep）
```

## 目录

```
ocr-router/
├── SKILL.md                         # WorkBuddy 技能入口
├── references/
│   ├── read-session-contract.md     # 普通读取交接契约
│   ├── backend-routing.md           # 后端路由规则
│   ├── material-reading-gate.md     # 正式门禁规则
│   ├── output-contract.md           # 输出 Schema 与升级映射
│   └── api-recovery.md              # API 错误恢复
├── scripts/
│   ├── update-read-session.py       # 读取记录汇总器
│   ├── validate-material-reading.py # 材料门禁校验器
│   └── run-legal-ocr-engine.sh      # OCR 引擎入口
└── backends/legal-ocr-engine/       # OCR 转换引擎
    ├── scripts/convert.py           # 主入口
    ├── scripts/paddle_ocr.py        # PaddleOCR 后端
    └── scripts/mineru_ocr.py        # MinerU 后端
```

## 运行测试

```bash
python3 scripts/test_update_read_session.py       # 25 项
python3 scripts/test_validate_material_reading.py  # 8 项
```

## 许可

MIT License。

## 反馈

有问题或建议，欢迎提 [Issue](https://github.com/6d7njmvkm9-bit/ocr-router/issues) 或 [Pull Request](https://github.com/6d7njmvkm9-bit/ocr-router/pulls)。
