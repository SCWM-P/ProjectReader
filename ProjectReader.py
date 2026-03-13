"""
ProjectReader for LLMs - Enhanced Edition
Version: 3.0.0
Description: Zero-dependency, intelligent codebase packer for Large Language Models.
Author: Enhanced by Claude Code
"""

import os
import re
import json
import fnmatch
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import defaultdict

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

VERSION = "3.0.0"
CONFIG_FILE = Path.home() / ".projectreader_config.json"

FILE_ICONS = {
    '.py': '🐍', '.js': '🟨', '.ts': '🟦', '.jsx': '⚛️', '.tsx': '⚛️',
    '.java': '☕', '.cpp': '⚙️', '.c': '⚙️', '.h': '📄', '.cs': '💠',
    '.html': '🌐', '.css': '🎨', '.scss': '🎨', '.md': '📝', '.json': '🔧',
    '.yaml': '🔧', '.yml': '🔧', '.xml': '📋', '.sh': '🐧', '.bash': '🐧',
    '.rs': '🦀', '.go': '🐹', '.sql': '💾', '.txt': '📄', '.vue': '💚',
    '.php': '🐘', '.rb': '💎', '.swift': '🦅', '.kt': '🟣', '.dart': '🎯'
}
DEFAULT_ICON = '📄'
FOLDER_ICON = '📂'

STATE_UNCHECKED = 0
STATE_CHECKED = 1
STATE_PARTIAL = 2

ICONS_STATE = {
    STATE_UNCHECKED: "☐",
    STATE_CHECKED: "☑",
    STATE_PARTIAL: "⊟"
}

PROJECT_PRESETS = {
    "Python": {
        "detect": ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"],
        "ignore": ["__pycache__", "*.pyc", "venv", "env", ".venv", ".env",
                   ".pytest_cache", ".tox", "build", "dist", "*.egg-info", ".mypy_cache"]
    },
    "Node.js / Web": {
        "detect": ["package.json", "yarn.lock", "package-lock.json"],
        "ignore": ["node_modules", "dist", ".next", "out", ".nuxt", ".env",
                   "build", ".cache", "coverage", ".turbo"]
    },
    "Java": {
        "detect": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "ignore": ["target", "build", ".gradle", ".idea", "*.class", "*.jar"]
    },
    "Rust": {
        "detect": ["Cargo.toml"],
        "ignore": ["target", "Cargo.lock"]
    },
    "Go": {
        "detect": ["go.mod", "go.sum"],
        "ignore": ["vendor", "bin"]
    },
    "Default / Generic": {
        "detect": [],
        "ignore": [".git", ".svn", ".hg", ".idea", ".vscode", ".DS_Store",
                   "*.exe", "*.dll", "*.so", "*.dylib", "*.jpg", "*.jpeg",
                   "*.png", "*.gif", "*.mp4", "*.mp3", "*.zip", "*.tar.gz",
                   "*.pdf", "*.sqlite", "*.db", "Thumbs.db"]
    }
}

# Theme configurations
THEMES = {
    "light": {
        "bg": "#ffffff",
        "fg": "#000000",
        "select_bg": "#e3f2fd",
        "select_fg": "#000000",
        "preview_bg": "#f5f5f5",
        "preview_fg": "#000000",
        "tree_bg": "#ffffff",
        "toolbar_bg": "#f0f0f0",
        "status_bg": "#e8e8e8",
        "button_bg": "#e0e0e0",
        "accent": "#1976d2"
    },
    "dark": {
        "bg": "#1e1e1e",
        "fg": "#d4d4d4",
        "select_bg": "#264f78",
        "select_fg": "#ffffff",
        "preview_bg": "#252526",
        "preview_fg": "#d4d4d4",
        "tree_bg": "#252526",
        "toolbar_bg": "#2d2d30",
        "status_bg": "#007acc",
        "button_bg": "#3c3c3c",
        "accent": "#007acc"
    }
}

# ============================================================================
# CONFIGURATION MANAGER
# ============================================================================

class ConfigManager:
    """Manages persistent configuration and history"""

    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "theme": "light",
            "recent_projects": [],
            "window_geometry": "1400x850",
            "auto_redact": True,
            "last_export_path": str(Path.home())
        }

    def save_config(self):
        """Save configuration to file"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def add_recent_project(self, path: str):
        """Add project to recent history"""
        recent = self.config.get("recent_projects", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.config["recent_projects"] = recent[:10]  # Keep last 10
        self.save_config()

    def get_recent_projects(self) -> List[str]:
        """Get recent projects list"""
        return [p for p in self.config.get("recent_projects", []) if os.path.exists(p)]

# ============================================================================
# CORE LOGIC ENGINE
# ============================================================================

class CodeProcessor:
    """Handles code processing operations"""

    SECRET_PATTERN = re.compile(
        r'(?i)(api[_-]?key|apikey|secret|password|passwd|token|auth[_-]?token)\s*[:=]\s*(["\'])[a-zA-Z0-9\-_]{10,}\2'
    )

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count (rough approximation)"""
        return len(text) // 4

    @staticmethod
    def redact_secrets(text: str) -> str:
        """Replace secrets with placeholder"""
        return CodeProcessor.SECRET_PATTERN.sub(r'\1 = "[REDACTED_SECRET]"', text)

    @staticmethod
    def extract_skeleton(text: str, ext: str) -> str:
        """Extract structural skeleton from code"""
        lines = text.splitlines()
        skeleton = []

        if ext == '.py':
            py_pat = re.compile(r'^\s*(def |class |async def |@)')
            in_docstring = False

            for line in lines:
                stripped = line.strip()
                if '"""' in stripped or "'''" in stripped:
                    in_docstring = not in_docstring
                    skeleton.append(line)
                    continue
                if in_docstring or stripped.startswith('#'):
                    skeleton.append(line)
                    continue
                if py_pat.match(line):
                    if line.strip().startswith('@'):
                        skeleton.append(line)
                    else:
                        skeleton.append(line + " ...")

        elif ext in ['.js', '.ts', '.jsx', '.tsx']:
            js_pat = re.compile(r'^\s*(export |public |private |protected |async )?(class |interface |function |const |let |var )\s*[a-zA-Z0-9_$]+')
            for line in lines:
                if js_pat.match(line) or line.strip().startswith('//'):
                    skeleton.append(line)

        elif ext in ['.java', '.cs', '.cpp', '.c', '.h']:
            c_pat = re.compile(r'^\s*(public |private |protected |static |final |virtual |override )*(class |interface |struct |enum |void |int |bool |string |double |float )')
            for line in lines:
                if c_pat.match(line):
                    skeleton.append(line)

        if not skeleton:
            return "(No structural skeleton found. Try full context mode.)"
        return "\n".join(skeleton)

# ============================================================================
# PROJECT ANALYZER
# ============================================================================

class ProjectAnalyzer:
    """Analyzes project structure and applies filters"""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.whitelist: List[str] = []
        self.blacklist: List[str] = []
        self.gitignore_rules: List[str] = []
        self.detected_type = "Default / Generic"
        self.file_stats: Dict[str, int] = defaultdict(int)
        self.top_files: List[Tuple[int, Path]] = []

    def auto_detect(self):
        """Auto-detect project type and apply presets"""
        for ptype, preset in PROJECT_PRESETS.items():
            if any((self.root / f).exists() for f in preset["detect"]):
                self.detected_type = ptype
                self.blacklist.extend(preset["ignore"])
                break

        self.blacklist.extend(PROJECT_PRESETS["Default / Generic"]["ignore"])
        self._parse_gitignore()
        self.blacklist = list(set(self.blacklist))

    def _parse_gitignore(self):
        """Parse .gitignore file"""
        gitignore_path = self.root / ".gitignore"
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if line.endswith('/'):
                                line = line[:-1]
                            self.gitignore_rules.append(line)
            except Exception:
                pass

    def _match_pattern(self, rel_path_str: str, name: str, patterns: List[str]) -> bool:
        """Match path against patterns"""
        rel_path_str = rel_path_str.replace(os.sep, '/')
        for pat in patterns:
            if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_path_str, pat):
                return True
            if '/' in pat and fnmatch.fnmatch(rel_path_str, pat.lstrip('/')):
                return True
        return False

    def is_ignored(self, path: Path) -> bool:
        """Check if path should be ignored"""
        try:
            rel_str = str(path.relative_to(self.root)).replace(os.sep, '/')
        except ValueError:
            return True

        name = path.name
        is_white = self._match_pattern(rel_str, name, self.whitelist) if self.whitelist else False
        is_black = self._match_pattern(rel_str, name, self.blacklist) or \
                   self._match_pattern(rel_str, name, self.gitignore_rules)

        # Whitelist override
        if is_white:
            return False

        # Blacklist with penetration
        if is_black:
            if path.is_dir() and self.whitelist:
                for w in self.whitelist:
                    if '*' in w or w.startswith(rel_str + '/'):
                        return False
            return True

        # Whitelist exclusive mode
        if self.whitelist and path.is_file():
            return True

        return False

# ============================================================================
# MAIN GUI APPLICATION
# ============================================================================

class ProjectReaderGUI:
    """Main GUI application"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"ProjectReader for LLMs v{VERSION}")

        # Configuration
        self.config = ConfigManager()
        geometry = self.config.config.get("window_geometry", "1400x850")
        self.root.geometry(geometry)

        # State
        self.analyzer: Optional[ProjectAnalyzer] = None
        self.tree_nodes: Dict[str, dict] = {}
        self.path_to_iid: Dict[Path, str] = {}
        self.current_theme = self.config.config.get("theme", "light")
        self.history_states: List[Dict] = []
        self.history_index = -1

        # Variables
        self.var_redact = tk.BooleanVar(value=self.config.config.get("auto_redact", True))
        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", self._on_search_changed)

        # Build UI
        self._apply_theme()
        self._build_ui()
        self._setup_shortcuts()
        self._setup_drag_drop()

        # Window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_theme(self):
        """Apply current theme"""
        theme = THEMES[self.current_theme]
        style = ttk.Style()

        try:
            style.theme_use('clam')
        except tk.TclError:
            pass

        # Configure styles
        style.configure(".", background=theme["bg"], foreground=theme["fg"])
        style.configure("TFrame", background=theme["bg"])
        style.configure("TLabel", background=theme["bg"], foreground=theme["fg"])
        style.configure("TButton", background=theme["button_bg"], foreground=theme["fg"])
        style.configure("Toolbar.TFrame", background=theme["toolbar_bg"])
        style.configure("Status.TFrame", background=theme["status_bg"])
        style.configure("Treeview",
                       background=theme["tree_bg"],
                       foreground=theme["fg"],
                       fieldbackground=theme["tree_bg"],
                       rowheight=24,
                       font=('Consolas', 10))
        style.map("Treeview",
                 background=[('selected', theme["select_bg"])],
                 foreground=[('selected', theme["select_fg"])])

    def _build_ui(self):
        """Build complete user interface"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Build components
        self._build_toolbar(main_frame)
        self._build_content(main_frame)
        self._build_statusbar(main_frame)

    def _build_toolbar(self, parent):
        """Build toolbar"""
        toolbar = ttk.Frame(parent, style="Toolbar.TFrame", padding=5)
        toolbar.pack(fill=tk.X)

        # Left section - File operations
        left_frame = ttk.Frame(toolbar, style="Toolbar.TFrame")
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(left_frame, text="📁 项目:", font=('', 10, 'bold')).pack(side=tk.LEFT, padx=5)

        self.entry_path = ttk.Entry(left_frame, font=('Consolas', 10))
        self.entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Button(left_frame, text="浏览", command=self._browse_dir, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_frame, text="🚀 扫描", command=self._start_scan, width=8).pack(side=tk.LEFT, padx=2)

        # Recent projects menu
        self.recent_menu = tk.Menu(self.root, tearoff=0)
        self._update_recent_menu()
        recent_btn = ttk.Menubutton(left_frame, text="📜 历史", menu=self.recent_menu, width=8)
        recent_btn.pack(side=tk.LEFT, padx=2)

        # Right section - View operations
        right_frame = ttk.Frame(toolbar, style="Toolbar.TFrame")
        right_frame.pack(side=tk.RIGHT)

        ttk.Button(right_frame, text="🔍 搜索", command=self._focus_search, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(right_frame, text="⚙️ 模板", command=self._show_templates, width=8).pack(side=tk.LEFT, padx=2)

        # Theme toggle
        theme_icon = "🌙" if self.current_theme == "light" else "☀️"
        self.theme_btn = ttk.Button(right_frame, text=theme_icon, command=self._toggle_theme, width=4)
        self.theme_btn.pack(side=tk.LEFT, padx=2)

    def _build_content(self, parent):
        """Build main content area"""
        # Search bar
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(search_frame, text="🔍 搜索:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(search_frame, textvariable=self.var_search, font=('Consolas', 10))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry = search_entry

        clear_btn = ttk.Button(search_frame, text="✕", command=self._clear_search, width=3)
        clear_btn.pack(side=tk.LEFT)

        # Main paned window
        self.paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left panel - File tree
        self._build_tree_panel()

        # Middle panel - Preview
        self._build_preview_panel()

        # Right panel - Controls
        self._build_control_panel()

    def _build_tree_panel(self):
        """Build file tree panel"""
        left_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, weight=1)

        # Header
        tree_header = ttk.Frame(left_frame)
        tree_header.pack(fill=tk.X)

        ttk.Label(tree_header, text="文件结构", font=('', 10, 'bold')).pack(side=tk.LEFT, pady=2)
        ttk.Button(tree_header, text="全选/反选", command=self._toggle_all, width=12).pack(side=tk.RIGHT, padx=2)
        ttk.Button(tree_header, text="展开全部", command=self._expand_all, width=12).pack(side=tk.RIGHT, padx=2)
        ttk.Button(tree_header, text="折叠全部", command=self._collapse_all, width=12).pack(side=tk.RIGHT, padx=2)

        # Tree view
        tree_container = ttk.Frame(left_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_container, columns=("size",), selectmode="browse")
        self.tree.heading("#0", text=" 名称", anchor="w")
        self.tree.heading("size", text="大小", anchor="e")
        self.tree.column("#0", width=300)
        self.tree.column("size", width=80, anchor="e")

        # Scrollbars
        ysb = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        xsb = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Tags
        self.tree.tag_configure('ignored', foreground='#888888')
        self.tree.tag_configure('skeleton', foreground='#0066cc')
        self.tree.tag_configure('search_match', background='#ffff99')

        # Bindings
        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-3>", self._show_context_menu)

    def _build_preview_panel(self):
        """Build preview panel"""
        mid_frame = ttk.Frame(self.paned)
        self.paned.add(mid_frame, weight=2)

        mid_frame.rowconfigure(1, weight=1)
        mid_frame.columnconfigure(0, weight=1)

        # Header
        preview_header = ttk.Frame(mid_frame)
        preview_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=2)

        self.lbl_preview = ttk.Label(preview_header, text="实时预览", font=('', 10, 'bold'))
        self.lbl_preview.pack(side=tk.LEFT)

        # Preview text
        theme = THEMES[self.current_theme]
        self.txt_preview = tk.Text(mid_frame, wrap=tk.NONE, font=('Consolas', 10),
                                  bg=theme["preview_bg"], fg=theme["preview_fg"],
                                  insertbackground=theme["fg"])

        # Scrollbars
        p_ysb = ttk.Scrollbar(mid_frame, orient=tk.VERTICAL, command=self.txt_preview.yview)
        p_xsb = ttk.Scrollbar(mid_frame, orient=tk.HORIZONTAL, command=self.txt_preview.xview)
        self.txt_preview.configure(yscrollcommand=p_ysb.set, xscrollcommand=p_xsb.set)

        self.txt_preview.grid(row=1, column=0, sticky="nsew")
        p_ysb.grid(row=1, column=1, sticky="ns")
        p_xsb.grid(row=2, column=0, sticky="ew")

    def _build_control_panel(self):
        """Build control panel"""
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=1)

        # Project info
        info_lf = ttk.LabelFrame(right_frame, text="📊 项目信息")
        info_lf.pack(fill=tk.X, pady=5)

        self.lbl_proj_type = ttk.Label(info_lf, text="类型: 未分析")
        self.lbl_proj_type.pack(anchor="w", padx=5, pady=2)

        self.lbl_file_count = ttk.Label(info_lf, text="文件: 0")
        self.lbl_file_count.pack(anchor="w", padx=5, pady=2)

        self.lbl_selected_count = ttk.Label(info_lf, text="已选: 0")
        self.lbl_selected_count.pack(anchor="w", padx=5, pady=2)

        # Large files radar
        radar_lf = ttk.LabelFrame(right_frame, text="⚠️ 大文件雷达")
        radar_lf.pack(fill=tk.X, pady=5)

        theme = THEMES[self.current_theme]
        self.txt_radar = tk.Text(radar_lf, height=6, font=('Consolas', 9),
                                state=tk.DISABLED, bg=theme["preview_bg"],
                                fg=theme["preview_fg"])
        self.txt_radar.pack(fill=tk.BOTH, padx=5, pady=5)

        # Options
        options_lf = ttk.LabelFrame(right_frame, text="⚙️ 选项")
        options_lf.pack(fill=tk.X, pady=5)

        ttk.Checkbutton(options_lf, text="自动脱敏密钥",
                       variable=self.var_redact).pack(anchor="w", padx=5, pady=2)

        # Filters
        filter_paned = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        filter_paned.pack(fill=tk.BOTH, expand=True, pady=5)

        # Whitelist
        white_lf = ttk.LabelFrame(filter_paned, text="✅ 白名单")
        self.txt_white = tk.Text(white_lf, height=4, font=('Consolas', 9),
                                bg=theme["preview_bg"], fg=theme["preview_fg"])
        self.txt_white.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        filter_paned.add(white_lf, weight=1)

        # Blacklist
        black_lf = ttk.LabelFrame(filter_paned, text="🚫 黑名单")
        self.txt_black = tk.Text(black_lf, height=6, font=('Consolas', 9),
                                bg=theme["preview_bg"], fg=theme["preview_fg"])
        self.txt_black.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        filter_paned.add(black_lf, weight=1)

        # Export buttons
        export_frame = ttk.Frame(right_frame)
        export_frame.pack(fill=tk.X, pady=5)

        ttk.Button(export_frame, text="📋 复制",
                  command=self._export_clipboard).pack(fill=tk.X, pady=2)
        ttk.Button(export_frame, text="💾 导出文件",
                  command=self._export_file).pack(fill=tk.X, pady=2)
        ttk.Button(export_frame, text="📝 仅结构",
                  command=lambda: self._export_clipboard(structure_only=True)).pack(fill=tk.X, pady=2)

        # Context menu
        self.ctx_menu = tk.Menu(self.root, tearoff=0)
        self.ctx_menu.add_command(label="🔄 切换完整/骨架模式", command=self._ctx_toggle_skeleton)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="✅ 加入白名单", command=self._ctx_add_whitelist)
        self.ctx_menu.add_command(label="🚫 加入黑名单", command=self._ctx_add_blacklist)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="📂 在文件管理器中打开", command=self._ctx_open_in_explorer)
        self.ctx_menu.add_command(label="📋 复制路径", command=self._ctx_copy_path)

    def _build_statusbar(self, parent):
        """Build status bar"""
        status_frame = ttk.Frame(parent, style="Status.TFrame", padding=5)
        status_frame.pack(fill=tk.X)

        self.lbl_status = ttk.Label(status_frame, text="就绪", style="Status.TFrame")
        self.lbl_status.pack(side=tk.LEFT)

        self.lbl_tokens = ttk.Label(status_frame, text="Tokens: 0 🟢",
                                   font=('', 10, 'bold'), style="Status.TFrame")
        self.lbl_tokens.pack(side=tk.RIGHT, padx=10)

        self.progress = ttk.Progressbar(status_frame, mode='indeterminate', length=100)

    # ========================================================================
    # SHORTCUTS & DRAG-DROP
    # ========================================================================

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind('<Control-o>', lambda _: self._browse_dir())
        self.root.bind('<Control-f>', lambda _: self._focus_search())
        self.root.bind('<Control-e>', lambda _: self._export_clipboard())
        self.root.bind('<Control-s>', lambda _: self._start_scan())
        self.root.bind('<Control-t>', lambda _: self._toggle_theme())
        self.root.bind('<Escape>', lambda _: self._clear_search())
        self.root.bind('<F5>', lambda _: self._start_scan())

    def _setup_drag_drop(self):
        """Setup drag and drop support"""
        # Note: Basic drag-drop without external dependencies
        # This is simplified - full implementation would use tkinterdnd2
        pass

    # ========================================================================
    # MENU HANDLERS
    # ========================================================================

    def _update_recent_menu(self):
        """Update recent projects menu"""
        self.recent_menu.delete(0, tk.END)
        recent = self.config.get_recent_projects()

        if not recent:
            self.recent_menu.add_command(label="(无历史记录)", state=tk.DISABLED)
        else:
            for path in recent:
                self.recent_menu.add_command(
                    label=f"📁 {Path(path).name} - {path}",
                    command=lambda p=path: self._load_recent_project(p)
                )

    def _load_recent_project(self, path: str):
        """Load a recent project"""
        self.entry_path.delete(0, tk.END)
        self.entry_path.insert(0, path)
        self._start_scan()

    def _show_templates(self):
        """Show quick filter templates"""
        menu = tk.Menu(self.root, tearoff=0)

        templates = {
            "Web 项目 (清除 node_modules)": ["node_modules", "dist", "build", ".next"],
            "Python 项目 (清除缓存)": ["__pycache__", "*.pyc", "venv", ".venv"],
            "只看源代码": ["*.py", "*.js", "*.ts", "*.java", "*.cpp", "*.c", "*.h"],
            "只看配置文件": ["*.json", "*.yaml", "*.yml", "*.toml", "*.ini"],
            "清空过滤器": []
        }

        for name, patterns in templates.items():
            menu.add_command(
                label=name,
                command=lambda p=patterns: self._apply_template(p)
            )

        menu.post(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def _apply_template(self, patterns: List[str]):
        """Apply a filter template"""
        if not patterns:
            self.txt_white.delete("1.0", tk.END)
            self.txt_black.delete("1.0", tk.END)
        else:
            self.txt_black.delete("1.0", tk.END)
            self.txt_black.insert("1.0", "\n".join(patterns))

        if self.analyzer:
            if messagebox.askyesno("应用模板", "是否立即重新扫描？"):
                self._start_scan()

    def _toggle_theme(self):
        """Toggle between light and dark theme"""
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.config.config["theme"] = self.current_theme
        self.config.save_config()

        # Update button icon
        theme_icon = "🌙" if self.current_theme == "light" else "☀️"
        self.theme_btn.config(text=theme_icon)

        # Apply theme
        self._apply_theme()

        # Update preview colors
        theme = THEMES[self.current_theme]
        self.txt_preview.config(bg=theme["preview_bg"], fg=theme["preview_fg"],
                               insertbackground=theme["fg"])
        self.txt_radar.config(bg=theme["preview_bg"], fg=theme["preview_fg"])
        self.txt_white.config(bg=theme["preview_bg"], fg=theme["preview_fg"])
        self.txt_black.config(bg=theme["preview_bg"], fg=theme["preview_fg"])

    # ========================================================================
    # SEARCH FUNCTIONALITY
    # ========================================================================

    def _focus_search(self):
        """Focus search entry"""
        self.search_entry.focus_set()

    def _clear_search(self):
        """Clear search"""
        self.var_search.set("")

    def _on_search_changed(self, *_):
        """Handle search text change"""
        search_text = self.var_search.get().lower()

        # Remove all search highlights
        for iid in self.tree_nodes:
            tags = list(self.tree.item(iid, 'tags'))
            if 'search_match' in tags:
                tags.remove('search_match')
                self.tree.item(iid, tags=tags)

        if not search_text:
            return

        # Highlight matches
        matches = []
        for iid, node in self.tree_nodes.items():
            if search_text in node['path'].name.lower():
                tags = list(self.tree.item(iid, 'tags'))
                if 'search_match' not in tags:
                    tags.append('search_match')
                self.tree.item(iid, tags=tags)
                matches.append(iid)

                # Expand parent
                parent = self.tree.parent(iid)
                while parent:
                    self.tree.item(parent, open=True)
                    parent = self.tree.parent(parent)

        # Focus first match
        if matches:
            self.tree.selection_set(matches[0])
            self.tree.see(matches[0])

    # ========================================================================
    # PROJECT SCANNING
    # ========================================================================

    def _browse_dir(self):
        """Browse for directory"""
        path = filedialog.askdirectory(title="选择项目文件夹")
        if path:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, path)
            self._start_scan()

    def _start_scan(self):
        """Start project scanning"""
        path_str = self.entry_path.get().strip()
        if not os.path.isdir(path_str):
            messagebox.showwarning("错误", "请提供有效的项目文件夹路径！")
            return

        # Save to history
        self.config.add_recent_project(path_str)
        self._update_recent_menu()

        # Initialize analyzer
        self.analyzer = ProjectAnalyzer(Path(path_str))
        self.analyzer.auto_detect()

        # Apply filters
        white_text = self.txt_white.get("1.0", tk.END).strip()
        if white_text:
            self.analyzer.whitelist = [w.strip() for w in white_text.splitlines() if w.strip()]

        black_text = self.txt_black.get("1.0", tk.END).strip()
        if black_text:
            self.analyzer.blacklist.extend([b.strip() for b in black_text.splitlines() if b.strip()])

        # Update UI
        self.lbl_proj_type.config(text=f"类型: {self.analyzer.detected_type}")
        self.lbl_status.config(text="扫描中...")
        self.progress.pack(side=tk.LEFT, padx=10)
        self.progress.start(10)

        # Clear tree
        self.tree.delete(*self.tree.get_children())
        self.tree_nodes.clear()
        self.path_to_iid.clear()

        # Start scan thread
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        """Background scanning thread"""
        if not self.analyzer:
            return

        nodes = []
        root_path = self.analyzer.root

        def walk_dir(current: Path):
            if not self.analyzer:
                return
            if self.analyzer.is_ignored(current):
                return

            is_dir = current.is_dir()
            try:
                size = current.stat().st_size if not is_dir else 0
            except:
                size = 0

            if not is_dir:
                self.analyzer.file_stats[current.suffix.lower()] += size
                self.analyzer.top_files.append((size, current))

            nodes.append({
                'path': current,
                'is_dir': is_dir,
                'size': size,
                'parent': current.parent
            })

            if is_dir:
                try:
                    children = sorted(
                        current.iterdir(),
                        key=lambda x: (not x.is_dir(), x.name.lower())
                    )
                    for child in children:
                        walk_dir(child)
                except Exception:
                    pass

        walk_dir(root_path)
        self.analyzer.top_files.sort(key=lambda x: x[0], reverse=True)

        # Update UI in main thread
        self.root.after(0, lambda: self._build_tree(nodes))

    def _build_tree(self, nodes: List[dict]):
        """Build tree from scanned nodes"""
        if not self.analyzer:
            return

        children_map = defaultdict(list)
        for n in nodes:
            children_map[n['parent']].append(n)

        def insert_node(node_data, parent_iid):
            p = node_data['path']
            is_dir = node_data['is_dir']

            icon = FOLDER_ICON if is_dir else FILE_ICONS.get(p.suffix.lower(), DEFAULT_ICON)
            size_str = self._human_size(node_data['size']) if not is_dir else ""
            text = f"{ICONS_STATE[STATE_CHECKED]} {icon} {p.name}"

            iid = self.tree.insert(parent_iid, 'end', text=text, values=(size_str,), open=False)
            self.tree_nodes[iid] = {
                'path': p,
                'state': STATE_CHECKED,
                'is_dir': is_dir,
                'size': node_data['size'],
                'skeleton': False
            }
            self.path_to_iid[p] = iid

            if is_dir and p in children_map:
                for child in children_map[p]:
                    insert_node(child, iid)

        root_node = {
            'path': self.analyzer.root,
            'is_dir': True,
            'size': 0,
            'parent': None
        }
        insert_node(root_node, "")

        # Update UI
        self._update_radar()
        self._update_statistics()
        self._recalculate_tokens()

        self.progress.stop()
        self.progress.pack_forget()
        self.lbl_status.config(text=f"就绪 - 共 {len(self.tree_nodes)} 个节点")

    def _human_size(self, size: float) -> str:
        """Convert size to human readable format"""
        for unit in ['B', 'KB', 'MB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}GB"

    def _update_radar(self):
        """Update large files radar"""
        if not self.analyzer:
            return

        self.txt_radar.config(state=tk.NORMAL)
        self.txt_radar.delete("1.0", tk.END)

        for i, (size, p) in enumerate(self.analyzer.top_files[:5]):
            try:
                rel = p.relative_to(self.analyzer.root)
                self.txt_radar.insert(tk.END,
                    f"{i+1}. {rel}\n   {self._human_size(size)}\n")
            except Exception:
                pass

        self.txt_radar.config(state=tk.DISABLED)

    def _update_statistics(self):
        """Update statistics display"""
        if not self.analyzer:
            return

        total_files = sum(1 for n in self.tree_nodes.values() if not n['is_dir'])
        selected_files = sum(1 for n in self.tree_nodes.values()
                           if not n['is_dir'] and n['state'] in [STATE_CHECKED])

        self.lbl_file_count.config(text=f"文件: {total_files}")
        self.lbl_selected_count.config(text=f"已选: {selected_files}")

    # ========================================================================
    # TREE OPERATIONS
    # ========================================================================

    def _expand_all(self):
        """Expand all tree nodes"""
        def expand_recursive(iid):
            self.tree.item(iid, open=True)
            for child in self.tree.get_children(iid):
                expand_recursive(child)

        for root_iid in self.tree.get_children(""):
            expand_recursive(root_iid)

    def _collapse_all(self):
        """Collapse all tree nodes"""
        def collapse_recursive(iid):
            self.tree.item(iid, open=False)
            for child in self.tree.get_children(iid):
                collapse_recursive(child)

        for root_iid in self.tree.get_children(""):
            collapse_recursive(root_iid)

    def _toggle_all(self):
        """Toggle all nodes"""
        root_children = self.tree.get_children("")
        if root_children:
            self._toggle_node_state(root_children[0])

    def _refresh_node_ui(self, iid: str):
        """Refresh node UI appearance"""
        node = self.tree_nodes[iid]
        p = node['path']
        state = node['state']
        is_dir = node['is_dir']
        skeleton = node['skeleton']

        icon = FOLDER_ICON if is_dir else FILE_ICONS.get(p.suffix.lower(), DEFAULT_ICON)
        base_text = f"{ICONS_STATE[state]} {icon} {p.name}"

        tags = []
        if skeleton and not is_dir:
            base_text += " [骨架]"
            tags.append('skeleton')
        elif state == STATE_UNCHECKED:
            tags.append('ignored')

        self.tree.item(iid, text=base_text, tags=tags)

    def _toggle_node_state(self, iid: str):
        """Toggle node selection state"""
        current_state = self.tree_nodes[iid]['state']
        new_state = STATE_UNCHECKED if current_state in [STATE_CHECKED, STATE_PARTIAL] else STATE_CHECKED

        def cascade_down(target_iid, st):
            self.tree_nodes[target_iid]['state'] = st
            self._refresh_node_ui(target_iid)
            for child in self.tree.get_children(target_iid):
                cascade_down(child, st)

        cascade_down(iid, new_state)

        def cascade_up(target_iid):
            parent = self.tree.parent(target_iid)
            if not parent:
                return

            siblings = self.tree.get_children(parent)
            states = set(self.tree_nodes[s]['state'] for s in siblings)

            if len(states) == 1 and STATE_CHECKED in states:
                p_state = STATE_CHECKED
            elif len(states) == 1 and STATE_UNCHECKED in states:
                p_state = STATE_UNCHECKED
            else:
                p_state = STATE_PARTIAL

            self.tree_nodes[parent]['state'] = p_state
            self._refresh_node_ui(parent)
            cascade_up(parent)

        cascade_up(iid)
        self._update_statistics()
        self._recalculate_tokens()

    def _on_tree_click(self, event):
        """Handle tree click - toggle state on checkbox"""
        iid = self.tree.identify_row(event.y)
        if not iid:
            return

        bbox = self.tree.bbox(iid, "#0")
        if bbox:
            x, y, w, h = bbox
            if x <= event.x <= x + 25:
                self._toggle_node_state(iid)
                return "break"

    def _on_tree_double_click(self, event):
        """Handle tree double-click - toggle state"""
        iid = self.tree.identify_row(event.y)
        if iid:
            self._toggle_node_state(iid)
            return "break"

    def _on_tree_select(self, event):
        """Handle tree selection - show preview"""
        sel = self.tree.selection()
        if not sel:
            return

        iid = sel[0]
        node = self.tree_nodes[iid]

        self.txt_preview.config(state=tk.NORMAL)
        self.txt_preview.delete("1.0", tk.END)

        if node['is_dir']:
            self.lbl_preview.config(text=f"📂 目录: {node['path'].name}")

            # Show directory summary
            file_count = sum(1 for child_iid in self.tree.get_children(iid)
                           if not self.tree_nodes[child_iid]['is_dir'])
            dir_count = sum(1 for child_iid in self.tree.get_children(iid)
                          if self.tree_nodes[child_iid]['is_dir'])

            self.txt_preview.insert(tk.END, f"目录: {node['path'].name}\n\n")
            self.txt_preview.insert(tk.END, f"包含: {file_count} 个文件, {dir_count} 个子目录\n")
        else:
            self.lbl_preview.config(text=f"📄 预览: {node['path'].name}")
            content = self._read_file_content(node['path'], node['skeleton'])

            lines = content.splitlines()
            preview_lines = lines[:1000]
            self.txt_preview.insert(tk.END, "\n".join(preview_lines))

            if len(lines) > 1000:
                self.txt_preview.insert(tk.END, "\n\n... (预览已截断) ...")

        self.txt_preview.config(state=tk.DISABLED)

    def _read_file_content(self, path: Path, skeleton: bool) -> str:
        """Read file content with optional skeleton extraction"""
        try:
            if path.stat().st_size > 1024 * 500 and not skeleton:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    preview = f.read(5000)
                return f"// 文件过大 ({self._human_size(path.stat().st_size)})，已截断\n{preview}\n// ..."

            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            if self.var_redact.get():
                content = CodeProcessor.redact_secrets(content)

            if skeleton:
                content = CodeProcessor.extract_skeleton(content, path.suffix.lower())

            return content
        except Exception as e:
            return f"无法读取文件: {str(e)}"

    # ========================================================================
    # CONTEXT MENU
    # ========================================================================

    def _show_context_menu(self, event):
        """Show context menu"""
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self.ctx_menu.post(event.x_root, event.y_root)

    def _ctx_toggle_skeleton(self):
        """Toggle skeleton mode for selected file"""
        sel = self.tree.selection()
        if sel:
            iid = sel[0]
            node = self.tree_nodes[iid]
            if not node['is_dir']:
                node['skeleton'] = not node['skeleton']
                self._refresh_node_ui(iid)
                self._on_tree_select(None)
                self._recalculate_tokens()

    def _ctx_add_whitelist(self):
        """Add selected to whitelist"""
        if not self.analyzer:
            return

        sel = self.tree.selection()
        if sel:
            p = self.tree_nodes[sel[0]]['path']
            try:
                rel = p.relative_to(self.analyzer.root).as_posix()
            except:
                rel = p.name

            self.txt_white.insert(tk.END, f"\n{rel}")

            if messagebox.askyesno("提示", "已添加到白名单。是否立即重新扫描？"):
                self._start_scan()

    def _ctx_add_blacklist(self):
        """Add selected to blacklist"""
        if not self.analyzer:
            return

        sel = self.tree.selection()
        if sel:
            p = self.tree_nodes[sel[0]]['path']
            try:
                rel = p.relative_to(self.analyzer.root).as_posix()
            except:
                rel = p.name

            self.txt_black.insert(tk.END, f"\n{rel}")

            if messagebox.askyesno("提示", "已添加到黑名单。是否立即重新扫描？"):
                self._start_scan()

    def _ctx_open_in_explorer(self):
        """Open selected in file explorer"""
        sel = self.tree.selection()
        if sel:
            path = self.tree_nodes[sel[0]]['path']

            import subprocess
            import platform

            system = platform.system()
            try:
                if system == "Windows":
                    os.startfile(path if path.is_dir() else path.parent)
                elif system == "Darwin":  # macOS
                    subprocess.run(["open", path if path.is_dir() else path.parent])
                else:  # Linux
                    subprocess.run(["xdg-open", path if path.is_dir() else path.parent])
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件管理器: {str(e)}")

    def _ctx_copy_path(self):
        """Copy selected path to clipboard"""
        sel = self.tree.selection()
        if sel:
            path = str(self.tree_nodes[sel[0]]['path'])
            self.root.clipboard_clear()
            self.root.clipboard_append(path)
            self.lbl_status.config(text=f"已复制路径: {path}")

    # ========================================================================
    # TOKEN CALCULATION
    # ========================================================================

    def _recalculate_tokens(self):
        """Recalculate token estimate"""
        def task():
            total_chars = 0
            for iid, node in self.tree_nodes.items():
                if node['state'] in [STATE_CHECKED] and not node['is_dir']:
                    size = node['size']
                    if node['skeleton']:
                        size = size // 5
                    total_chars += size

            tokens = CodeProcessor.estimate_tokens('a' * total_chars)

            if tokens < 30000:
                color = "🟢"
            elif tokens < 80000:
                color = "🟡"
            else:
                color = "🔴"

            self.root.after(0, lambda: self.lbl_tokens.config(
                text=f"Tokens: {tokens:,} {color}"
            ))

        threading.Thread(target=task, daemon=True).start()

    # ========================================================================
    # EXPORT OPERATIONS
    # ========================================================================

    def _generate_tree_text(self, iid: str, prefix: str = "", is_last: bool = True) -> List[str]:
        """Generate tree structure text"""
        if not self.analyzer:
            return []

        node = self.tree_nodes[iid]
        if node['state'] == STATE_UNCHECKED:
            return []

        lines = []
        connector = "└── " if is_last else "├── "
        name = node['path'].name + ("/" if node['is_dir'] else "")

        if node['skeleton'] and not node['is_dir']:
            name += " [骨架]"

        if iid == self.path_to_iid.get(self.analyzer.root):
            lines.append(name)
        else:
            lines.append(f"{prefix}{connector}{name}")

        if node['is_dir']:
            children = [c for c in self.tree.get_children(iid)
                       if self.tree_nodes[c]['state'] != STATE_UNCHECKED]
            new_prefix = prefix + ("    " if is_last else "│   ")
            if iid == self.path_to_iid.get(self.analyzer.root):
                new_prefix = ""

            for i, c in enumerate(children):
                lines.extend(self._generate_tree_text(c, new_prefix, i == len(children) - 1))

        return lines

    def _export_clipboard(self, structure_only: bool = False):
        """Export to clipboard"""
        if not self.tree_nodes or not self.analyzer:
            messagebox.showwarning("提示", "请先扫描项目！")
            return

        self.lbl_status.config(text="正在生成内容...")

        def task():
            if not self.analyzer:
                return

            output = []
            output.append(f"# Project Context: {self.analyzer.root.name}")
            output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            output.append(f"\n## 1. Directory Structure\n```plaintext")

            root_iid = self.tree.get_children("")[0]
            tree_lines = self._generate_tree_text(root_iid)
            output.extend(tree_lines)
            output.append("```\n")

            if not structure_only:
                output.append("## 2. File Contents\n")

                for iid, node in self.tree_nodes.items():
                    if not node['is_dir'] and node['state'] == STATE_CHECKED:
                        try:
                            rel_path = node['path'].relative_to(self.analyzer.root).as_posix()
                        except ValueError:
                            rel_path = node['path'].name

                        content = self._read_file_content(node['path'], node['skeleton'])
                        ext = node['path'].suffix[1:] if node['path'].suffix else 'txt'

                        output.append(f"### File: `{rel_path}`")
                        if node['skeleton']:
                            output.append("*(Skeleton mode - structure only)*")
                        output.append(f"```{ext}\n{content}\n```\n")

            final_text = "\n".join(output)

            self.root.clipboard_clear()
            self.root.clipboard_append(final_text)

            tokens = CodeProcessor.estimate_tokens(final_text)

            self.root.after(0, lambda: messagebox.showinfo(
                "成功",
                f"内容已复制到剪贴板！\n\n预估消耗 {tokens:,} Tokens"
            ))
            self.root.after(0, lambda: self.lbl_status.config(text="导出完成"))

        threading.Thread(target=task, daemon=True).start()

    def _export_file(self):
        """Export to file"""
        if not self.tree_nodes or not self.analyzer:
            messagebox.showwarning("提示", "请先扫描项目！")
            return

        default_name = f"{self.analyzer.root.name}_context.md"
        initial_dir = self.config.config.get("last_export_path", str(Path.home()))

        filepath = filedialog.asksaveasfilename(
            title="导出到文件",
            initialdir=initial_dir,
            initialfile=default_name,
            defaultextension=".md",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not filepath:
            return

        self.config.config["last_export_path"] = str(Path(filepath).parent)
        self.config.save_config()

        self.lbl_status.config(text="正在导出文件...")

        def task():
            if not self.analyzer:
                return

            output = []
            output.append(f"# Project Context: {self.analyzer.root.name}")
            output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            output.append(f"Project Type: {self.analyzer.detected_type}")
            output.append(f"\n## 1. Directory Structure\n```plaintext")

            root_iid = self.tree.get_children("")[0]
            tree_lines = self._generate_tree_text(root_iid)
            output.extend(tree_lines)
            output.append("```\n")

            output.append("## 2. File Contents\n")

            for iid, node in self.tree_nodes.items():
                if not node['is_dir'] and node['state'] == STATE_CHECKED:
                    try:
                        rel_path = node['path'].relative_to(self.analyzer.root).as_posix()
                    except ValueError:
                        rel_path = node['path'].name

                    content = self._read_file_content(node['path'], node['skeleton'])
                    ext = node['path'].suffix[1:] if node['path'].suffix else 'txt'

                    output.append(f"### File: `{rel_path}`")
                    if node['skeleton']:
                        output.append("*(Skeleton mode - structure only)*")
                    output.append(f"```{ext}\n{content}\n```\n")

            final_text = "\n".join(output)

            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(final_text)

                tokens = CodeProcessor.estimate_tokens(final_text)

                self.root.after(0, lambda: messagebox.showinfo(
                    "成功",
                    f"已导出到:\n{filepath}\n\n预估消耗 {tokens:,} Tokens"
                ))
                self.root.after(0, lambda: self.lbl_status.config(text="导出完成"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"导出失败: {str(e)}"))
                self.root.after(0, lambda: self.lbl_status.config(text="导出失败"))

        threading.Thread(target=task, daemon=True).start()

    # ========================================================================
    # WINDOW MANAGEMENT
    # ========================================================================

    def _on_close(self):
        """Handle window close"""
        # Save window geometry
        self.config.config["window_geometry"] = self.root.geometry()
        self.config.config["auto_redact"] = self.var_redact.get()
        self.config.save_config()

        self.root.destroy()

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    # Enable DPI awareness on Windows
    try:
        from ctypes import windll  # type: ignore
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = tk.Tk()
    ProjectReaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
