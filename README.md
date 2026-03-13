# ProjectReader for LLMs

> **The Ultimate Zero-Dependency Codebase Packer for LLMs.**
>
> 停止无意义的复制粘贴。一键将你的本地项目打包成完美的 LLM 上下文。

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/Dependencies-0-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-gray.svg)]()
[![Version](https://img.shields.io/badge/Version-3.0.0-orange.svg)]()

## 🎉 v3.0 全新升级！

在 v2.0 的基础上，全面重构和增强：
- 🎨 **现代化界面** - 深色/浅色主题切换，更优雅的布局
- 🔍 **实时搜索** - 快速定位文件，高亮显示匹配结果
- 📜 **历史记录** - 自动保存最近打开的项目
- ⌨️ **快捷键** - 全键盘操作支持
- 💾 **导出增强** - 支持导出到文件 (.md/.txt)
- 📊 **详细统计** - 文件数量、Token 估算、大文件雷达
- ⚙️ **快速模板** - 预设过滤规则，一键应用
- 🎯 **更多图标** - 支持更多文件类型识别
- 🔧 **配置持久化** - 自动保存窗口大小、主题等设置

---

### 💡 为什么造这个轮子？
在使用 ChatGPT / Claude / DeepSeek 等大模型辅助编程时，我受够了：
* 手动挨个打开文件，复制粘贴代码？
* 直接把整个目录扔给大模型，结果 `node_modules` 或大文件直接导致 Token 爆炸？
* LLM 被大量无用的业务逻辑干扰，抓不住项目整体架构？

所以我造了这个轮子...

**ProjectReader for LLMs** 是一个 **100% 零依赖** 的单文件脚本，允许零环境的纯净 Python 以 GUI 形式读取你的项目，并以 LLM 友好的 Markdown 形式总结和形成上下文。

![Screenshot](./ProjectReader-GUI.png)

---

## ✨ 核心特性

### 🔧 绝对零依赖 (Zero-Dependency)
* 只有一个 `.py` 文件。纯 Python 标准库编写 (`Tkinter`, `os`, `re`, `json`...)
* **无需 `pip install`**。下载即用，用完即走，不污染开发环境

### 🎨 现代化界面
* **深色/浅色主题** - 一键切换，护眼舒适
* **工具栏** - 清晰的操作按钮布局
* **状态栏** - 实时显示 Token 估算和操作状态
* **三栏布局** - 文件树 + 预览区 + 控制面板
* **响应式设计** - 可调节各栏宽度

### 🔍 智能搜索
* **实时过滤** - 输入即搜，高亮匹配
* **自动展开** - 匹配项自动展开父目录
* **快捷键 Ctrl+F** - 快速聚焦搜索框

### 📜 历史记录
* **自动保存** - 记录最近打开的 10 个项目
* **快速访问** - 工具栏"历史"菜单一键打开
* **持久化存储** - 配置保存在用户目录

### 🦴 智能骨架提取 (Skeleton Mode)
* 万行巨型 `utils.py` 太费 Token？右键开启「骨架模式」
* 瞬间抹除所有函数实现，**仅保留 Class 结构、函数签名和类型注解**
* 支持 Python、JavaScript/TypeScript、Java、C/C++ 等多种语言

### 🛡️ 硬核过滤策略 (Smart Penetration)
* 自动识别 Vue/Python/Java/Rust/Go 项目，预设忽略垃圾目录
* **原生解析 `.gitignore`**，Git 忽略什么，它就忽略什么
* **白名单穿透机制**：即使父目录被黑名单封杀，只要命中白名单，依然能从深处将文件精准"捞"出
* **快速模板** - 预设常用过滤规则（Web/Python/只看源码等）

### 🔐 本地脱敏 (Secret Redaction)
* 复制前自动扫描，将疑似硬编码的 `api_key`、`password` 替换为 `[REDACTED_SECRET]`，安全第一
* 可选开关，根据需要启用/禁用

### ⌨️ 快捷键支持
* `Ctrl+O` - 打开项目文件夹
* `Ctrl+F` - 聚焦搜索框
* `Ctrl+E` - 导出到剪贴板
* `Ctrl+S` - 重新扫描项目
* `Ctrl+T` - 切换主题
* `F5` - 刷新扫描
* `Esc` - 清除搜索

### 💾 灵活导出
* **复制到剪贴板** - 一键复制完整 Markdown
* **导出到文件** - 保存为 .md 或 .txt 文件
* **仅导出结构** - 只导出目录树，不含文件内容
* **时间戳** - 自动添加生成时间

### 🎯 右键菜单
* 切换完整/骨架模式
* 加入白名单/黑名单
* 在文件管理器中打开
* 复制文件路径

---

## 🚀 极速起步

你可以克隆仓库，或者干脆只直接下载这一个文件：

```bash
# 1. 下载单文件脚本
curl -O https://raw.githubusercontent.com/SCWM-P/ProjectReader/main/ProjectReader.py

# 2. 直接运行
python ProjectReader.py
```
*(就这么简单。)*

---

## 📖 使用指南

### 基本流程

1. **运行程序**
   ```bash
   python ProjectReader.py
   ```

2. **选择项目**
   - 点击"浏览"按钮选择项目文件夹
   - 或直接输入路径后点击"扫描"
   - 也可以从"历史"菜单选择最近的项目

3. **配置过滤**
   - 程序自动识别项目类型（Python/Node.js/Java/Rust/Go）
   - 可在白名单/黑名单中添加自定义规则
   - 使用"模板"按钮快速应用常用规则

4. **选择文件**
   - 在文件树中勾选/取消勾选文件
   - 使用搜索框快速定位
   - 右键菜单切换骨架模式

5. **导出使用**
   - 点击"复制"按钮复制到剪贴板
   - 或点击"导出文件"保存到本地
   - 直接粘贴到 ChatGPT/Claude 等 LLM 对话框

### 高级技巧

**骨架模式使用场景**
- 大型源文件需要展示结构时
- 向 LLM 介绍项目架构时
- 减少 Token 消耗时

**白名单穿透示例**
```
# 黑名单中有 node_modules
# 但白名单中添加：
node_modules/my-custom-lib/*.js

# 结果：只提取该目录下的 .js 文件
```

**搜索技巧**
- 搜索文件名：`config`
- 搜索扩展名：`.py`
- 支持部分匹配

---

## 📝 导出格式预览

一键点击 `[复制给 LLM]` 后，剪贴板会得到高度标准化的 Markdown：

```markdown
# Project Context: my_awesome_project
Generated: 2026-03-13 10:30:45
Project Type: Python

## 1. Directory Structure
```plaintext
my_awesome_project/
├── main.py
├── core/
│   └── processor.py [骨架]
└── README.md
```

## 2. File Contents

### File: `main.py`
```python
import argparse
from core.processor import DataProcessor

def main():
    parser = argparse.ArgumentParser()
    # ... main code ...
```

### File: `core/processor.py`
*(Skeleton mode - structure only)*
```python
class DataProcessor:
    def __init__(self, config: dict): ...
    async def process_batch(self, data: list) -> bool: ...
```
```

---

## 🎨 主题展示

### 浅色主题 ☀️
适合白天使用，清爽明亮

### 深色主题 🌙
适合夜间使用，护眼舒适

使用快捷键 `Ctrl+T` 或点击工具栏主题按钮即可切换。

---

## 🔧 配置文件

程序会在用户目录创建配置文件 `~/.projectreader_config.json`：

```json
{
  "theme": "dark",
  "recent_projects": [
    "/path/to/project1",
    "/path/to/project2"
  ],
  "window_geometry": "1400x850",
  "auto_redact": true,
  "last_export_path": "/path/to/exports"
}
```

可以手动编辑此文件来调整默认设置。

---

## 🆚 版本对比

| 特性 | v2.0 | v3.0 |
|------|------|------|
| 零依赖 | ✅ | ✅ |
| 智能过滤 | ✅ | ✅ |
| 骨架提取 | ✅ | ✅ |
| 安全脱敏 | ✅ | ✅ |
| 主题切换 | ❌ | ✅ |
| 实时搜索 | ❌ | ✅ |
| 历史记录 | ❌ | ✅ |
| 快捷键 | ❌ | ✅ |
| 导出文件 | ❌ | ✅ |
| 快速模板 | ❌ | ✅ |
| 详细统计 | ❌ | ✅ |
| 配置持久化 | ❌ | ✅ |

---

## 🛠️ 技术栈

- **Python 3.8+** - 核心语言
- **Tkinter** - GUI 框架（标准库）
- **pathlib** - 路径处理（标准库）
- **json** - 配置管理（标准库）
- **threading** - 异步扫描（标准库）
- **re** - 正则表达式（标准库）

**无任何第三方依赖！**

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发分支说明
- `main` - 稳定版本分支
- `claude-dev` - Claude Code 开发分支（v3.0+）

---

## 📄 License

MIT License - 完全开源，你可以随心所欲地魔改它！

Copyright (c) 2025 彭博 & Claude Code Contributors

---

## 🙏 致谢

感谢所有使用和反馈的用户！

特别感谢 Claude Code 对 v3.0 的全面重构贡献。

---

## 📮 反馈

如有问题或建议，欢迎：
- 提交 GitHub Issue
- 发起 Pull Request
- 分享你的使用体验

---

**让 LLM 真正理解你的代码！** 🚀
