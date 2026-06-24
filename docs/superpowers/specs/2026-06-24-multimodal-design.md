# 多模态支持 — 设计文档

**日期**: 2026-06-24
**目标**: 支持截图分析，自动切换视觉模型，三种图片输入方式

---

## 1. 图片输入方式

| 方式 | 触发 | 实现 |
|------|------|------|
| `/image <path>` | 手动输入命令 | 读文件 → base64 → 校验格式/大小 |
| `Ctrl+I` | 快捷键框选截图 | `screencapture -i /tmp/aicoder_img.png` → 自动插入 `/image <path>` |
| 剪贴板检测 | 提交时自动检测 | `osascript clipboard info` → 有 PNG → 保存 → 提示确认 |

## 2. 模型自动切换

- 检测到图片时，检查当前模型 `vision` 字段
- `vision: False` → 自动切 `deepseek-vl2`
- 响应后提示恢复方式

## 3. 图片处理

- Pillow 压缩：最长边 ≤ 2048px，文件 ≤ 2MB
- 支持格式：PNG / JPEG / GIF / WEBP
- 不支持格式拒绝并提示

## 4. 消息格式

```python
HumanMessage(content=[
    {"type": "text", "text": "分析这个UI"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
])
```

## 5. 文件改动

| 文件 | 责任 |
|------|------|
| `agent/images.py` | 新：图片读取、压缩、base64、格式校验 |
| `agent/models.py` | deepseek-vl2 + GPT-4o-vision 注册，vision 标记 |
| `cli/commands.py` | `/image <path>` 解析 |
| `cli/repl.py` | Ctrl+I 截图 + 剪贴板检测 + 多模态消息 + 模型自动切换 |
