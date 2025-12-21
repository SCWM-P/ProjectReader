"""
Project File Reader & Analyzer Tool
Version: 1.0.0
Author: Python Tooling Logic
Date: 2025-01-27
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
from datetime import datetime
from typing import List, Set, Dict, Optional, Any

# --- 配置管理器 (Configuration Manager) ---
class ConfigHandler:
    """
    负责处理配置文件的加载、保存和默认生成。
    为了保持零依赖，实现了一个简易的 YAML 子集解析器 (仅支持 Key-Value 和 String List)。
    """
    DEFAULT_CONFIG_NAME = "ProjectReader.yaml"
    
    DEFAULT_DATA = {
        "max_chars_python": 8000,
        "max_chars_code": 3000,
        "max_chars_text": 1500,
        "ignore_patterns": [
            ".git", "node_modules", "__pycache__", "venv", ".idea", ".vscode", "build", "dist",
            "*.pyc", "*.exe", "*.dll", "*.so", "*.dylib", "*.class", "*.jar",
            "*.jpg", "*.png", "*.gif", "*.mp4", "*.zip", "*.tar", "*.gz", "*.pdf", "*.db", "*.sqlite"
        ],
        "summary_patterns": [
            "*.log", "*.tmp", "migrations/*.py", "*.svg", "*.lock", "*.json", "*.xml"
        ]
    }

    @staticmethod
    def load_config(path: str = DEFAULT_CONFIG_NAME) -> Dict[str, Any]:
        """读取配置文件，如果失败则返回默认配置"""
        config = ConfigHandler.DEFAULT_DATA.copy()
        try:
            if not os.path.exists(path):
                return config
            
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            current_list_key = None
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if line.endswith(':'):
                    key = line[:-1].strip()
                    if key in config and isinstance(config[key], list):
                        config[key] = [] # 清空默认，使用文件中的列表
                        current_list_key = key
                    else:
                        current_list_key = None
                elif line.startswith('- ') and current_list_key:
                    value = line[2:].strip().strip("'").strip('"')
                    config[current_list_key].append(value)
                elif ':' in line:
                    parts = line.split(':', 1)
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key in config and isinstance(config[key], int):
                        try:
                            config[key] = int(value)
                        except ValueError:
                            pass
            return config
        except Exception as e:
            print(f"Config load error: {e}")
            return config

    @staticmethod
    def save_config(path: str, data: Dict[str, Any]):
        """保存配置到文件"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"# Project Reader Configuration - Generated at {datetime.now()}\n\n")
                
                # 写入数值设置
                for key in ["max_chars_python", "max_chars_code", "max_chars_text"]:
                    f.write(f"{key}: {data.get(key, 0)}\n")
                
                f.write("\n")
                
                # 写入列表设置
                for key in ["ignore_patterns", "summary_patterns"]:
                    f.write(f"{key}:\n")
                    for item in data.get(key, []):
                        f.write(f"  - {item}\n")
                    f.write("\n")
        except Exception as e:
            print(f"Config save error: {e}")

# --- 核心逻辑处理器 (Backend) ---
class ProjectProcessor:
    def __init__(self):
        self.config = ConfigHandler.DEFAULT_DATA.copy()
        self.root_dir = Path(".")
        
    def update_config(self, new_config: Dict[str, Any]):
        self.config = new_config

    def is_ignored(self, path: Path, root: Path) -> bool:
        import fnmatch
        rel_path = str(path.relative_to(root)).replace(os.sep, '/')
        name = path.name
        for pat in self.config["ignore_patterns"]:
            if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_path, pat):
                return True
        return False

    def is_summary_target(self, path: Path, root: Path) -> bool:
        import fnmatch
        rel_path = str(path.relative_to(root)).replace(os.sep, '/')
        name = path.name
        for pat in self.config["summary_patterns"]:
            if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_path, pat):
                return True
        return False

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def _human_size(self, size):
        for unit in ['B', 'KB', 'MB']:
            if size < 1024: return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"

    def generate_markdown(self, root_path: Path, selected_paths: Set[Path], summary_paths: Set[Path], progress_callback=None) -> str:
        output = []
        output.append(f"# 项目分析报告: {root_path.name}")
        output.append(f"根路径: `{root_path.resolve()}`")
        output.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("\n## 1. 目录结构")
        output.append("```plaintext")
        
        tree_lines = self._render_tree_text(root_path, root_path, selected_paths, summary_paths, "", True)
        output.extend(tree_lines)
        output.append("```")

        output.append("\n## 2. 文件内容")
        
        file_list = sorted([p for p in selected_paths if p.is_file()], key=lambda p: str(p))
        total_files = len(file_list)
        
        for idx, file_path in enumerate(file_list):
            if progress_callback:
                progress_callback(idx, total_files)
            
            # 检查是否处于摘要目录中
            parent = file_path.parent
            in_summary_mode = False
            while parent != root_path.parent:
                if parent in summary_paths:
                    in_summary_mode = True
                    break
                parent = parent.parent
            
            if in_summary_mode:
                continue

            try:
                rel_path = file_path.relative_to(root_path).as_posix()
            except ValueError:
                rel_path = file_path.name

            content_block = self._read_file_content(file_path)
            if content_block:
                output.append(f"\n### `{rel_path}`")
                output.append(content_block)
                output.append("---")

        return "\n".join(output)

    def _render_tree_text(self, current: Path, root: Path, selected: Set[Path], summary_nodes: Set[Path], prefix: str, is_last: bool) -> List[str]:
        if current != root and current not in selected:
            return []

        lines = []
        name = current.name
        connector = "└── " if is_last else "├── "
        
        info_suffix = ""
        is_summary = current in summary_nodes

        if current == root:
            lines.append(name + "/")
        else:
            if is_summary:
                if current.is_dir():
                    count = sum(1 for p in current.rglob('*') if p.is_file() and not self.is_ignored(p, root))
                    info_suffix = f" [摘要模式: 包含 {count} 个文件]"
                else:
                    info_suffix = " [摘要]"
            elif not current.is_dir():
                pass # 普通文件暂不显示后缀，保持简洁
            
            lines.append(f"{prefix}{connector}{name}{'/' if current.is_dir() else ''}{info_suffix}")

        if current != root and is_summary:
            return lines

        if current.is_dir():
            children = []
            try:
                for child in current.iterdir():
                    if child in selected:
                        children.append(child)
            except OSError:
                pass
            
            children.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            
            new_prefix = prefix + ("    " if is_last else "│   ")
            if current == root: new_prefix = ""

            for i, child in enumerate(children):
                lines.extend(self._render_tree_text(child, root, selected, summary_nodes, new_prefix, i == len(children) - 1))

        return lines

    def _read_file_content(self, path: Path) -> Optional[str]:
        ext = path.suffix.lower()
        limit = self.config['max_chars_text']
        if ext == '.py': limit = self.config['max_chars_python']
        elif ext in ['.js', '.java', '.cpp', '.h', '.ts', '.css', '.html', '.rs', '.go']: limit = self.config['max_chars_code']
        
        try:
            size = path.stat().st_size
            if size > 1024 * 1024: 
                return f"```\n(文件过大: {self._human_size(size)} - 内容已跳过)\n```"

            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            if len(content) > limit:
                content = content[:limit] + f"\n... (剩余 {len(content)-limit} 字符已截断)"
            
            # 修复 Markdown 转义
            import re
            max_ticks = max([len(m) for m in re.findall(r'`+', content)] or [0])
            fence = "`" * (max(3, max_ticks + 1))
            
            lang = ext[1:] if ext else ""
            return f"{fence}{lang}\n{content}\n{fence}"
        except Exception as e:
            return f"```\n(读取错误: {str(e)})\n```"

# --- GUI 界面类 (Frontend) ---
class ProjectReaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Project Reader v1.0.0")
        self.root.geometry("1100x750")
        
        self.processor = ProjectProcessor()
        
        # UI资源
        self.icon_checked = "☑"
        self.icon_unchecked = "☐"
        self.icon_folder = "📂"
        self.icon_file = "📄"
        self.icon_summary = "📦"
        
        # 数据状态
        self.tree_items = {}   # iid -> Path
        self.path_map = {}     # Path -> iid
        self.check_state = {}  # Path -> bool
        self.summary_state = {} # Path -> bool
        self.project_root = Path(".")
        
        # 初始化配置
        self._load_initial_config()
        self._build_ui()

    def _load_initial_config(self):
        # 尝试读取默认配置
        if os.path.exists(ConfigHandler.DEFAULT_CONFIG_NAME):
            cfg = ConfigHandler.load_config(ConfigHandler.DEFAULT_CONFIG_NAME)
            self.processor.update_config(cfg)
        else:
            # 不存在则提示创建
            if messagebox.askyesno("初始化", f"未找到配置文件，是否创建默认的 '{ConfigHandler.DEFAULT_CONFIG_NAME}'?"):
                ConfigHandler.save_config(ConfigHandler.DEFAULT_CONFIG_NAME, self.processor.config)

    def _build_ui(self):
        # 1. 顶部栏 (路径与操作)
        top_bar = ttk.Frame(self.root, padding=5)
        top_bar.pack(fill=tk.X)
        
        ttk.Label(top_bar, text="项目路径:").pack(side=tk.LEFT)
        self.entry_path = ttk.Entry(top_bar)
        self.entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(top_bar, text="选择...", command=self._browse_path).pack(side=tk.LEFT)
        ttk.Button(top_bar, text="加载配置...", command=self._load_custom_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_bar, text="开始扫描", command=self._start_scan).pack(side=tk.LEFT)

        # 2. 主体区 (左树右参)
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧容器
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=3)
        
        # 全路径面包屑 (Breadcrumb)
        self.lbl_breadcrumb = ttk.Label(left_frame, text="准备就绪", anchor="w", background="#e1e1e1", padding=2)
        self.lbl_breadcrumb.pack(fill=tk.X)

        # 树形视图
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(tree_frame, columns=("size", "status"), selectmode="browse")
        self.tree.heading("#0", text="文件目录结构", anchor="w")
        self.tree.heading("size", text="大小", anchor="e")
        self.tree.heading("status", text="状态", anchor="center")
        
        self.tree.column("#0", width=400)
        self.tree.column("size", width=80, anchor="e")
        self.tree.column("status", width=80, anchor="center")
        
        ysb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        xsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=ysb.set, xscroll=xsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # 绑定事件
        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-3>", self._show_context_menu)

        # 右侧容器
        right_frame = ttk.Frame(paned, padding=5)
        paned.add(right_frame, weight=1)
        
        self._build_settings_panel(right_frame)

        # 3. 底部栏 (进度与动作)
        bottom_bar = ttk.Frame(self.root, padding=5)
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.lbl_status = ttk.Label(bottom_bar, text="等待操作")
        self.lbl_status.pack(side=tk.LEFT)
        
        self.progress = ttk.Progressbar(bottom_bar, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        ttk.Button(bottom_bar, text="复制到剪贴板", command=self._copy_result).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_bar, text="导出文件", command=self._export_result).pack(side=tk.RIGHT)

        # 上下文菜单
        self.ctx_menu = tk.Menu(self.root, tearoff=0)
        self.ctx_menu.add_command(label="切换全文/摘要模式", command=self._toggle_summary_ctx)
        self.ctx_menu.add_command(label="添加至忽略列表", command=self._add_ignore_ctx)

    def _build_settings_panel(self, parent):
        # 限制设置
        lf_limits = ttk.Labelframe(parent, text="读取限制 (字符数)")
        lf_limits.pack(fill=tk.X, pady=5)
        
        self.vars_limits = {
            'max_chars_python': tk.IntVar(),
            'max_chars_code': tk.IntVar(),
            'max_chars_text': tk.IntVar()
        }
        
        order = [('max_chars_python', 'Python:'), ('max_chars_code', '代码:'), ('max_chars_text', '文本:')]
        for key, label in order:
            f = ttk.Frame(lf_limits)
            f.pack(fill=tk.X, padx=5, pady=2)
            ttk.Label(f, text=label).pack(side=tk.LEFT)
            ttk.Entry(f, textvariable=self.vars_limits[key], width=8).pack(side=tk.RIGHT)

        # 模式设置
        lf_pats = ttk.Labelframe(parent, text="过滤规则 (每行一条)")
        lf_pats.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(lf_pats, text="忽略模式:").pack(anchor="w")
        self.txt_ignore = tk.Text(lf_pats, height=8, width=20)
        self.txt_ignore.pack(fill=tk.X, padx=5)
        
        ttk.Label(lf_pats, text="摘要模式:").pack(anchor="w", pady=(5,0))
        self.txt_summary = tk.Text(lf_pats, height=8, width=20)
        self.txt_summary.pack(fill=tk.X, padx=5)
        
        ttk.Button(lf_pats, text="应用配置刷新", command=self._apply_config_and_rescan).pack(pady=5)
        
        self._sync_ui_from_config()

    def _sync_ui_from_config(self):
        cfg = self.processor.config
        for k in self.vars_limits:
            self.vars_limits[k].set(cfg.get(k, 0))
        
        self.txt_ignore.delete("1.0", tk.END)
        self.txt_ignore.insert("1.0", "\n".join(cfg.get("ignore_patterns", [])))
        
        self.txt_summary.delete("1.0", tk.END)
        self.txt_summary.insert("1.0", "\n".join(cfg.get("summary_patterns", [])))

    def _sync_config_from_ui(self):
        cfg = self.processor.config
        for k in self.vars_limits:
            cfg[k] = self.vars_limits[k].get()
        
        cfg["ignore_patterns"] = [line.strip() for line in self.txt_ignore.get("1.0", tk.END).splitlines() if line.strip()]
        cfg["summary_patterns"] = [line.strip() for line in self.txt_summary.get("1.0", tk.END).splitlines() if line.strip()]

    # --- 交互逻辑 ---
    
    def _browse_path(self):
        p = filedialog.askdirectory()
        if p:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, p)
            self._start_scan()

    def _load_custom_config(self):
        p = filedialog.askopenfilename(filetypes=[("YAML/Config", "*.yaml"), ("All Files", "*.*")])
        if p:
            cfg = ConfigHandler.load_config(p)
            self.processor.update_config(cfg)
            self._sync_ui_from_config()
            messagebox.showinfo("配置", f"已加载配置: {Path(p).name}")

    def _apply_config_and_rescan(self):
        self._sync_config_from_ui()
        if self.entry_path.get():
            self._start_scan()

    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if sel:
            path = self.tree_items.get(sel[0])
            if path:
                # 类似Excel冻结表头的效果：在顶部显示完整路径
                self.lbl_breadcrumb.config(text=f"当前位置: {path.absolute()}")

    def _on_tree_click(self, event):
        """核心交互：区分折叠操作与选中操作"""
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        
        # 识别点击的元素部分 (text, image, symbol, etc.)
        element = self.tree.identify_element(event.x, event.y)
        
        # 调试: print(element) -> 通常 'text', 'image', 'indicator'
        # 如果点击的是 'indicator' (折叠箭头)，由Tkinter默认处理
        # 如果点击的是 'text' 或 'image' (我们的自定义图标)，则处理复选框
        
        if element in ['text', 'image']:
            path = self.tree_items.get(item_id)
            if path:
                self._toggle_check(path)
                return "break"

    def _show_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            self.ctx_menu.post(event.x_root, event.y_root)

    def _toggle_summary_ctx(self):
        sel = self.tree.selection()
        if sel:
            path = self.tree_items[sel[0]]
            current = self.summary_state.get(path, False)
            self.summary_state[path] = not current
            self._refresh_node(path)

    def _add_ignore_ctx(self):
        sel = self.tree.selection()
        if sel:
            path = self.tree_items[sel[0]]
            self.txt_ignore.insert(tk.END, f"\n{path.name}")
            if messagebox.askyesno("规则更新", "已添加忽略规则，是否立即刷新？"):
                self._apply_config_and_rescan()

    def _toggle_check(self, path: Path):
        new_state = not self.check_state.get(path, True)
        self.check_state[path] = new_state
        
        # 向下递归更新子节点
        def cascade_update(p):
            # 更新数据状态
            self.check_state[p] = new_state
            # 如果该节点在树中可见，刷新显示
            if p in self.path_map:
                self._refresh_node(p)
            
            # 只有当它是目录且当前已展开(或存在于path_map中)时，才尝试递归子项
            # 注意：未展开的节点可能不在 path_map 中（取决于是否懒加载），此处假设全量加载
            node_id = self.path_map.get(p)
            if node_id:
                children_ids = self.tree.get_children(node_id)
                for cid in children_ids:
                    child_path = self.tree_items[cid]
                    cascade_update(child_path)

        cascade_update(path)

    def _refresh_node(self, path: Path):
        iid = self.path_map.get(path)
        if not iid: return
        
        is_checked = self.check_state.get(path, True)
        is_summary = self.summary_state.get(path, False)
        is_dir = path.is_dir()
        
        check_mark = self.icon_checked if is_checked else self.icon_unchecked
        type_mark = self.icon_summary if is_summary else (self.icon_folder if is_dir else self.icon_file)
        
        display_text = f"{check_mark}  {type_mark}  {path.name}"
        status_text = "摘要" if is_summary else ""
        
        # 保留原有的 values (size)，只更新 text 和 status
        current_vals = self.tree.item(iid, "values")
        size_val = current_vals[0] if current_vals else ""
        
        self.tree.item(iid, text=display_text, values=(size_val, status_text))

    # --- 扫描与生成逻辑 ---

    def _start_scan(self):
        path_str = self.entry_path.get()
        if not os.path.isdir(path_str):
            return
        
        self.project_root = Path(path_str).resolve()
        self._sync_config_from_ui()
        
        # UI 重置
        self.tree.delete(*self.tree.get_children())
        self.tree_items.clear()
        self.path_map.clear()
        self.check_state.clear()
        self.summary_state.clear()
        self.progress.config(mode='indeterminate')
        self.progress.start(10)
        self.lbl_status.config(text="正在分析文件结构...")
        
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        # 缓冲区
        buffer_nodes = []
        
        def recursive_scan(current_path):
            if self.processor.is_ignored(current_path, self.project_root):
                return
            
            # 自动判断摘要模式
            if self.processor.is_summary_target(current_path, self.project_root):
                self.summary_state[current_path] = True
            
            self.check_state[current_path] = True
            
            node_data = {
                'path': current_path,
                'is_dir': current_path.is_dir(),
                'size': current_path.stat().st_size if not current_path.is_dir() else 0,
                'parent': current_path.parent
            }
            buffer_nodes.append(node_data)
            
            if current_path.is_dir():
                try:
                    # 排序：文件夹在前，文件在后，字母顺序
                    for child in sorted(current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                        recursive_scan(child)
                except OSError:
                    pass

        try:
            recursive_scan(self.project_root)
            self.root.after(0, lambda: self._populate_tree(buffer_nodes))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("扫描错误", str(e)))

    def _populate_tree(self, nodes):
        self.progress.stop()
        self.progress.config(mode='determinate', value=0)
        
        # 建立父子索引
        nodes_map = {} # path -> node_data
        children_map = {} # path -> [child_nodes]
        
        root_path_str = str(self.project_root)
        
        for n in nodes:
            nodes_map[n['path']] = n
            parent_path = n['parent']
            if parent_path not in children_map: children_map[parent_path] = []
            children_map[parent_path].append(n)

        def insert_recursive(parent_path, parent_iid):
            if parent_path not in children_map: return
            
            for item in children_map[parent_path]:
                path = item['path']
                
                # 只有当该路径是根路径的子集，或者就是根路径时才显示
                # 这里的逻辑通过 recursive_scan 保证了，只需要处理根节点特殊情况
                pass

                is_dir = item['is_dir']
                size_str = self.processor._human_size(item['size']) if not is_dir else ""
                
                # 初始渲染
                iid = self.tree.insert(parent_iid, 'end', text="", values=(size_str, ""), open=(path==self.project_root))
                
                self.tree_items[iid] = path
                self.path_map[path] = iid
                
                # 刷新一次显示文本（带图标）
                self._refresh_node(path)
                
                if is_dir:
                    insert_recursive(path, iid)

        # 启动插入：从根目录的父级开始找，或者直接插入根目录
        # 为了展示根目录本身，我们需要手动插入根节点，然后递归其子节点
        if self.project_root in nodes_map:
            root_item = nodes_map[self.project_root]
            root_iid = self.tree.insert("", 'end', text="", open=True)
            self.tree_items[root_iid] = self.project_root
            self.path_map[self.project_root] = root_iid
            self._refresh_node(self.project_root)
            insert_recursive(self.project_root, root_iid)
        
        self.lbl_status.config(text=f"就绪。共发现 {len(nodes)} 个对象。")

    # --- 导出 ---
    def _collect_selections(self):
        sel = {p for p, s in self.check_state.items() if s}
        summ = {p for p, s in self.summary_state.items() if s}
        return sel, summ

    def _copy_result(self):
        if not self.tree_items: return
        self.lbl_status.config(text="正在生成 Markdown...")
        
        def task():
            sel, summ = self._collect_selections()
            text = self.processor.generate_markdown(self.project_root, sel, summ)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            
            tokens = self.processor.estimate_tokens(text)
            msg = f"已复制! 长度: {len(text)} 字符, 约 {tokens} Tokens"
            self.root.after(0, lambda: self.lbl_status.config(text=msg))
            self.root.after(0, lambda: messagebox.showinfo("完成", msg))
            
        threading.Thread(target=task, daemon=True).start()

    def _export_result(self):
        if not self.tree_items: return
        target = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md")])
        if not target: return
        
        def task():
            sel, summ = self._collect_selections()
            
            def cb(curr, total):
                if total: self.progress['value'] = (curr/total)*100
                
            text = self.processor.generate_markdown(self.project_root, sel, summ, cb)
            with open(target, 'w', encoding='utf-8') as f:
                f.write(text)
            self.root.after(0, lambda: messagebox.showinfo("导出成功", f"文件已保存: {target}"))
            
        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    # DPI适配
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    root = tk.Tk()
    app = ProjectReaderApp(root)
    root.mainloop()