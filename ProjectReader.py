"""
LLM Context Builder (Super Project Reader)
Version: 2.0.0
Description: Zero-dependency, intelligent codebase packer for Large Language Models.
"""

import os
import re
import fnmatch
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import defaultdict
from typing import Optional, List, Dict, Tuple

# --- 常量与配置字典 ---
FILE_ICONS = {
    '.py': '🐍', '.js': '🟨', '.ts': '🟦', '.java': '☕', 
    '.cpp': '⚙', '.c': '⚙', '.h': '📄', '.cs': '💠',
    '.html': '🌐', '.css': '🎨', '.md': '📝', '.json': '🔧',
    '.yaml': '🔧', '.yml': '🔧', '.xml': '📋', '.sh': '🐧',
    '.rs': '🦀', '.go': '🐹', '.sql': '💾', '.txt': '📄'
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
        "ignore": ["__pycache__", "*.pyc", "venv", ".env", ".pytest_cache", ".tox", "build", "dist", "*.egg-info"]
    },
    "Node.js / Web": {
        "detect": ["package.json", "yarn.lock"],
        "ignore": ["node_modules", "dist", ".next", "out", ".nuxt", ".env", "build", ".cache"]
    },
    "Java": {
        "detect": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "ignore": ["target", "build", ".idea", "*.class", "*.jar"]
    },
    "Rust": {
        "detect": ["Cargo.toml"],
        "ignore": ["target", "Cargo.lock"]
    },
    "Default / Generic": {
        "detect": [],
        "ignore": [".git", ".svn", ".idea", ".vscode", "*.exe", "*.dll", "*.so", "*.dylib", "*.jpg", "*.png", "*.gif", "*.mp4", "*.zip", "*.tar.gz", "*.pdf", "*.sqlite", "*.db"]
    }
}

# --- 核心逻辑引擎 ---
class CodeProcessor:
    SECRET_PATTERN = re.compile(
        r'(?i)(api_key|apikey|secret|password|passwd|token)\s*[:=]\s*(["\'])[a-zA-Z0-9\-_]{10,}\2'
    )

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return len(text) // 4

    @staticmethod
    def redact_secrets(text: str) -> str:
        return CodeProcessor.SECRET_PATTERN.sub(r'\1 = "[REDACTED_SECRET]"', text)

    @staticmethod
    def extract_skeleton(text: str, ext: str) -> str:
        lines = text.splitlines()
        skeleton = []
        py_pat = re.compile(r'^\s*(def |class |async def )')
        c_pat = re.compile(r'^\s*(export |public |private |protected |)?(class |interface |function |struct |enum )\s*[a-zA-Z0-9_]+')
        in_docstring = False
        
        for line in lines:
            stripped = line.strip()
            if ext == '.py':
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    in_docstring = not in_docstring
                    skeleton.append(line)
                    continue
                if in_docstring:
                    skeleton.append(line)
                    continue
                if py_pat.match(line):
                    skeleton.append(line + " ...")
            else:
                if c_pat.match(line):
                    skeleton.append(line + (" { ... }" if not stripped.endswith(';') else ""))
                    
        if not skeleton:
            return "(No structural skeleton found, or file is too generic. Try full context.)"
        return "\n".join(skeleton)

class ProjectAnalyzer:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.whitelist: List[str] = []
        self.blacklist: List[str] = []
        self.gitignore_rules: List[str] = []
        self.detected_type = "Default / Generic"
        
        self.file_stats: Dict[str, int] = defaultdict(int)
        self.top_files: List[Tuple[int, Path]] = []
        
    def auto_detect(self):
        for ptype, preset in PROJECT_PRESETS.items():
            if any((self.root / f).exists() for f in preset["detect"]):
                self.detected_type = ptype
                self.blacklist.extend(preset["ignore"])
                break
        
        self.blacklist.extend(PROJECT_PRESETS["Default / Generic"]["ignore"])
        
        gitignore_path = self.root / ".gitignore"
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if line.endswith('/'): line = line[:-1]
                            self.gitignore_rules.append(line)
            except Exception:
                pass
                
        self.blacklist = list(set(self.blacklist))

    def _match_pattern(self, rel_path_str: str, name: str, patterns: List[str]) -> bool:
        rel_path_str = rel_path_str.replace(os.sep, '/')
        for pat in patterns:
            if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_path_str, pat):
                return True
            if '/' in pat and fnmatch.fnmatch(rel_path_str, pat.lstrip('/')):
                return True
        return False

    def is_ignored(self, path: Path) -> bool:
        """核心过滤逻辑：支持白名单排他与黑名单穿透"""
        try:
            rel_str = str(path.relative_to(self.root)).replace(os.sep, '/')
        except ValueError:
            return True
            
        name = path.name
        
        is_white = self._match_pattern(rel_str, name, self.whitelist) if self.whitelist else False
        is_black = self._match_pattern(rel_str, name, self.blacklist) or \
                   self._match_pattern(rel_str, name, self.gitignore_rules)
        
        # 1. 明确命明白名单的，无视黑名单，绝对放行
        if is_white:
            return False
            
        # 2. 如果被黑名单命中
        if is_black:
            # 特殊情况：如果是目录且存在白名单，检查是否需要"刺透"黑名单寻找里面的白名单文件
            if path.is_dir() and self.whitelist:
                for w in self.whitelist:
                    if '*' in w or w.startswith(rel_str + '/'):
                        return False # 刺透放行，继续遍历里面
            return True # 黑名单生效，忽略
            
        # 3. 既无白命中，也无黑命中
        # 如果用户填写了白名单，意味着开启了"排他模式" (仅收录白名单项目)
        if self.whitelist and path.is_file():
            return True
            
        return False

# --- GUI 界面 (View & Controller) ---
class AppGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LLM Context Builder v2.0")
        self.root.geometry("1400x850")
        
        style = ttk.Style()
        try: style.theme_use('clam')
        except tk.TclError: pass
        style.configure("Treeview", rowheight=24, font=('Consolas', 10))
        
        self.analyzer: Optional[ProjectAnalyzer] = None
        self.tree_nodes: Dict[str, dict] = {}  
        self.path_to_iid: Dict[Path, str] = {} 
        
        self._build_ui()

    def _build_ui(self):
        # 1. 顶部栏
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="📦 项目路径:", font=('', 10, 'bold')).pack(side=tk.LEFT)
        self.entry_path = ttk.Entry(top_frame, font=('Consolas', 10))
        self.entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        ttk.Button(top_frame, text="浏览...", command=self._browse_dir).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="🚀 扫描分析", command=self._start_scan).pack(side=tk.LEFT, padx=5)

        # 2. 主体三栏
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # ---------------- 左栏：目录树 ----------------
        left_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, weight=1)
        
        tree_header = ttk.Frame(left_frame)
        tree_header.pack(fill=tk.X)
        ttk.Label(tree_header, text="文件结构 (双击或点选框更改)", font=('', 9, 'bold')).pack(side=tk.LEFT, pady=2)
        ttk.Button(tree_header, text="全选/反选", command=self._toggle_all).pack(side=tk.RIGHT)

        self.tree = ttk.Treeview(left_frame, columns=("size"), selectmode="browse")
        self.tree.heading("#0", text=" 名称", anchor="w")
        self.tree.heading("size", text="大小", anchor="e")
        self.tree.column("#0", width=300)
        self.tree.column("size", width=80, anchor="e")
        
        self.tree.tag_configure('ignored', foreground='#a0a0a0')
        self.tree.tag_configure('skeleton', foreground='#0055ff')
        
        ysb = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)       # 单击检测图标位
        self.tree.bind("<Double-1>", self._on_tree_double_click)       # 双击切换状态
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)     # 单击仅选定预览
        self.tree.bind("<Button-3>", self._show_context_menu)          # 右键菜单
        
        # ---------------- 中栏：预览区 (使用 Grid 修复滚动条错位) ----------------
        mid_frame = ttk.Frame(self.paned)
        self.paned.add(mid_frame, weight=2)
        
        mid_frame.rowconfigure(1, weight=1)
        mid_frame.columnconfigure(0, weight=1)
        
        self.lbl_preview = ttk.Label(mid_frame, text="实时预览: (未选择)", font=('', 9, 'bold'))
        self.lbl_preview.grid(row=0, column=0, columnspan=2, sticky="ew", pady=2)
        
        self.txt_preview = tk.Text(mid_frame, wrap=tk.NONE, font=('Consolas', 10), bg='#1e1e1e', fg='#d4d4d4')
        p_ysb = ttk.Scrollbar(mid_frame, orient=tk.VERTICAL, command=self.txt_preview.yview)
        p_xsb = ttk.Scrollbar(mid_frame, orient=tk.HORIZONTAL, command=self.txt_preview.xview)
        self.txt_preview.configure(yscrollcommand=p_ysb.set, xscrollcommand=p_xsb.set)
        
        self.txt_preview.grid(row=1, column=0, sticky="nsew")
        p_ysb.grid(row=1, column=1, sticky="ns")
        p_xsb.grid(row=2, column=0, sticky="ew")

        # ---------------- 右栏：控制台 ----------------
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=1)
        
        info_lf = ttk.LabelFrame(right_frame, text="🤖 项目情报")
        info_lf.pack(fill=tk.X, pady=5)
        self.lbl_proj_type = ttk.Label(info_lf, text="类型: 等待分析...", foreground="blue")
        self.lbl_proj_type.pack(anchor="w", padx=5, pady=2)
        
        radar_lf = ttk.LabelFrame(right_frame, text="⚠️ 巨型文件雷达 (Top 5)")
        radar_lf.pack(fill=tk.X, pady=5)
        self.txt_radar = tk.Text(radar_lf, height=6, font=('Consolas', 9), state=tk.DISABLED, bg='#f9f9f9')
        self.txt_radar.pack(fill=tk.BOTH, padx=5, pady=5)
        
        self.var_redact = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_frame, text="🛡️ 自动脱敏密码/Key", variable=self.var_redact).pack(anchor="w", pady=2)
        
        # 过滤器 (支持上下调节比例)
        filter_paned = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        filter_paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        white_lf = ttk.LabelFrame(filter_paned, text="✅ 白名单 (回车分隔, 穿透生效)")
        self.txt_white = tk.Text(white_lf, height=4, font=('Consolas', 9))
        self.txt_white.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        filter_paned.add(white_lf, weight=1)
        
        black_lf = ttk.LabelFrame(filter_paned, text="🚫 黑名单 (回车分隔)")
        self.txt_black = tk.Text(black_lf, height=6, font=('Consolas', 9))
        self.txt_black.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        filter_paned.add(black_lf, weight=1)

        # 3. 底部栏
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.pack(fill=tk.X)
        
        self.lbl_status = ttk.Label(bottom_frame, text="就绪", font=('', 10))
        self.lbl_status.pack(side=tk.LEFT)
        
        self.lbl_tokens = ttk.Label(bottom_frame, text="预估 Tokens: 0 🟢", font=('', 10, 'bold'))
        self.lbl_tokens.pack(side=tk.LEFT, padx=20)
        
        ttk.Button(bottom_frame, text="📋 仅复制结构", command=lambda: self._export(structure_only=True)).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="📝 复制给 LLM (完整)", command=self._export).pack(side=tk.RIGHT, padx=5)
        
        self.ctx_menu = tk.Menu(self.root, tearoff=0)
        self.ctx_menu.add_command(label="🔄 切换 完整 / 骨架提取模式", command=self._ctx_toggle_skeleton)
        self.ctx_menu.add_command(label="✅ 将此文件加入白名单", command=self._ctx_add_whitelist)
        self.ctx_menu.add_command(label="🚫 将此文件加入黑名单", command=self._ctx_add_blacklist)

    # --- 交互与事件逻辑 ---
    def _browse_dir(self):
        p = filedialog.askdirectory()
        if p:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, p)
            self._start_scan()

    def _start_scan(self):
        path_str = self.entry_path.get().strip()
        if not os.path.isdir(path_str):
            messagebox.showwarning("错误", "请提供有效的项目文件夹路径！")
            return
            
        self.analyzer = ProjectAnalyzer(Path(path_str))
        self.analyzer.auto_detect()
        
        white_add = self.txt_white.get("1.0", tk.END).strip().splitlines()
        if white_add:
            self.analyzer.whitelist = [w.strip() for w in white_add if w.strip()]
        
        black_add = self.txt_black.get("1.0", tk.END).strip().splitlines()
        self.analyzer.blacklist.extend([b.strip() for b in black_add if b.strip()])
        
        self.lbl_proj_type.config(text=f"类型: {self.analyzer.detected_type}")
        self.lbl_status.config(text="扫描中，请稍候...")
        
        self.tree.delete(*self.tree.get_children())
        self.tree_nodes.clear()
        self.path_to_iid.clear()
        
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        if not self.analyzer: return 
        nodes = []
        root_path = self.analyzer.root
        
        def walk_dir(current: Path):
            if not self.analyzer: return
            if self.analyzer.is_ignored(current): return
                
            is_dir = current.is_dir()
            size = current.stat().st_size if not is_dir else 0
            
            if not is_dir:
                self.analyzer.file_stats[current.suffix.lower()] += size
                self.analyzer.top_files.append((size, current))
                
            nodes.append({
                'path': current, 'is_dir': is_dir, 'size': size, 'parent': current.parent
            })
            
            if is_dir:
                try:
                    children = sorted(current.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                    for child in children:
                        walk_dir(child)
                except Exception: pass

        walk_dir(root_path)
        self.analyzer.top_files.sort(key=lambda x: x[0], reverse=True)
        self.root.after(0, lambda: self._build_tree(nodes))

    def _human_size(self, size: float) -> str:
        for unit in ['B', 'KB', 'MB']:
            if size < 1024: return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}GB"

    def _build_tree(self, nodes):
        if not self.analyzer: return
        children_map = defaultdict(list)
        for n in nodes: children_map[n['parent']].append(n)
            
        def insert_node(node_data, parent_iid):
            p = node_data['path']
            is_dir = node_data['is_dir']
            icon = FOLDER_ICON if is_dir else FILE_ICONS.get(p.suffix.lower(), DEFAULT_ICON)
            size_str = self._human_size(node_data['size']) if not is_dir else ""
            text = f"{ICONS_STATE[STATE_CHECKED]} {icon} {p.name}"
            
            iid = self.tree.insert(parent_iid, 'end', text=text, values=(size_str,), open=True)
            self.tree_nodes[iid] = {
                'path': p, 'state': STATE_CHECKED, 'is_dir': is_dir, 
                'size': node_data['size'], 'skeleton': False
            }
            self.path_to_iid[p] = iid
            
            if is_dir and p in children_map:
                for child in children_map[p]: insert_node(child, iid)

        root_node = {'path': self.analyzer.root, 'is_dir': True, 'size': 0, 'parent': None}
        insert_node(root_node, "")
        
        self._update_radar()
        self._recalculate_ui()
        self.lbl_status.config(text=f"就绪。共加载 {len(self.tree_nodes)} 个项目节点。")

    def _update_radar(self):
        if not self.analyzer: return
        self.txt_radar.config(state=tk.NORMAL)
        self.txt_radar.delete("1.0", tk.END)
        for i, (size, p) in enumerate(self.analyzer.top_files[:5]):
            rel = p.relative_to(self.analyzer.root)
            self.txt_radar.insert(tk.END, f"{i+1}. {rel} ({self._human_size(size)})\n")
        self.txt_radar.config(state=tk.DISABLED)

    def _refresh_node_ui(self, iid: str):
        node = self.tree_nodes[iid]
        p = node['path']
        state = node['state']
        is_dir = node['is_dir']
        skeleton = node['skeleton']
        
        icon = FOLDER_ICON if is_dir else FILE_ICONS.get(p.suffix.lower(), DEFAULT_ICON)
        base_text = f"{ICONS_STATE[state]} {icon} {p.name}"
        
        if skeleton and not is_dir:
            self.tree.item(iid, text=base_text + " [骨架]", tags=('skeleton',))
        elif state == STATE_UNCHECKED:
            self.tree.item(iid, text=base_text, tags=('ignored',))
        else:
            self.tree.item(iid, text=base_text, tags=())

    def _toggle_node_state(self, iid: str):
        current_state = self.tree_nodes[iid]['state']
        new_state = STATE_UNCHECKED if current_state in [STATE_CHECKED, STATE_PARTIAL] else STATE_CHECKED
        
        def cascade_down(target_iid, st):
            self.tree_nodes[target_iid]['state'] = st
            self._refresh_node_ui(target_iid)
            for child in self.tree.get_children(target_iid): cascade_down(child, st)
        cascade_down(iid, new_state)
        
        def cascade_up(target_iid):
            parent = self.tree.parent(target_iid)
            if not parent: return
            siblings = self.tree.get_children(parent)
            states = set(self.tree_nodes[s]['state'] for s in siblings)
            
            if len(states) == 1 and STATE_CHECKED in states: p_state = STATE_CHECKED
            elif len(states) == 1 and STATE_UNCHECKED in states: p_state = STATE_UNCHECKED
            else: p_state = STATE_PARTIAL
                
            self.tree_nodes[parent]['state'] = p_state
            self._refresh_node_ui(parent)
            cascade_up(parent)

        cascade_up(iid)
        self._recalculate_ui()

    def _on_tree_click(self, event):
        """处理单击事件：只有精确点击复选框位才切换状态"""
        iid = self.tree.identify_row(event.y)
        if not iid: return
        bbox = self.tree.bbox(iid, "#0")
        if bbox:
            x, y, w, h = bbox
            # X 坐标落在文本框的前 25 像素内 (大致为复选框的区域)
            if x <= event.x <= x + 25:
                self._toggle_node_state(iid)
                return "break" # 阻止默认的选择事件

    def _on_tree_double_click(self, event):
        """双击整行切换状态"""
        iid = self.tree.identify_row(event.y)
        if iid:
            self._toggle_node_state(iid)
            return "break"

    def _toggle_all(self):
        root_children = self.tree.get_children("")
        if not root_children: return
        self._toggle_node_state(root_children[0])

    def _show_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self.ctx_menu.post(event.x_root, event.y_root)

    def _ctx_toggle_skeleton(self):
        sel = self.tree.selection()
        if sel:
            iid = sel[0]
            node = self.tree_nodes[iid]
            if not node['is_dir']:
                node['skeleton'] = not node['skeleton']
                self._refresh_node_ui(iid)
                self._on_tree_select(None)
                self._recalculate_ui()
                
    def _ctx_add_whitelist(self):
        if not self.analyzer: return
        sel = self.tree.selection()
        if sel:
            p = self.tree_nodes[sel[0]]['path']
            try: rel = p.relative_to(self.analyzer.root).as_posix()
            except: rel = p.name
            self.txt_white.insert(tk.END, f"\n{rel}")
            if messagebox.askyesno("提示", "已添加到白名单。是否立即重新扫描？"):
                self._start_scan()

    def _ctx_add_blacklist(self):
        if not self.analyzer: return
        sel = self.tree.selection()
        if sel:
            p = self.tree_nodes[sel[0]]['path']
            try: rel = p.relative_to(self.analyzer.root).as_posix()
            except: rel = p.name
            self.txt_black.insert(tk.END, f"\n{rel}")
            if messagebox.askyesno("提示", "已添加到黑名单。是否立即重新扫描？"):
                self._start_scan()

    def _read_file_content(self, path: Path, skeleton: bool) -> str:
        try:
            if path.stat().st_size > 1024 * 500 and not skeleton:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    preview = f.read(5000)
                return f"// 文件过大 ({self._human_size(path.stat().st_size)})，已自动截断...\n{preview}\n// ... [截断]"
                       
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            if self.var_redact.get(): content = CodeProcessor.redact_secrets(content)
            if skeleton: content = CodeProcessor.extract_skeleton(content, path.suffix.lower())
            return content
        except Exception as e:
            return f"无法读取文件: {str(e)}"

    def _on_tree_select(self, event):
        """处理树节点选择：用于展示预览"""
        sel = self.tree.selection()
        if not sel: return
        
        iid = sel[0]
        node = self.tree_nodes[iid]
        
        self.txt_preview.config(state=tk.NORMAL)
        self.txt_preview.delete("1.0", tk.END)
        
        if node['is_dir']:
            self.lbl_preview.config(text=f"📂 目录: {node['path'].name}")
            self.txt_preview.insert(tk.END, "请选择具体文件查看内容。")
        else:
            self.lbl_preview.config(text=f"📄 预览: {node['path'].name}")
            content = self._read_file_content(node['path'], node['skeleton'])
            lines = content.splitlines()
            self.txt_preview.insert(tk.END, "\n".join(lines[:1000]))
            if len(lines) > 1000:
                self.txt_preview.insert(tk.END, "\n\n... (预览已截断，导出时包含完整设定内容) ...")
                
        self.txt_preview.config(state=tk.DISABLED)

    def _recalculate_ui(self):
        def task():
            total_chars = 0
            for iid, node in self.tree_nodes.items():
                if node['state'] in [STATE_CHECKED, STATE_PARTIAL] and not node['is_dir']:
                    size = node['size']
                    if node['skeleton']: size = size // 5
                    total_chars += size
            tokens = CodeProcessor.estimate_tokens(total_chars * 'a')
            color = "🟢" if tokens < 30000 else "🟡" if tokens < 80000 else "🔴"
            self.root.after(0, lambda: self.lbl_tokens.config(text=f"预估 Tokens: {tokens:,} {color}"))
        threading.Thread(target=task, daemon=True).start()

    def _generate_tree_text(self, iid: str, prefix: str = "", is_last: bool = True) -> List[str]:
        if not self.analyzer: return []
        node = self.tree_nodes[iid]
        if node['state'] == STATE_UNCHECKED: return []
        
        lines = []
        connector = "└── " if is_last else "├── "
        name = node['path'].name + ("/" if node['is_dir'] else "")
        if iid == self.path_to_iid.get(self.analyzer.root): lines.append(name)
        else: lines.append(f"{prefix}{connector}{name}")
            
        if node['is_dir']:
            children = [c for c in self.tree.get_children(iid) if self.tree_nodes[c]['state'] != STATE_UNCHECKED]
            new_prefix = prefix + ("    " if is_last else "│   ")
            if iid == self.path_to_iid.get(self.analyzer.root): new_prefix = ""
            for i, c in enumerate(children):
                lines.extend(self._generate_tree_text(c, new_prefix, i == len(children)-1))
        return lines

    def _export(self, structure_only: bool = False):
        if not self.tree_nodes or not self.analyzer: return
        self.lbl_status.config(text="正在生成构建...")
        
        def task():
            if not self.analyzer: return
            output = []
            output.append(f"# Project Context: {self.analyzer.root.name}")
            output.append("## 1. Directory Structure")
            output.append("```plaintext")
            
            root_iid = self.tree.get_children("")[0]
            tree_lines = self._generate_tree_text(root_iid)
            output.extend(tree_lines)
            output.append("```\n")
            
            if not structure_only:
                output.append("## 2. File Contents\n")
                for iid, node in self.tree_nodes.items():
                    if not node['is_dir'] and node['state'] in [STATE_CHECKED]:
                        try: rel_path = node['path'].relative_to(self.analyzer.root).as_posix()
                        except ValueError: rel_path = node['path'].name
                        content = self._read_file_content(node['path'], node['skeleton'])
                        ext = node['path'].suffix[1:] if node['path'].suffix else ''
                        output.append(f"### File: `{rel_path}`\n```{ext}\n{content}\n```\n")
            
            final_text = "\n".join(output)
            self.root.clipboard_clear()
            self.root.clipboard_append(final_text)
            tokens = CodeProcessor.estimate_tokens(final_text)
            self.root.after(0, lambda: messagebox.showinfo("成功", f"内容已复制到剪贴板！\n预估消耗 {tokens:,} Tokens。"))
            self.root.after(0, lambda: self.lbl_status.config(text="复制完成。"))

        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    try:
        from ctypes import windll # type: ignore
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception: pass
    app = AppGUI(tk.Tk())
    app.root.mainloop()