# mermaid-doc-renderer

Mermaid 图渲染 + Markdown 转 Word 文档的一体化**离线**工具链。

由 CodeBuddy 在「投行函证 PDF 工具」需求文档（v5.0）编写过程中沉淀而来：
当时发现 headless Chromium + 本地 mermaid.min.js 渲染出的图质量很好，于是把
「Mermaid → 高清图」和「Markdown（含 Mermaid）→ 无 Markdown 语法的 Word」整理成
可复用的 skill。

## 能力

| 命令 | 说明 |
|------|------|
| `render_mermaid.py` | 提取 Markdown 里的 ```mermaid 块，渲染为 PNG / SVG / WebP / PDF / JPG（完全离线） |
| `gen_docx.py` | 把 Markdown 转成 Word（.docx），mermaid 图用 PNG 嵌入，剥离全部 markdown 语法 |

## 快速开始

### 1. 渲染 Mermaid → PNG

```bash
python scripts/render_mermaid.py 需求.md --out ./render_out --format png --scale 2
```

输出 `render_out/mermaid_0.png`、`mermaid_1.png`…（按 md 中顺序）。

### 2. Markdown + PNG → Word

```bash
python scripts/gen_docx.py 需求.md --docx 需求.docx --png-dir ./render_out
```

## 支持格式

- **PNG**：headless Chromium 截图（DSF 缩放，默认 2x 高清）+ PIL 裁白边
- **SVG**：`--dump-dom` 提取矢量源码
- **WebP / JPG / PDF**：从 PNG 转换

## 依赖

- Python：`Pillow`（docx 另需 `python-docx`）
- headless Chromium（Playwright 自带 `chromium_headless_shell-*`，自动探测）
- `assets/mermaid.min.js`（v10，离线加载，本仓库自带）

> 不使用 cairosvg 的原因：mermaid 生成的 SVG 含复杂 CSS/foreignObject，
> cairosvg 常报 `mismatched tag` 且中文字体支持差；截图方式零兼容风险。

## 许可证

MIT
