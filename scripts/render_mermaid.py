# -*- coding: utf-8 -*-
"""Mermaid → 图片/矢量 通用渲染器（mermaid-doc-renderer skill）

支持输出格式：png / svg / webp / jpg / pdf
支持分辨率：--scale 倍率，或 --width 目标像素宽度

渲染管线（完全离线，验证可靠）：
  1. headless Chromium 加载 HTML（内嵌本地 mermaid.min.js），mermaid 渲染成 SVG
  2. PNG/WebP/JPG/PDF：--screenshot 直接截取高清位图（DSF 缩放），PIL 裁剪白边
  3. SVG：--dump-dom 读回 DOM 提取 <svg> 矢量源码

为什么不用 cairosvg 转 SVG？
  mermaid 生成的 SVG 含复杂 CSS/foreignObject，cairosvg 解析常报 mismatched tag，
  且中文字体支持差。截图方式（DSF>=2）零兼容风险，足够高清。

用法：
  python render_mermaid.py <md_path> --out <dir> --format png --scale 2
  python render_mermaid.py <md_path> --out <dir> --format svg
  python render_mermaid.py <md_path> --out <dir> --format png --width 1200
  # 单条 mermaid 字符串（不读 md）
  python render_mermaid.py --code "graph LR; A-->B" --out <dir> --format svg
  # 自定义 mermaid.js / Chromium 路径
  python render_mermaid.py <md> --out <dir> --mermaid-js <path> --shell <path>

依赖：
  - Python：Pillow（无 cairosvg 需求）
  - headless Chromium（本机 Playwright 自带 chromium_headless_shell-1148）
  - mermaid.min.js v10（离线，本 skill 自带 assets/mermaid.min.js）
"""
import os, sys, re, subprocess, argparse, glob, io, html, json

# ====== 自动探测环境常量 ======
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_mermaid_js():
    cands = [
        os.path.join(SKILL_DIR, 'assets', 'mermaid.min.js'),
        r'C:\Users\10355\mmdc_work\mermaid.min.js',
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    return cands[0]


def find_headless_shell():
    patterns = [
        os.path.join(os.environ.get('LOCALAPPDATA', r'C:\Users\10355\AppData\Local'),
                     'ms-playwright', 'chromium_headless_shell-*', 'chrome-win', 'headless_shell.exe'),
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    ]
    for pat in patterns:
        hits = glob.glob(pat)
        if hits:
            return hits[0]
    return patterns[0]


MERMAID_JS = os.environ.get('MERMAID_JS') or find_mermaid_js()
SHELL = os.environ.get('HEADLESS_SHELL') or find_headless_shell()
DEFAULT_OUT = os.path.join(SKILL_DIR, 'render_out')


def extract_mermaid_blocks(md_text):
    blocks = []
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith('```mermaid'):
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            blocks.append('\n'.join(buf))
            i += 1
        else:
            i += 1
    return blocks


def make_html(mermaid_code):
    mermaid_js_url = 'file:///' + MERMAID_JS.replace('\\', '/')
    code_json = json.dumps(mermaid_code)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="{mermaid_js_url}"></script>
<style>
  html,body {{ margin:0; padding:0; background:#fff; }}
  .mermaid {{ padding:16px; }}
</style>
</head><body>
<div class="mermaid" id="mm"></div>
<script>
  var code = {code_json};
  document.getElementById('mm').textContent = code;
  mermaid.initialize({{ startOnLoad:true, theme:'default', securityLevel:'loose' }});
  setTimeout(function(){{
    try {{ var s=document.querySelector('#mm svg'); if(s) document.title='MMD_READY'; }} catch(e){{}}
  }}, 3000);
</script>
</body></html>"""


def render_png_screenshot(mermaid_code, out_path, scale=2, view_w=1800, view_h=1400):
    """headless_shell 截图 → PNG（DSF 缩放），验证可靠"""
    html_path = os.path.join(os.path.dirname(out_path) or '.', f'_mm_tmp.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(make_html(mermaid_code))
    cmd = [SHELL, '--headless', '--disable-gpu', '--no-sandbox',
           '--hide-scrollbars', f'--force-device-scale-factor={scale}',
           f'--window-size={view_w},{view_h}', '--virtual-time-budget=10000',
           f'--screenshot={out_path}',
           f'file:///{html_path.replace(chr(92), "/")}']
    try:
        subprocess.run(cmd, capture_output=True, timeout=60)
    except Exception as e:
        print(f'  render error: {e}')
        return None
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        print('  no png produced')
        return None
    return out_path


def render_svg_dump(mermaid_code, out_path, scale=2, view_w=1800, view_h=1400):
    """dump-dom 提取 SVG 矢量源码"""
    html_path = os.path.join(os.path.dirname(out_path) or '.', f'_mm_tmp.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(make_html(mermaid_code))
    cmd = [SHELL, '--headless', '--disable-gpu', '--no-sandbox',
           '--hide-scrollbars', f'--force-device-scale-factor={scale}',
           f'--window-size={view_w},{view_h}', '--virtual-time-budget=10000',
           '--dump-dom', f'file:///{html_path.replace(chr(92), "/")}']
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60)
    except Exception as e:
        print(f'  render error: {e}')
        return None
    dom = r.stdout.decode('utf-8', errors='replace')
    start = dom.find('<svg')
    if start == -1:
        print('  no svg found in dom')
        return None
    end = dom.rfind('</svg>')
    if end == -1:
        print('  svg incomplete')
        return None
    svg_text = dom[start:end + len('</svg>')]
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(svg_text)
    return out_path


def trim_whitespace(path):
    """裁剪图片四周纯白边"""
    from PIL import Image
    img = Image.open(path).convert('RGB')
    px = img.load()
    w, h = img.size
    bg = (255, 255, 255)

    def is_bg(x, y):
        r, g, b = px[x, y]
        return r > 250 and g > 250 and b > 250

    top = 0
    while top < h:
        if not all(is_bg(x, top) for x in range(w)):
            break
        top += 1
    bottom = h - 1
    while bottom > top:
        if not all(is_bg(x, bottom) for x in range(w)):
            break
        bottom -= 1
    left = 0
    while left < w:
        if not all(is_bg(left, y) for y in range(top, bottom + 1)):
            break
        left += 1
    right = w - 1
    while right > left:
        if not all(is_bg(right, y) for y in range(top, bottom + 1)):
            break
        right -= 1
    img = img.crop((left, top, right + 1, bottom + 1))
    img.save(path)
    return img.size


def convert_png_to(out_path, fmt, width=None):
    """从 PNG 转换 webp/jpg/pdf（PIL 支持）"""
    from PIL import Image
    img = Image.open(out_path)
    if width:
        h = int(img.height * width / img.width)
        img = img.resize((width, h), Image.LANCZOS)
    base = os.path.splitext(out_path)[0]
    target = base + '.' + fmt
    if fmt in ('webp', 'jpg', 'jpeg'):
        img.save(target, format='WEBP' if fmt == 'webp' else 'JPEG')
    elif fmt == 'pdf':
        img.convert('RGB').save(target, format='PDF')
    return target


def render_one(mermaid_code, idx, out_dir, fmt='png', scale=2, width=None, trim=True, work_dir=None):
    work_dir = work_dir or out_dir
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(work_dir, exist_ok=True)

    png_path = os.path.join(work_dir, f'mermaid_{idx}.png')
    svg_path = os.path.join(work_dir, f'mermaid_{idx}.svg')

    if fmt == 'svg':
        res = render_svg_dump(mermaid_code, svg_path, scale=scale)
        if not res:
            return None
        final = os.path.join(out_dir, f'mermaid_{idx}.svg')
        os.replace(svg_path, final)
        print(f'  [{idx}] -> {os.path.basename(final)} size=vector')
        return final

    # 默认走截图路径（png/webp/jpg/pdf 都先出 PNG）
    res = render_png_screenshot(mermaid_code, png_path, scale=scale)
    if not res:
        return None
    if trim:
        trim_whitespace(png_path)

    if fmt == 'png':
        if work_dir != out_dir:
            final = os.path.join(out_dir, f'mermaid_{idx}.png')
            os.replace(png_path, final)
            out_path = final
        else:
            out_path = png_path
        if width:
            from PIL import Image
            img = Image.open(out_path)
            h = int(img.height * width / img.width)
            img = img.resize((width, h), Image.LANCZOS)
            img.save(out_path)
        from PIL import Image
        try:
            sz = Image.open(out_path).size
        except Exception:
            sz = 'ok'
        print(f'  [{idx}] -> {os.path.basename(out_path)} size={sz}')
        return out_path

    # webp/jpg/pdf
    target = convert_png_to(png_path, fmt, width=width)
    if work_dir != out_dir:
        final = os.path.join(out_dir, os.path.basename(target))
        os.replace(target, final)
        target = final
    print(f'  [{idx}] -> {os.path.basename(target)}')
    return target


def main():
    ap = argparse.ArgumentParser(description='Mermaid → 图片/矢量 渲染器')
    ap.add_argument('md_path', nargs='?', help='markdown 文件路径（含 mermaid 块）')
    ap.add_argument('--code', help='直接渲染这段 mermaid 源码（优先级最高）')
    ap.add_argument('--out', default=DEFAULT_OUT, help='输出目录')
    ap.add_argument('--work', help='临时工作目录（默认=out）')
    ap.add_argument('--format', default='png', choices=['png', 'svg', 'webp', 'pdf', 'jpg'],
                    help='输出格式')
    ap.add_argument('--scale', type=float, default=2, help='分辨率倍率（默认2）')
    ap.add_argument('--width', type=int, default=None, help='目标像素宽度（指定后 scale 失效）')
    ap.add_argument('--no-trim', action='store_true', help='不裁剪白边')
    ap.add_argument('--mermaid-js', default=None, help='自定义 mermaid.min.js 路径')
    ap.add_argument('--shell', default=None, help='自定义 headless Chromium 路径')
    args = ap.parse_args()

    global MERMAID_JS, SHELL
    if args.mermaid_js:
        MERMAID_JS = args.mermaid_js
    if args.shell:
        SHELL = args.shell

    if not os.path.exists(MERMAID_JS):
        print(f'找不到 mermaid.min.js：{MERMAID_JS}')
        sys.exit(1)
    if not os.path.exists(SHELL):
        print(f'找不到 headless Chromium：{SHELL}')
        sys.exit(1)

    out_dir = args.out
    work_dir = args.work or out_dir

    if args.code:
        render_one(args.code, 'single', out_dir, fmt=args.format,
                   scale=args.scale, width=args.width, trim=not args.no_trim, work_dir=work_dir)
        print('DONE')
        return

    if not args.md_path:
        print('需提供 md_path 或 --code')
        sys.exit(1)
    with open(args.md_path, encoding='utf-8') as f:
        md = f.read()
    blocks = extract_mermaid_blocks(md)
    print(f'找到 {len(blocks)} 个 mermaid 块')
    for i, b in enumerate(blocks):
        print(f'== 块 {i}: {b.splitlines()[0][:40]}')
        render_one(b, i, out_dir, fmt=args.format, scale=args.scale,
                   width=args.width, trim=not args.no_trim, work_dir=work_dir)
    print('DONE')


if __name__ == '__main__':
    main()
