"""
Generate a prompt for Kimi web to extract UI element bounding boxes from a screenshot.

Usage:
    python scripts/generate_prompt.py [image_path]

If image_path is provided, also copies the prompt to clipboard (requires pyperclip).
The prompt instructs Kimi to return a JSON array describing each UI element's
position, size, type, and purpose.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROMPT_TEMPLATE = """\
请仔细分析这张截图中的所有 UI 元素（按钮、输入框、标签、图标、菜单项、下拉框、复选框、滑块、标签页、工具栏、状态栏等），并以 JSON 格式输出每个元素的信息。

## 输出要求

返回一个 JSON 对象，格式如下：

```json
{{
  "image_width": <图片宽度像素>,
  "image_height": <图片高度像素>,
  "elements": [
    {{
      "id": 1,
      "type": "<元素类型>",
      "label": "<元素上显示的文字，无文字则为空字符串>",
      "purpose": "<该元素的功能用途简述>",
      "bbox": {{
        "x": <左上角x坐标>,
        "y": <左上角y坐标>,
        "width": <宽度>,
        "height": <高度>
      }},
      "interactive": <true/false 是否可交互>,
      "state": "<可选: enabled/disabled/checked/unchecked/selected/hover>"
    }}
  ]
}}
```

## 规则

1. **坐标系**: 左上角为原点 (0, 0)，x 向右增长，y 向下增长，单位为像素
2. **bbox 精确性**: 尽可能精确地框选每个元素的可见边界，不要留太多空白
3. **层级**: 只输出叶子级可见元素，不要输出容器/布局等不可见元素
4. **type 取值**: button, input, label, icon, checkbox, radio, slider, tab, menu_item, dropdown, toolbar, statusbar, scrollbar, image, link, progress_bar, tooltip, dialog, panel, list_item, tree_item, table_cell, other
5. **完整性**: 不要遗漏任何可见的 UI 元素
6. **只输出 JSON**: 不要输出任何解释性文字，只返回上述格式的 JSON
"""


def generate_prompt(image_path: str | None = None) -> str:
    """Return the prompt text. If image_path given, include a note about it."""
    prompt = PROMPT_TEMPLATE
    if image_path:
        p = Path(image_path)
        prompt += f"\n（分析的图片文件: {p.name}）\n"
    return prompt


def main():
    image_path = sys.argv[1] if len(sys.argv) > 1 else None

    if image_path:
        p = Path(image_path)
        if not p.exists():
            print(f"[WARNING] Image file not found: {image_path}")

    prompt = generate_prompt(image_path)

    # Print to stdout
    print("=" * 60)
    print("  Kimi Prompt — 复制以下内容到 Kimi 网页版并上传截图")
    print("=" * 60)
    print()
    print(prompt)
    print("=" * 60)

    # Try to copy to clipboard
    try:
        import pyperclip
        pyperclip.copy(prompt)
        print("\n✅ Prompt 已复制到剪贴板")
    except ImportError:
        print("\n💡 安装 pyperclip 可自动复制到剪贴板: pip install pyperclip")

    # Save prompt to file for convenience
    out_path = Path(__file__).parent / "last_prompt.txt"
    out_path.write_text(prompt, encoding="utf-8")
    print(f"📄 Prompt 已保存到: {out_path}")

    if image_path:
        print(f"\n📋 使用步骤:")
        print(f"   1. 打开 Kimi 网页版 (kimi.moonshot.cn)")
        print(f"   2. 上传图片: {image_path}")
        print(f"   3. 粘贴 Prompt 并发送")
        print(f"   4. 复制 Kimi 返回的 JSON")
        print(f"   5. 保存为 .json 文件")
        print(f"   6. 打开 scripts/visualizer.html 查看可视化结果")


if __name__ == "__main__":
    main()
