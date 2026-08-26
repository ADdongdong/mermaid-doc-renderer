---
name: mermaid-doc-renderer
description: >
  Mermaid 图渲染 + Markdown 转 Word 文档的一体化工具。
  用 headless Chromium + 本地 mermaid.min.js（完全离线）把 Mermaid 声明式代码渲染为
  高清 PNG / 矢量 SVG / WebP / PDF / JPG，再把含 Mermaid 代码块的 Markdown 文档
  转成无 Markdown 语法的 Word（.docx，图用 PNG 嵌入）。
  当用户需要"把 md 里的 mermaid 图导出成图片"、"md 生成 Word/需求文档"、
  "mermaid 转 png/svg"、"文档里的图要清晰、不要 markdown 痕迹"时触发。
agent_created: true
version: 1.0.0
display_name: "Mermaid 渲染与文档生成"
display_name_en: "Mermaid Render & Doc Generator"
description_zh: "Mermaid 渲染与文档生成：用 headless Chromium + 离线 mermaid.min.js 把 Mermaid 代码渲染为 PNG/SVG/WebP/PDF，并支持把含 Mermaid 图的 Markdown 转为无 Markdown 语法的 Word 文档（.docx）。"
description_en: "Render Mermaid diagrams to PNG/SVG/WebP/PDF and convert Markdown with Mermaid blocks to clean Word (.docx) documents, fully offline."
visibility: "public"
---

# Mermaid 渲染与文档生成

把「Mermaid 代码 → 高清图片/矢量」和「Markdown（含 Mermaid 图）→ 干净的 Word 文档」
串成一条可复用的离线流水线。所有渲染完全离线（本地 mermaid.min.js + headless Chromium），
不依赖任何在线图床。

## 适用场景

- 用户提供一份 Markdown，希望把里面的 ```mermaid 代码块导出成图片（PNG/SVG/WebP/PDF/JPG）
- 用户提供 Markdown，希望生成 Word 文档（.docx），且「不要出现 markdown 语法、图要 PNG 格式」
- 用户在写需求规格说明书、设计文档、技术方案时，文档里的架构图/流程图需要高质量渲染

## 前置依赖

- **Python 解释器**（含 `cairosvg`、`Pillow`、`python-docx`）
  - 本项目环境：`E:\08_Anaconda3\Anaconda3\envs\pytorch\python.exe`（已装全部依赖）
- **headless Chromium**（自动探测，优先 Playwright 自带 `chromium_headless_shell-*`）
  - 本机：`C:\Users\10355\AppData\Local\ms-playwright\chromium_headless_shell-1148\chrome-win\headless_shell.exe`
  - ⚠️ 必须用 headless_shell.exe 独立可执行文件；本机 Chrome 因「现有浏览器会话」会转发而非真正 headless
- **mermaid.min.js v10**（本 skill 自带 `assets/mermaid.min.js`，离线加载）

## 工作流程

### 一、渲染 Mermaid → 图片/矢量（`scripts/render_mermaid.py`）

```bash
# 提取 md 中所有 mermaid 块 → PNG（2x 高清，自动裁剪白边）
python scripts/render_mermaid.py <md路径> --out <输出目录> --format png --scale 2

# → 矢量 SVG（保留原始矢量，适合嵌入网页/后续编辑）
python scripts/render_mermaid.py <md路径> --out <输出目录> --format svg

# → 指定目标像素宽度（--scale 失效）
python scripts/render_mermaid.py <md路径> --out <输出目录> --format png --width 1200

# 单条 mermaid 字符串（不读 md）
python scripts/render_mermaid.py --code "graph LR; A-->B" --out <输出目录> --format png
```

关键行为：
- 输出命名：`mermaid_0.png`、`mermaid_1.png`…（按 md 中出现顺序，从 0 开始）
- `--scale` 默认 2（2 倍分辨率，足够清晰）；`--width` 指定像素宽时 scale 失效
- `--format` 可选 `png` / `svg` / `webp` / `pdf` / `jpg`
- 自动探测 `assets/mermaid.min.js` 和 headless Chromium；也可用 `--mermaid-js` / `--shell` 覆盖
- PNG/WebP/JPG 默认自动裁剪四周纯白边（`--no-trim` 关闭）

### 二、Markdown + PNG → Word（`scripts/gen_docx.py`）

```bash
# 渲染图输出到 render_out/ 后，直接生成 docx（自动从 md 首个 H1 取标题）
python scripts/gen_docx.py <md路径> --docx <输出.docx> --png-dir <render_out目录>

# 自定义标题/副标题
python scripts/gen_docx.py <md路径> --docx <输出.docx> --png-dir <render_out目录> \
    --title "文档标题" --subtitle "副标题"
```

关键行为：
- **mermaid 代码块 → 嵌入对应 PNG**（按 `mermaid_0.png` 顺序对应 md 中的 mermaid 块）
- **剥离所有 markdown 语法**：`**加粗**`、`` `代码` ``、`[链接](url)`、表格语法、引用 `>`、列表标记
- 标题（##/###）转为 Word 标题样式；表格转 Table Grid；代码块用等宽字体 + 浅灰底
- 图片按 6.3 英寸等比缩放，超高图按高度缩放

## 端到端示例（md → docx）

```bash
# 1. 渲染 md 里所有 mermaid 块 → PNG
python scripts/render_mermaid.py 需求.md --out ./render_out --format png --scale 2

# 2. 生成 Word（自动嵌入 PNG）
python scripts/gen_docx.py 需求.md --docx 需求.docx --png-dir ./render_out
```

## 常见问题

| 现象 | 处理 |
|------|------|
| 找不到 mermaid.min.js | 确认 `assets/mermaid.min.js` 存在，或用 `--mermaid-js` 指定 |
| 找不到 headless Chromium | 确认 Playwright 的 chromium_headless_shell 已安装，或用 `--shell` 指定路径 |
| 渲染超时 / 无 svg | 增大 `--virtual-time-budget`（脚本内 10000ms），或检查 mermaid 语法 |
| 中文乱码 | headless_shell 已加载系统字体；确认 `C:/Windows/Fonts/` 有中文字体 |
| docx 表格列数报错 | 检查 md 表格每行列数一致（表头列数 = 数据行列数） |
| cairosvg 报错 | 确认 Python 环境已 `pip install cairosvg Pillow python-docx` |
