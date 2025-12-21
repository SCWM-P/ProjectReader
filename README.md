# Project Reader

> **Zero-Dependency Codebase Serializer for LLMs.**
>
> Stop manually copy-pasting files. Feed your project context to LLMs efficiently.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-grey.svg)]()

---

### ⚡ Why?

I wanna to feed LLMs with a whole project directory instantly! LLMs have limited context windows. Sending `node_modules` or huge `*.log` files is a waste of tokens and money.
**Project Reader** solves this with a lightweight GUI that helps you **select**, **filter**, and **summarize** your codebase into a single, clean Markdown block.


### ✨ Features

*   **🚫 Zero Dependencies**: No `pip install`. Uses standard `tkinter` & `pathlib`.
*   **📦 Smart Summary**: Fold unimportant directories (logs, assets) into 1-line summaries to save tokens.
*   **👁️ Visual Tree**: Interactive checkbox tree. What you see is what you get.
*   **🛡️ Privacy First**: Runs 100% locally. No API keys required.
*   **📋 One-Click Copy**: Generate formatted Markdown to clipboard instantly.

---

### 🚀 Quick Start

1.  **Download** the script.
2.  **Run** it.

```bash
python ProjectReader.py
```

*(That's it. Seriously.)*

---

### ⚙️ Configuration (`ProjectReader.yaml`)

The tool auto-generates a config file on first run. You can hack it:

```yaml
# Token Savers
max_chars_python: 8000
max_chars_code: 3000

# Noise Filters (Glob patterns)
ignore_patterns:
  - .git
  - __pycache__
  - node_modules
  - *.pyc

# Context Compressors (Show structure, hide content)
summary_patterns:
  - migrations/*.py
  - *.log
  - assets/*
```

---

### 📝 License

MIT License. Customize your own version as you like.