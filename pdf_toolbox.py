#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF工具箱 - 基于qpdf（Material Design风格）
功能：合并PDF、页面旋转、提取页面、删除页面、解密PDF、加密PDF、
     移除限制、查看信息、PDF概要、页面大小、附件管理、修复PDF
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets.scrolled import ScrolledText
from ttkbootstrap.dialogs import Messagebox
from tkinter import filedialog
import tkinter as tk
import tkinter.font as tkfont
import subprocess
import os
import sys
import json
import shutil

# 默认 qpdf 路径（会被 get_qpdf_path 自动搜索覆盖）
QPDF_PATH = ""

# 配置持久化目录
if sys.platform == 'win32':
    _CONFIG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'PDF工具箱')
elif sys.platform == 'darwin':
    _CONFIG_DIR = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'PDF工具箱')
else:
    _CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.config', 'PDF工具箱')
_CONFIG_FILE = os.path.join(_CONFIG_DIR, 'config.json')

# 平台相关常量
if sys.platform == 'win32':
    UI_FONT = 'Microsoft YaHei UI'
    UI_FONT_FIXED = 'Segoe UI'
    QPDF_EXE = 'qpdf.exe'
    _NO_WINDOW = subprocess.CREATE_NO_WINDOW
elif sys.platform == 'darwin':
    UI_FONT = 'PingFang SC'
    UI_FONT_FIXED = 'Helvetica Neue'
    QPDF_EXE = 'qpdf'
    _NO_WINDOW = 0
else:
    UI_FONT = 'Noto Sans CJK SC'
    UI_FONT_FIXED = 'Monospace'
    QPDF_EXE = 'qpdf'
    _NO_WINDOW = 0

# 导航项定义: (key, label, icon_color, icon_bg, group)
# icon_color: 图形颜色; icon_bg: 圆角矩形浅底色
NAV_ITEMS = [
    ("merge",    "合并PDF",   "#1A73E8", "#D2E3FC", "页面操作"),
    ("rotate",   "页面旋转",  "#137333", "#CEEAD6", "页面操作"),
    ("split",    "提取页面",  "#B06000", "#FEF7D0", "页面操作"),
    ("delete",   "删除页面",  "#C5221F", "#FCE8E6", "页面操作"),
    ("pagesize", "页面大小",  "#1A73E8", "#D2E3FC", "页面操作"),
    ("decrypt",  "解密PDF",   "#137333", "#CEEAD6", "安全"),
    ("encrypt",  "加密PDF",   "#1A73E8", "#D2E3FC", "安全"),
    ("restrict", "移除限制",  "#B06000", "#FEF7D0", "安全"),
    ("info",     "查看信息",  "#1A73E8", "#D2E3FC", "查看"),
    ("summary",  "PDF概要",   "#137333", "#CEEAD6", "查看"),
    ("attach",   "附件管理",  "#B06000", "#FEF7D0", "查看"),
    ("repair",   "修复PDF",   "#C5221F", "#FCE8E6", "查看"),
    ("print",     "批量打印",  "#1A73E8", "#D2E3FC", "工具"),
]

# 颜色方案
NAV_BG = '#FFFFFF'          # 导航栏背景：纯白
NAV_BG_HOVER = '#F0F6FF'    # 悬停：浅蓝
NAV_BG_ACTIVE = '#E8F0FE'   # 选中：淡蓝
NAV_FG = '#444444'          # 默认文字颜色
NAV_FG_ACTIVE = '#1A73E8'   # 选中文字颜色：Google蓝
TITLE_BG = '#FFFFFF'        # 标题栏背景
ACCENT_COLOR = '#1A73E8'    # 主题强调色

def _search_qpdf():
    """搜索系统中可用的 qpdf"""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    search_paths = [
        # === 打包后的捆绑目录 ===
        lambda: os.path.join(os.path.dirname(sys.executable), 'qpdf', QPDF_EXE) if getattr(sys, 'frozen', False) else None,
        lambda: os.path.join(os.path.dirname(sys.executable), '_internal', 'qpdf', QPDF_EXE) if getattr(sys, 'frozen', False) else None,
        lambda: os.path.join(sys._MEIPASS, 'qpdf', QPDF_EXE) if hasattr(sys, '_MEIPASS') else None,
    ]

    # === 脚本附近目录（开发/构建时使用）===
    for dir_name in [f'qpdf-12.3.2-msvc64', f'qpdf-12.3.2-linux-x86_64']:
        search_paths.append(lambda dn=dir_name: os.path.join(os.path.dirname(script_dir), dn, 'bin', QPDF_EXE))
        search_paths.append(lambda dn=dir_name: os.path.join(script_dir, dn, 'bin', QPDF_EXE))

    # === 系统安装路径 ===
    if sys.platform == 'win32':
        search_paths.extend([
            r"C:\Program Files\qpdf 12.3.2\bin\qpdf.exe",
            r"C:\Program Files\qpdf\bin\qpdf.exe",
            r"C:\qpdf-12.3.2-msvc64\bin\qpdf.exe",
            r"D:\qpdf-12.3.2-msvc64\bin\qpdf.exe",
        ])
    elif sys.platform == 'darwin':
        search_paths.extend([
            "/usr/local/bin/qpdf",
            "/opt/homebrew/bin/qpdf",
            "/opt/local/bin/qpdf",
        ])
    else:  # Linux / UOS
        search_paths.extend([
            "/usr/bin/qpdf",
            "/usr/local/bin/qpdf",
        ])

    # === build_exe.py 下载缓存 ===
    search_paths.append(lambda: next(
        (os.path.join(root, QPDF_EXE)
         for root, _, files in os.walk(os.path.join(script_dir, 'qpdf_cache'))
         if QPDF_EXE in files),
        None
    ))

    for entry in search_paths:
        path = entry() if callable(entry) else entry
        if path and os.path.isfile(path):
            return path
    # === 最后兜底：搜索系统 PATH ===
    which = shutil.which('qpdf')
    if which:
        return which
    return None


def get_qpdf_path():
    """查找可用的 qpdf，找到后缓存结果"""
    if not hasattr(get_qpdf_path, '_cached'):
        path = _search_qpdf()
        if not path:
            path = r"C:\Program Files\qpdf 12.3.2\bin\qpdf.exe"
        get_qpdf_path._cached = path
    return get_qpdf_path._cached


# ========== 图标字体检测与加载 ==========
_ICON_FONT = None  # 全局缓存：字体名称或 None

# Font Awesome 6 Solid 图标字符映射（优先使用，最专业）
_FA_ICON_CHARS = {
    'merge':    '\uf0c5',   # fa-copy（合并/复制）
    'rotate':   '\uf2f1',   # fa-rotate（旋转）
    'split':    '\uf0c4',   # fa-scissors（剪切/提取）
    'delete':   '\uf2ed',   # fa-trash-can（删除）
    'pagesize': '\uf002',   # fa-magnifying-glass（预览/尺寸）
    'decrypt':  '\uf09c',   # fa-unlock（解锁）
    'encrypt':  '\uf023',   # fa-lock（锁定）
    'restrict': '\uf3ed',   # fa-unlock-keyhole（移除限制/解锁）
    'info':     '\uf05a',   # fa-circle-info（信息）
    'summary':  '\uf15c',   # fa-file-lines（文档概要）
    'attach':   '\uf0c6',   # fa-paperclip（附件/回形针）
    'repair':   '\uf0ad',   # fa-wrench（修复/扳手）
    'print':    '\uf02f',   # fa-print（打印）
}

# 标题图标
_FA_TITLE_ICON_CHAR = '\uf1c1'   # fa-file-pdf

# Segoe MDL2 Assets / Fluent Icons 备用映射 (Win10/11 自带)
_MDL2_ICON_CHARS = {
    'merge':    '\uE8F1',   # CopyTo
    'rotate':   '\uE7AD',   # Rotate
    'split':    '\uE8C8',   # Cut
    'delete':   '\uE74D',   # Delete
    'pagesize': '\uE7C3',   # Preview
    'decrypt':  '\uE72E',   # Lock
    'encrypt':  '\uE72E',   # Lock
    'restrict': '\uEA18',   # Shield
    'info':     '\uE946',   # Info
    'summary':  '\uE8A5',   # Document
    'attach':   '\uE7C1',   # Link
    'repair':   '\uE90F',   # Settings
    'print':    '\uE749',   # Print
}
_MDL2_TITLE_ICON_CHAR = '\uEA90'


def _detect_icon_font():
    """检测并加载可用的图标字体（优先级：Font Awesome > Segoe Fluent > MDL2）"""
    global _ICON_FONT
    if _ICON_FONT is not None:
        return _ICON_FONT if _ICON_FONT != "" else None
    try:
        # 1. 尝试加载 Font Awesome .ttf 文件（最专业，圆润美观）
        fa_ttf = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fa-solid-900.ttf')
        if os.path.isfile(fa_ttf):
            if sys.platform == 'win32':
                try:
                    import ctypes
                    # 从内存加载字体（不锁定文件，不影响复制/删除）
                    with open(fa_ttf, 'rb') as f:
                        font_data = f.read()
                    # AddFontMemResourceEx: 从内存加载，不锁定 .ttf 文件
                    ctypes.windll.gdi32.AddFontMemResourceEx(
                        font_data, len(font_data), 0, ctypes.byref(ctypes.c_ulong(0))
                    )
                except Exception:
                    pass
            # 检查字体是否已注册成功
            families = tkfont.families()
            for fa_name in ["Font Awesome 6 Free", "Font Awesome 6 Free Solid"]:
                if fa_name in families:
                    _ICON_FONT = fa_name
                    return _ICON_FONT
    except Exception:
        pass
    if sys.platform == 'win32':
        try:
            # 2. (仅 Windows) 尝试系统 Segoe Fluent Icons / MDL2 Assets
            families = tkfont.families()
            for name in ["Segoe Fluent Icons", "Segoe MDL2 Assets"]:
                if name in families:
                    _ICON_FONT = name
                    return _ICON_FONT
        except Exception:
            pass
    _ICON_FONT = ""  # 标记已检测但未找到
    return None


def _get_icon_char(key, is_title=False):
    """根据已加载的字体返回对应的图标字符"""
    if is_title:
        if _ICON_FONT and 'Awesome' in _ICON_FONT:
            return _FA_TITLE_ICON_CHAR
        return _MDL2_TITLE_ICON_CHAR
    if _ICON_FONT and 'Awesome' in _ICON_FONT:
        return _FA_ICON_CHARS.get(key, '\uf128')
    return _MDL2_ICON_CHARS.get(key, '\uE7C3')


def _draw_rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    """在 Canvas 上绘制圆角矩形"""
    points = [
        x1 + r, y1, x2 - r, y1,
        x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r,
        x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def _draw_icon(canvas, key, icon_color, icon_bg):
    """在 Canvas 上绘制导航图标（优先使用系统图标字体，Fallback 到手绘）"""
    # 大圆角浅色背景
    _draw_rounded_rect(canvas, 1, 1, 23, 23, 8, fill=icon_bg, outline='')

    font = _detect_icon_font()
    if font:
        # 使用图标字体（Font Awesome > Segoe > Canvas 手绘）
        char = _get_icon_char(key)
        size = 13 if 'Awesome' in font else 12
        canvas.create_text(12, 13, text=char, fill=icon_color,
                          font=(font, size))
        return

    # Fallback: Canvas 手绘图形
    c = icon_color
    w = 1.2

    if key == 'merge':
        _draw_rounded_rect(canvas, 3, 4, 12, 14, 2, outline=c, width=w)
        _draw_rounded_rect(canvas, 10, 10, 20, 20, 2, outline=c, width=w, fill=icon_bg)
        canvas.create_line(12, 15, 18, 15, fill=c, width=1.5)
        canvas.create_line(15, 12, 15, 18, fill=c, width=1.5)

    elif key == 'rotate':
        canvas.create_arc(3, 3, 20, 20, start=50, extent=280,
                          outline=c, width=w, style='arc')
        canvas.create_polygon(19, 4, 20, 8.5, 15.5, 5.5, fill=c, outline='')

    elif key == 'split':
        _draw_rounded_rect(canvas, 3, 3, 13, 17, 2, outline=c, width=w)
        canvas.create_line(11, 10, 20, 10, fill=c, width=w,
                           arrow='last', arrowshape=(5, 6, 3))

    elif key == 'delete':
        _draw_rounded_rect(canvas, 7, 9, 17, 19, 2, outline=c, width=w)
        canvas.create_line(5, 9, 19, 9, fill=c, width=1.3)
        canvas.create_line(9, 6, 15, 6, fill=c, width=1.3)
        canvas.create_line(9, 6, 9, 9, fill=c, width=1.3)
        canvas.create_line(15, 6, 15, 9, fill=c, width=1.3)

    elif key == 'pagesize':
        _draw_rounded_rect(canvas, 4, 3, 14, 19, 2, outline=c, width=w)
        canvas.create_line(17, 5, 17, 17, fill=c, width=1,
                           arrow='both', arrowshape=(3, 4, 2))

    elif key == 'decrypt':
        # 开锁：锁体 + 明显翘起的锁扣（右侧完全抬起）
        _draw_rounded_rect(canvas, 5, 12, 19, 20, 2, outline=c, width=w, fill=icon_bg)
        # 锁扣：从锁体左侧出发，向右上方翘起（不闭合）
        # 左侧连接点
        canvas.create_line(7, 12, 7, 8, fill=c, width=w)
        # 弧形锁扣向右上方翘起（开口朝右下）
        canvas.create_arc(5, 0, 15, 10, start=200, extent=140, outline=c, width=w, style='arc')
        # 钥匙孔
        canvas.create_oval(10.5, 14.5, 13.5, 17.5, fill=c, outline='')

    elif key == 'encrypt':
        # 闭锁：锁体 + 闭合的U形锁扣
        _draw_rounded_rect(canvas, 5, 12, 19, 20, 2, outline=c, width=w, fill=icon_bg)
        # 闭合锁扣（完整U形，两侧都连入锁体）
        canvas.create_arc(7, 2, 17, 11, start=0, extent=180, outline=c, width=w, style='arc')
        # 两侧直边连入锁体
        canvas.create_line(7, 6.5, 7, 12, fill=c, width=w)
        canvas.create_line(17, 6.5, 17, 12, fill=c, width=w)
        # 钥匙孔
        canvas.create_oval(10.5, 14.5, 13.5, 17.5, fill=c, outline='')

    elif key == 'restrict':
        # 盾牌 + X号 = 保护/限制被移除
        canvas.create_polygon(12, 4, 19, 7, 19, 13, 12, 19, 5, 13, 5, 7,
                              outline=c, width=w, fill=icon_bg, smooth=True)
        # 更明显的X号
        canvas.create_line(8, 8, 16, 16, fill=c, width=2)
        canvas.create_line(16, 8, 8, 16, fill=c, width=2)

    elif key == 'info':
        canvas.create_oval(3, 3, 21, 21, outline=c, width=w)
        canvas.create_oval(10.5, 6.5, 13.5, 9.5, fill=c, outline='')
        canvas.create_line(12, 11, 12, 17, fill=c, width=1.8)

    elif key == 'summary':
        canvas.create_polygon(4, 3, 14, 3, 20, 9, 20, 20, 4, 20,
                              outline=c, width=w, fill=icon_bg, smooth=True)
        canvas.create_line(14, 3, 14, 9, fill=c, width=w)
        canvas.create_line(14, 9, 20, 9, fill=c, width=w)
        canvas.create_line(7, 12, 17, 12, fill=c, width=1)
        canvas.create_line(7, 15, 17, 15, fill=c, width=1)
        canvas.create_line(7, 18, 13, 18, fill=c, width=1)

    elif key == 'attach':
        canvas.create_arc(7, 3, 16, 12, start=0, extent=180,
                          outline=c, width=w, style='arc')
        canvas.create_line(7, 7.5, 7, 18, fill=c, width=w)
        canvas.create_line(16, 7.5, 16, 18, fill=c, width=w)
        canvas.create_arc(7, 14, 16, 22, start=180, extent=180,
                          outline=c, width=w, style='arc')

    elif key == 'repair':
        canvas.create_oval(6, 6, 18, 18, outline=c, width=w, fill=icon_bg)
        _draw_rounded_rect(canvas, 10, 2, 14, 6, 1.5, fill=c, outline='')
        _draw_rounded_rect(canvas, 10, 18, 14, 22, 1.5, fill=c, outline='')
        _draw_rounded_rect(canvas, 2, 10, 6, 14, 1.5, fill=c, outline='')
        _draw_rounded_rect(canvas, 18, 10, 22, 14, 1.5, fill=c, outline='')
        canvas.create_oval(9.5, 9.5, 14.5, 14.5, outline=c, width=1, fill=icon_bg)

    elif key == 'print':
        # 打印机：底部纸盒 + 上部出纸
        _draw_rounded_rect(canvas, 3, 10, 21, 20, 2, outline=c, width=w, fill=icon_bg)
        canvas.create_line(3, 14, 21, 14, fill=c, width=1)
        canvas.create_rectangle(7, 4, 17, 10, outline=c, width=w, fill=icon_bg)
        canvas.create_line(9, 16, 15, 16, fill=c, width=1)
        canvas.create_line(9, 18, 15, 18, fill=c, width=1)


class PdfToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF工具箱")
        self._config = self._load_config()
        geom = self._config.get('geometry', '780x560')
        self.root.geometry(geom)
        self.root.resizable(True, True)
        self.root.minsize(720, 500)
        if self._config.get('maximized'):
            self.root.state('zoomed')

        self.qpdf_path = get_qpdf_path()
        self._nav_buttons = {}
        self._pages = {}
        self._resize_timer = None
        _detect_icon_font()  # 在 Tk 实例存在后检测图标字体
        self._bind_resize_save()
        self._build_ui()

    # ==================== 配置持久化 ====================
    def _load_config(self):
        try:
            if os.path.isfile(_CONFIG_FILE):
                with open(_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_config(self):
        try:
            os.makedirs(_CONFIG_DIR, exist_ok=True)
            geom = self.root.winfo_geometry()
            self._config['geometry'] = geom.split('+')[0]
            self._config['maximized'] = self.root.state() == 'zoomed'
            with open(_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _bind_resize_save(self):
        def _on_resize(event):
            if event.widget == self.root:
                if self._resize_timer:
                    self.root.after_cancel(self._resize_timer)
                self._resize_timer = self.root.after(500, self._save_config)
        self.root.bind('<Configure>', _on_resize, add='+')
        self.root.protocol('WM_DELETE_WINDOW', lambda: (self._save_config(), self.root.destroy()))

    # ==================== UI 构建 ====================
    def _build_ui(self):
        # 主容器
        main = ttk.Frame(self.root)
        main.pack(fill='both', expand=True)

        # --- 左侧导航栏 ---
        # 根据标题文字宽度动态计算导航栏宽度，适配不同系统/字体/DPI
        _title_font = tk.font.Font(font=(UI_FONT, 11, 'bold'))
        _title_px = _title_font.measure("PDF工具箱")
        _nav_width = max(140, _title_px + 26 + 32)  # 文字 + 图标 + 两侧间距

        nav_frame = ttk.Frame(main, width=_nav_width)
        nav_frame.pack(side='left', fill='y')
        nav_frame.pack_propagate(False)

        # 导航栏背景（白色清新风格）
        nav_inner = tk.Frame(nav_frame, bg=NAV_BG, width=_nav_width)
        nav_inner.pack(fill='both', expand=True)
        nav_inner.pack_propagate(False)

        # 标题（带 Canvas 圆角矩形图标）- 固定在顶部
        title_row = tk.Frame(nav_inner, bg=NAV_BG)
        title_row.pack(fill='x', padx=12, pady=(14, 6))
        title_icon = tk.Canvas(title_row, width=26, height=26, bg=NAV_BG,
                               highlightthickness=0)
        title_icon.pack(side='left')
        _draw_rounded_rect(title_icon, 2, 2, 24, 24, 6,
                           fill='#1A73E8', outline='')
        font = _detect_icon_font()
        if font:
            title_char = _get_icon_char('merge', is_title=True)
            size = 12 if 'Awesome' not in font else 13
            title_icon.create_text(13, 14, text=title_char, fill='white',
                                   font=(font, size))
        else:
            # Fallback: 简单的 PDF 文字
            title_icon.create_text(13, 14, text="P", fill='white',
                                   font=('Arial', 11, 'bold'))
        tk.Label(title_row, text="PDF工具箱", font=(UI_FONT, 11, 'bold'),
                 bg=NAV_BG, fg='#1A73E8').pack(side='left', padx=(6, 0))

        # 分隔线
        tk.Frame(nav_inner, height=1, bg='#E8E8E8').pack(fill='x', padx=10, pady=(0, 8))

        # 可滚动的按钮区域（Frame 隔离 pack/grid）
        nav_scroll_frame = tk.Frame(nav_inner, bg=NAV_BG)
        nav_canvas = tk.Canvas(nav_scroll_frame, bg=NAV_BG, highlightthickness=0)
        nav_scrollbar = ttk.Scrollbar(nav_scroll_frame, orient='vertical', command=nav_canvas.yview)
        nav_scrollable = tk.Frame(nav_canvas, bg=NAV_BG)

        _nav_window = nav_canvas.create_window((0, 0), window=nav_scrollable, anchor='nw')

        nav_scroll_frame.pack(fill='both', expand=True)
        nav_scroll_frame.grid_rowconfigure(0, weight=1)
        nav_scroll_frame.grid_columnconfigure(0, weight=1)
        nav_scroll_frame.grid_columnconfigure(1, weight=0)

        nav_canvas.grid(row=0, column=0, sticky='nsew')
        nav_scrollbar.grid(row=0, column=1, sticky='ns')

        # 画布尺寸变化时同步内层宽度
        def _on_canvas_resize(e):
            cw = e.width
            if cw > 0:
                nav_canvas.itemconfigure(_nav_window, width=cw)

        nav_canvas.bind('<Configure>', _on_canvas_resize)

        # 刷新滚动条状态
        def _do_refresh_scrollbar():
            try:
                self.root.update_idletasks()
                bbox = nav_canvas.bbox('all')
                if bbox is None:
                    return
                content_h, canvas_h = bbox[3], nav_canvas.winfo_height()
                if canvas_h < 10:
                    return
                need = content_h > canvas_h
            except Exception:
                return
            if need:
                nav_scrollbar.grid()
                nav_canvas.configure(scrollregion=nav_canvas.bbox('all'))
            else:
                nav_scrollbar.grid_remove()
                nav_canvas.yview_moveto(0)

        def _refresh_scrollbar(*args):
            nav_canvas.configure(scrollregion=nav_canvas.bbox('all'))
            self.root.after_idle(_do_refresh_scrollbar)

        nav_scrollable.bind('<Configure>', _refresh_scrollbar)
        nav_inner.bind('<Configure>', _refresh_scrollbar)
        self.root.bind('<Configure>', _refresh_scrollbar)

        # 启动时先显示滚动条，窗口映射后再自动判断
        self.root.after(200, _refresh_scrollbar)

        # 鼠标滚轮（仅内容溢出时可用）
        def _on_mousewheel(event):
            if nav_scrollbar.winfo_ismapped():
                nav_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        def _bind_mousewheel(widget):
            widget.bind('<MouseWheel>', _on_mousewheel)
            for child in widget.winfo_children():
                _bind_mousewheel(child)

        self.root.after(100, lambda: _bind_mousewheel(nav_scrollable))

        # 按组生成导航按钮
        current_group = None
        for key, label, icon_color, icon_bg, group in NAV_ITEMS:
            if group != current_group:
                if current_group is not None:
                    tk.Frame(nav_scrollable, height=4, bg=NAV_BG).pack()  # 组间距
                tk.Label(nav_scrollable, text=group, font=(UI_FONT, 8),
                         bg=NAV_BG, fg='#BBBBBB', anchor='w').pack(fill='x', padx=14, pady=(0, 2))
                current_group = group

            # 使用容器确保图标对齐
            btn = tk.Frame(nav_scrollable, bg=NAV_BG, cursor='hand2')
            btn.pack(fill='x', padx=6, pady=1)
            
            # Canvas 图形图标（24x24）
            icon_canvas = tk.Canvas(btn, width=24, height=24, bg=NAV_BG,
                                    highlightthickness=0, cursor='hand2')
            icon_canvas.pack(side='left', padx=(4, 4), pady=3)
            # 绘制功能图形图标
            _draw_icon(icon_canvas, key, icon_color, icon_bg)
            
            # 文字
            text_lbl = tk.Label(btn, text=label, font=(UI_FONT, 9),
                               bg=NAV_BG, fg=NAV_FG, anchor='w')
            text_lbl.pack(side='left', fill='x', expand=True, padx=(2, 0))
            
            # 绑定事件到整个按钮容器
            for widget in [btn, icon_canvas, text_lbl]:
                widget.bind('<Button-1>', lambda e, k=key: self._switch_page(k))
            btn.bind('<Enter>', lambda e, b=btn, ic=icon_canvas, tl=text_lbl: 
                     self._on_nav_hover(b, ic, tl, True))
            btn.bind('<Leave>', lambda e, b=btn, ic=icon_canvas, tl=text_lbl: 
                     self._on_nav_hover(b, ic, tl, False))
            self._nav_buttons[key] = (btn, icon_canvas, text_lbl)

        # --- 右侧内容区 ---
        content_frame = ttk.Frame(main, padding=0)
        content_frame.pack(side='left', fill='both', expand=True)

        # 页面标题栏（白色 + 左侧蓝色竖线）
        self.page_title_var = tk.StringVar(value="合并PDF")
        title_frame = tk.Frame(content_frame, bg=TITLE_BG, height=44)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        # 蓝色左侧竖线
        tk.Frame(title_frame, width=4, bg=ACCENT_COLOR).pack(side='left', fill='y', padx=(0, 0), pady=10)
        tk.Label(title_frame, textvariable=self.page_title_var,
                 font=(UI_FONT, 13, 'bold'),
                 bg=TITLE_BG, fg='#333333').pack(side='left', padx=(10, 16))
        tk.Frame(title_frame, height=1, bg='#E8E8E8').pack(side='bottom', fill='x')

        # 页面容器
        self.page_container = ttk.Frame(content_frame)
        self.page_container.pack(fill='both', expand=True, padx=14, pady=10)

        # 创建所有页面
        self._create_pages()

        # 默认显示第一个
        self._switch_page("merge")

        # 状态栏
        self.status_var = ttk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var,
                               bootstyle=(LIGHT, INVERSE),
                               anchor='w', padding=(10, 4))
        status_bar.pack(fill='x', side='bottom')

    def _on_nav_hover(self, btn, icon_canvas, text_lbl, entering):
        """导航按钮悬停效果"""
        # 检查是否为当前选中项
        is_active = btn['bg'] == NAV_BG_ACTIVE
        if entering and not is_active:
            bg = NAV_BG_HOVER
        elif not entering and not is_active:
            bg = NAV_BG
        else:
            return
        btn.config(bg=bg)
        icon_canvas.config(bg=bg)
        text_lbl.config(bg=bg)

    def _switch_page(self, key):
        """切换页面"""
        # 更新导航按钮状态
        for k, (btn, icon_canvas, text_lbl) in self._nav_buttons.items():
            if k == key:
                btn.config(bg=NAV_BG_ACTIVE)
                icon_canvas.config(bg=NAV_BG_ACTIVE)
                text_lbl.config(bg=NAV_BG_ACTIVE, fg=NAV_FG_ACTIVE)
            else:
                btn.config(bg=NAV_BG)
                icon_canvas.config(bg=NAV_BG)
                text_lbl.config(bg=NAV_BG, fg=NAV_FG)

        # 更新标题（图标 + 文字，不带 emoji）
        for item_key, label, icon_color, icon_bg, group in NAV_ITEMS:
            if item_key == key:
                self.page_title_var.set(label)
                break

        # 切换页面
        for k, page in self._pages.items():
            if k == key:
                page.pack(fill='both', expand=True)
            else:
                page.pack_forget()

    def _create_pages(self):
        """创建所有功能页面"""
        builders = {
            "merge": self._build_merge_page,
            "rotate": self._build_rotate_page,
            "split": self._build_split_page,
            "delete": self._build_delete_page,
            "decrypt": self._build_decrypt_page,
            "encrypt": self._build_encrypt_page,
            "restrict": self._build_restrict_page,
            "info": self._build_info_page,
            "summary": self._build_summary_page,
            "pagesize": self._build_pagesize_page,
            "attach": self._build_attach_page,
            "repair": self._build_repair_page,
            "print": self._build_print_page,
        }
        for key, builder in builders.items():
            page = ttk.Frame(self.page_container)
            builder(page)
            self._pages[key] = page

    # ==================== 通用组件工厂 ====================
    def _make_file_row(self, parent, label, var, browse_cmd):
        """创建一行：标签 + 输入框 + 浏览按钮"""
        row = ttk.Frame(parent)
        row.pack(fill='x', pady=5)
        ttk.Label(row, text=label, width=10, anchor='e',
                  font=(UI_FONT, 9)).pack(side='left')
        entry = ttk.Entry(row, textvariable=var)
        entry.pack(side='left', fill='x', expand=True, padx=(8, 8))
        ttk.Button(row, text="浏览...", command=browse_cmd,
                   bootstyle=PRIMARY, width=8).pack(side='left')

    def _make_action_bar(self, parent, buttons):
        """创建底部操作按钮栏, buttons=[(text, cmd, bootstyle), ...]"""
        bf = ttk.Frame(parent)
        bf.pack(fill='x', pady=(14, 6))
        for text, cmd, style in buttons:
            ttk.Button(bf, text=text, command=cmd,
                       bootstyle=style, width=16).pack(side='left', padx=10, expand=True)

    def _make_hint(self, parent, text):
        """创建灰色提示文字"""
        ttk.Label(parent, text=text, bootstyle=SECONDARY,
                  font=(UI_FONT, 8),
                  wraplength=560).pack(fill='x', pady=(6, 2))

    # ==================== 合并PDF ====================
    def _build_merge_page(self, parent):
        self.merge_files = []
        self.merge_output = ttk.StringVar()

        lf = ttk.Labelframe(parent, text="要合并的PDF文件（按顺序）", padding=10)
        lf.pack(fill='both', expand=True, pady=(0, 6))

        list_frame = ttk.Frame(lf)
        list_frame.pack(fill='both', expand=True)
        self.merge_listbox = tk.Listbox(list_frame, height=6, bg='#FAFCFF',
                                         selectbackground='#1A73E8', selectforeground='white',
                                         font=(UI_FONT_FIXED, 9), relief='solid', bd=1,
                                         borderwidth=1, highlightthickness=0,
                                         selectborderwidth=0, activestyle='none')
        sb = ttk.Scrollbar(list_frame, command=self.merge_listbox.yview, bootstyle=ROUND)
        self.merge_listbox.config(yscrollcommand=sb.set)
        self.merge_listbox.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        btn_frame = ttk.Frame(lf)
        btn_frame.pack(fill='x', pady=(8, 0))
        for text, cmd in [("添加文件", self._merge_add), ("删除选中", self._merge_remove),
                          ("上移", lambda: self._merge_move(-1)), ("下移", lambda: self._merge_move(1)),
                          ("清空", self._merge_clear)]:
            ttk.Button(btn_frame, text=text, command=cmd,
                       bootstyle=OUTLINE, width=10).pack(side='left', padx=3)

        lf2 = ttk.Labelframe(parent, text="输出PDF文件", padding=10)
        lf2.pack(fill='x', pady=6)
        self._make_file_row(lf2, "输出文件：", self.merge_output,
                            lambda: self._browse_save(self.merge_output))

        self._make_action_bar(parent, [("执 行 合 并", self._do_merge, PRIMARY)])

    def _merge_add(self):
        paths = filedialog.askopenfilenames(title="选择PDF文件", filetypes=[("PDF文件", "*.pdf")])
        for p in paths:
            self.merge_files.append(p)
            self.merge_listbox.insert('end', os.path.basename(p))

    def _merge_remove(self):
        sel = self.merge_listbox.curselection()
        for i in reversed(sel):
            self.merge_listbox.delete(i)
            del self.merge_files[i]

    def _merge_move(self, direction):
        sel = self.merge_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self.merge_files):
            return
        self.merge_files[idx], self.merge_files[new_idx] = self.merge_files[new_idx], self.merge_files[idx]
        self.merge_listbox.delete(0, 'end')
        for fp in self.merge_files:
            self.merge_listbox.insert('end', os.path.basename(fp))
        self.merge_listbox.selection_set(new_idx)

    def _merge_clear(self):
        self.merge_files.clear()
        self.merge_listbox.delete(0, 'end')

    def _do_merge(self):
        if len(self.merge_files) < 2:
            Messagebox.show_warning("请至少添加2个PDF文件", "提示")
            return
        if not self.merge_output.get():
            Messagebox.show_warning("请指定输出PDF文件", "提示")
            return
        if not os.path.isfile(self.qpdf_path):
            Messagebox.show_error(f"qpdf.exe 不存在：\n{self.qpdf_path}", "错误")
            return
        pages_args = ["--pages"] + self.merge_files + ["--"]
        cmd = [self.qpdf_path] + pages_args + [self.merge_files[0], self.merge_output.get()]
        self._run_cmd(cmd, "合并完成！")

    # ==================== 页面旋转 ====================
    def _build_rotate_page(self, parent):
        self.rotate_input = ttk.StringVar()
        self.rotate_output = ttk.StringVar()
        self.rotate_pages = ttk.StringVar()
        self.rotate_angle = ttk.StringVar(value="90")

        self._make_file_row(parent, "输入文件：", self.rotate_input,
                            lambda: self._browse_pdf(self.rotate_input, self.rotate_output))
        self._make_file_row(parent, "输出文件：", self.rotate_output,
                            lambda: self._browse_save(self.rotate_output))

        lf = ttk.Labelframe(parent, text="旋转设置", padding=10)
        lf.pack(fill='x', pady=8)

        row = ttk.Frame(lf)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="旋转页码：", width=10, anchor='e').pack(side='left')
        ttk.Entry(row, textvariable=self.rotate_pages, width=30).pack(side='left', padx=8)
        ttk.Label(row, text="(留空=全部, 如: 1,1-3,5)", bootstyle=SECONDARY).pack(side='left', padx=4)

        row = ttk.Frame(lf)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="旋转角度：", width=10, anchor='e').pack(side='left')
        for text, val in [("顺时针90°", "90"), ("180°", "180"), ("逆时针90°", "-90")]:
            ttk.Radiobutton(row, text=text, value=val, variable=self.rotate_angle,
                            bootstyle=PRIMARY).pack(side='left', padx=8)

        self._make_action_bar(parent, [("执 行 旋 转", self._do_rotate, PRIMARY)])

    def _do_rotate(self):
        if not self._check_input_output(self.rotate_input, self.rotate_output):
            return
        angle = self.rotate_angle.get()
        pages = self.rotate_pages.get().strip()
        if pages:
            rotate_arg = f"--rotate=+{angle}:{pages}" if not angle.startswith('-') else f"--rotate={angle}:{pages}"
        else:
            rotate_arg = f"--rotate=+{angle}" if not angle.startswith('-') else f"--rotate={angle}"
        cmd = [self.qpdf_path] + rotate_arg.split() + [self.rotate_input.get(), self.rotate_output.get()]
        self._run_cmd(cmd, "旋转完成！")

    # ==================== 提取页面 ====================
    def _build_split_page(self, parent):
        self.split_input = ttk.StringVar()
        self.split_output = ttk.StringVar()
        self.split_pages = ttk.StringVar()

        self._make_file_row(parent, "输入文件：", self.split_input,
                            lambda: self._browse_pdf(self.split_input, self.split_output))
        self._make_file_row(parent, "输出文件：", self.split_output,
                            lambda: self._browse_save(self.split_output))

        lf = ttk.Labelframe(parent, text="提取设置", padding=10)
        lf.pack(fill='x', pady=8)
        row = ttk.Frame(lf)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="提取页码：", width=10, anchor='e').pack(side='left')
        ttk.Entry(row, textvariable=self.split_pages, width=30).pack(side='left', padx=8)
        ttk.Label(row, text="(如: 1-3,5,7-9)", bootstyle=SECONDARY).pack(side='left', padx=4)

        self._make_action_bar(parent, [("执 行 提 取", self._do_split, PRIMARY)])

    def _do_split(self):
        if not self._check_input_output(self.split_input, self.split_output):
            return
        pages = self.split_pages.get().strip()
        if not pages:
            Messagebox.show_warning("请输入要提取的页码", "提示")
            return
        cmd = [self.qpdf_path, "--pages", ".", pages, "--", self.split_input.get(), self.split_output.get()]
        self._run_cmd(cmd, "提取完成！")

    # ==================== 删除页面 ====================
    def _build_delete_page(self, parent):
        self.delete_input = ttk.StringVar()
        self.delete_output = ttk.StringVar()
        self.delete_pages = ttk.StringVar()

        self._make_file_row(parent, "输入文件：", self.delete_input,
                            lambda: self._browse_pdf(self.delete_input, self.delete_output))
        self._make_file_row(parent, "输出文件：", self.delete_output,
                            lambda: self._browse_save(self.delete_output))

        lf = ttk.Labelframe(parent, text="删除设置", padding=10)
        lf.pack(fill='x', pady=8)
        row = ttk.Frame(lf)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="删除页码：", width=10, anchor='e').pack(side='left')
        ttk.Entry(row, textvariable=self.delete_pages, width=30).pack(side='left', padx=8)
        ttk.Label(row, text="(如: 2,4-6)", bootstyle=SECONDARY).pack(side='left', padx=4)

        self._make_action_bar(parent, [("执 行 删 除", self._do_delete, PRIMARY)])

    def _do_delete(self):
        if not self._check_input_output(self.delete_input, self.delete_output):
            return
        pages = self.delete_pages.get().strip()
        if not pages:
            Messagebox.show_warning("请输入要删除的页码", "提示")
            return
        delete_parts = [f"r{p.strip()}" for p in pages.split(',')]
        exclude_str = ','.join(delete_parts)
        cmd = [self.qpdf_path, "--pages", ".", exclude_str, "--", self.delete_input.get(), self.delete_output.get()]
        self._run_cmd(cmd, "删除完成！")

    # ==================== 解密PDF ====================
    def _build_decrypt_page(self, parent):
        self.decrypt_input = ttk.StringVar()
        self.decrypt_output = ttk.StringVar()
        self.decrypt_password = ttk.StringVar()

        self._make_file_row(parent, "输入文件：", self.decrypt_input,
                            lambda: self._browse_pdf(self.decrypt_input, self.decrypt_output))
        self._make_file_row(parent, "输出文件：", self.decrypt_output,
                            lambda: self._browse_save(self.decrypt_output))

        lf = ttk.Labelframe(parent, text="解密设置", padding=10)
        lf.pack(fill='x', pady=8)
        row = ttk.Frame(lf)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="打开密码：", width=10, anchor='e').pack(side='left')
        ttk.Entry(row, textvariable=self.decrypt_password, width=30, show='*').pack(side='left', padx=8)
        ttk.Label(row, text="(有密码时填写)", bootstyle=SECONDARY).pack(side='left', padx=4)

        self._make_hint(parent, "说明：移除PDF的打开密码，需要知道原密码才能解密")
        self._make_action_bar(parent, [("执 行 解 密", self._do_decrypt, PRIMARY)])

    def _do_decrypt(self):
        if not self._check_input_output(self.decrypt_input, self.decrypt_output):
            return
        cmd = [self.qpdf_path, "--decrypt"]
        pwd = self.decrypt_password.get().strip()
        if pwd:
            cmd += [f"--password={pwd}"]
        cmd += [self.decrypt_input.get(), self.decrypt_output.get()]
        self._run_cmd(cmd, "解密完成！")

    # ==================== 加密PDF ====================
    def _build_encrypt_page(self, parent):
        self.encrypt_input = ttk.StringVar()
        self.encrypt_output = ttk.StringVar()
        self.encrypt_user_pwd = ttk.StringVar()
        self.encrypt_owner_pwd = ttk.StringVar()
        self.encrypt_key = ttk.StringVar(value="256")

        self._make_file_row(parent, "输入文件：", self.encrypt_input,
                            lambda: self._browse_pdf(self.encrypt_input, self.encrypt_output))
        self._make_file_row(parent, "输出文件：", self.encrypt_output,
                            lambda: self._browse_save(self.encrypt_output))

        lf = ttk.Labelframe(parent, text="加密设置", padding=10)
        lf.pack(fill='x', pady=8)

        row = ttk.Frame(lf)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="打开密码：", width=10, anchor='e').pack(side='left')
        ttk.Entry(row, textvariable=self.encrypt_user_pwd, width=30, show='*').pack(side='left', padx=8)
        ttk.Label(row, text="(打开PDF时需要输入)", bootstyle=SECONDARY).pack(side='left', padx=4)

        row = ttk.Frame(lf)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="权限密码：", width=10, anchor='e').pack(side='left')
        ttk.Entry(row, textvariable=self.encrypt_owner_pwd, width=30, show='*').pack(side='left', padx=8)
        ttk.Label(row, text="(控制打印/复制等权限)", bootstyle=SECONDARY).pack(side='left', padx=4)

        row = ttk.Frame(lf)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="加密强度：", width=10, anchor='e').pack(side='left')
        for text, val in [("256位AES", "256"), ("128位AES", "128"), ("40位RC4", "40")]:
            ttk.Radiobutton(row, text=text, value=val, variable=self.encrypt_key,
                            bootstyle=PRIMARY).pack(side='left', padx=8)

        self._make_action_bar(parent, [("执 行 加 密", self._do_encrypt, PRIMARY)])

    def _do_encrypt(self):
        if not self._check_input_output(self.encrypt_input, self.encrypt_output):
            return
        user_pwd = self.encrypt_user_pwd.get()
        owner_pwd = self.encrypt_owner_pwd.get()
        if not user_pwd and not owner_pwd:
            Messagebox.show_warning("请至少设置打开密码或权限密码", "提示")
            return
        key_len = self.encrypt_key.get()
        cmd = [self.qpdf_path, "--encrypt", user_pwd, owner_pwd, key_len, "--",
               self.encrypt_input.get(), self.encrypt_output.get()]
        self._run_cmd(cmd, "加密完成！")

    # ==================== 移除限制 ====================
    def _build_restrict_page(self, parent):
        self.restrict_input = ttk.StringVar()
        self.restrict_output = ttk.StringVar()

        self._make_file_row(parent, "输入文件：", self.restrict_input,
                            lambda: self._browse_pdf(self.restrict_input, self.restrict_output))
        self._make_file_row(parent, "输出文件：", self.restrict_output,
                            lambda: self._browse_save(self.restrict_output))

        self._make_hint(parent, "说明：PDF能打开但禁止打印/复制/编辑时，用此功能去掉权限限制\n（不需要密码，直接去掉所有者密码限制）")
        self._make_action_bar(parent, [("移 除 限 制", self._do_restrict, PRIMARY)])

    def _do_restrict(self):
        if not self._check_input_output(self.restrict_input, self.restrict_output):
            return
        cmd = [self.qpdf_path, "--decrypt", self.restrict_input.get(), self.restrict_output.get()]
        self._run_cmd(cmd, "限制已移除！")

    # ==================== 查看信息 ====================
    def _build_info_page(self, parent):
        self.info_input = ttk.StringVar()

        self._make_file_row(parent, "PDF文件：", self.info_input,
                            lambda: self._browse_pdf(self.info_input))

        self._make_hint(parent, "查看每页的页码、旋转角度、尺寸等信息")

        self._make_action_bar(parent, [
            ("查看页面信息", self._do_info, PRIMARY),
            ("查看页面旋转", lambda: self._do_info_extra("--show-rotation"), INFO),
        ])

        # 结果显示区
        self.info_text = ScrolledText(parent, height=12, autohide=True, bootstyle=INFO)
        self.info_text.pack(fill='both', expand=True, pady=(8, 0))

    def _do_info(self):
        if not self._check_input(self.info_input):
            return
        cmd = [self.qpdf_path, "--show-pages", "--show-rotation", self.info_input.get()]
        self._run_show_cmd(cmd, self.info_text)

    def _do_info_extra(self, extra_arg):
        if not self._check_input(self.info_input):
            return
        cmd = [self.qpdf_path, "--show-pages", extra_arg, self.info_input.get()]
        self._run_show_cmd(cmd, self.info_text)

    # ==================== PDF概要 ====================
    def _build_summary_page(self, parent):
        self.summary_input = ttk.StringVar()

        self._make_file_row(parent, "PDF文件：", self.summary_input,
                            lambda: self._browse_pdf(self.summary_input))

        self._make_hint(parent, "显示PDF的加密状态、PDF版本、页数等基本信息")

        self._make_action_bar(parent, [
            ("显示概要", self._do_summary, PRIMARY),
            ("检查结构", self._do_check, INFO),
            ("显示加密信息", self._do_encryption_info, INFO),
        ])

        self.summary_text = ScrolledText(parent, height=12, autohide=True, bootstyle=INFO)
        self.summary_text.pack(fill='both', expand=True, pady=(8, 0))

    def _do_summary(self):
        if not self._check_input(self.summary_input):
            return
        cmd = [self.qpdf_path, "--show-encryption", "--show-pages", "--show-rotation", self.summary_input.get()]
        self._run_show_cmd(cmd, self.summary_text)

    def _do_check(self):
        if not self._check_input(self.summary_input):
            return
        cmd = [self.qpdf_path, "--check", self.summary_input.get()]
        self._run_show_cmd(cmd, self.summary_text)

    def _do_encryption_info(self):
        if not self._check_input(self.summary_input):
            return
        cmd = [self.qpdf_path, "--show-encryption", self.summary_input.get()]
        self._run_show_cmd(cmd, self.summary_text)

    # ==================== 页面大小 ====================
    def _build_pagesize_page(self, parent):
        self.pagesize_input = ttk.StringVar()
        self.pagesize_output = ttk.StringVar()
        self.pagesize_width = ttk.StringVar(value="210")
        self.pagesize_height = ttk.StringVar(value="297")
        self.pagesize_unit = ttk.StringVar(value="mm")
        self.pagesize_pages = ttk.StringVar()

        self._make_file_row(parent, "输入文件：", self.pagesize_input,
                            lambda: self._browse_pdf(self.pagesize_input, self.pagesize_output))
        self._make_file_row(parent, "输出文件：", self.pagesize_output,
                            lambda: self._browse_save(self.pagesize_output))

        lf = ttk.Labelframe(parent, text="页面大小设置", padding=10)
        lf.pack(fill='x', pady=8)

        # 预设
        row = ttk.Frame(lf)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="常用预设：", width=10, anchor='e').pack(side='left')
        presets = [("A4", "210", "297"), ("A3", "297", "420"),
                   ("Letter", "8.5", "11"), ("Legal", "8.5", "14")]
        for text, w, h in presets:
            ttk.Button(row, text=text, command=lambda w=w, h=h: self._set_pagesize_preset(w, h),
                       bootstyle=OUTLINE, width=8).pack(side='left', padx=4)

        row = ttk.Frame(lf)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="宽度：", width=10, anchor='e').pack(side='left')
        ttk.Entry(row, textvariable=self.pagesize_width, width=8).pack(side='left', padx=4)
        ttk.Label(row, text="高度：").pack(side='left')
        ttk.Entry(row, textvariable=self.pagesize_height, width=8).pack(side='left', padx=4)
        ttk.Label(row, text="单位：").pack(side='left', padx=(8, 0))
        for text, val in [("mm", "mm"), ("cm", "cm"), ("in", "in"), ("pt", "pt")]:
            ttk.Radiobutton(row, text=text, value=val, variable=self.pagesize_unit,
                            bootstyle=PRIMARY).pack(side='left', padx=4)

        row = ttk.Frame(lf)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="应用页码：", width=10, anchor='e').pack(side='left')
        ttk.Entry(row, textvariable=self.pagesize_pages, width=30).pack(side='left', padx=8)
        ttk.Label(row, text="(留空=全部)", bootstyle=SECONDARY).pack(side='left', padx=4)

        self._make_action_bar(parent, [("设 置 页 面 大 小", self._do_pagesize, PRIMARY)])

    def _set_pagesize_preset(self, w, h):
        self.pagesize_width.set(w)
        self.pagesize_height.set(h)

    def _do_pagesize(self):
        if not self._check_input_output(self.pagesize_input, self.pagesize_output):
            return
        w = self.pagesize_width.get().strip()
        h = self.pagesize_height.get().strip()
        if not w or not h:
            Messagebox.show_warning("请输入页面宽度和高度", "提示")
            return

        unit = self.pagesize_unit.get()
        factor = {"mm": 2.835, "cm": 28.35, "in": 72, "pt": 1}
        w_pt = float(w) * factor[unit]
        h_pt = float(h) * factor[unit]

        cmd = [self.qpdf_path,
               f"--set-page-geometry={w_pt:.1f}x{h_pt:.1f}",
               "--replace-input" if not self.pagesize_pages.get().strip() else ""]

        pages = self.pagesize_pages.get().strip()
        if pages:
            cmd = [self.qpdf_path, "--pages", ".", pages, "--"]

        cmd = [c for c in cmd if c]
        cmd += [self.pagesize_input.get(), self.pagesize_output.get()]
        self._run_cmd(cmd, "页面大小设置完成！")

    # ==================== 附件管理 ====================
    def _build_attach_page(self, parent):
        # 上半部分：添加附件
        lf_add = ttk.Labelframe(parent, text="添加附件", padding=10)
        lf_add.pack(fill='x', pady=(0, 8))

        self.attach_input = ttk.StringVar()
        self.attach_output = ttk.StringVar()
        self.attach_file = ttk.StringVar()

        row = ttk.Frame(lf_add)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="PDF文件：", width=10, anchor='e').pack(side='left')
        ttk.Entry(row, textvariable=self.attach_input).pack(side='left', fill='x', expand=True, padx=8)
        ttk.Button(row, text="浏览...", command=lambda: self._browse_pdf(self.attach_input, self.attach_output),
                   bootstyle=PRIMARY, width=8).pack(side='left')

        row = ttk.Frame(lf_add)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="附件文件：", width=10, anchor='e').pack(side='left')
        ttk.Entry(row, textvariable=self.attach_file).pack(side='left', fill='x', expand=True, padx=8)
        ttk.Button(row, text="浏览...", command=self._browse_attach_file,
                   bootstyle=PRIMARY, width=8).pack(side='left')

        row = ttk.Frame(lf_add)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="输出PDF：", width=10, anchor='e').pack(side='left')
        ttk.Entry(row, textvariable=self.attach_output).pack(side='left', fill='x', expand=True, padx=8)
        ttk.Button(row, text="浏览...", command=lambda: self._browse_save(self.attach_output),
                   bootstyle=PRIMARY, width=8).pack(side='left')

        ttk.Button(lf_add, text="添加附件到PDF", command=self._do_add_attach,
                   bootstyle=PRIMARY, width=18).pack(pady=8)

        # 下半部分：查看附件
        lf_view = ttk.Labelframe(parent, text="查看附件", padding=10)
        lf_view.pack(fill='both', expand=True)

        ttk.Button(lf_view, text="列出所有附件", command=self._do_list_attach,
                   bootstyle=INFO, width=16).pack(pady=(0, 8))

        self.attach_text = ScrolledText(lf_view, height=8, autohide=True, bootstyle=INFO)
        self.attach_text.pack(fill='both', expand=True)

    def _browse_attach_file(self):
        path = filedialog.askopenfilename(title="选择附件文件")
        if path:
            self.attach_file.set(path)

    def _do_add_attach(self):
        if not self._check_input_output(self.attach_input, self.attach_output):
            return
        if not self.attach_file.get() or not os.path.isfile(self.attach_file.get()):
            Messagebox.show_warning("请选择要添加的附件文件", "提示")
            return
        cmd = [self.qpdf_path, "--add-attachment", self.attach_file.get(),
               "--", self.attach_input.get(), self.attach_output.get()]
        self._run_cmd(cmd, "附件添加完成！")

    def _do_list_attach(self):
        if not self._check_input(self.attach_input):
            return
        cmd = [self.qpdf_path, "--list-attachments", self.attach_input.get()]
        self._run_show_cmd(cmd, self.attach_text)

    # ==================== 修复PDF ====================
    def _build_repair_page(self, parent):
        self.repair_input = ttk.StringVar()
        self.repair_output = ttk.StringVar()

        self._make_file_row(parent, "输入文件：", self.repair_input,
                            lambda: self._browse_pdf(self.repair_input, self.repair_output))
        self._make_file_row(parent, "输出文件：", self.repair_output,
                            lambda: self._browse_save(self.repair_output))

        self._make_hint(parent, "说明：qpdf在复制PDF时会自动修复损坏的结构，\n"
                          "包括修复交叉引用表、修复损坏的对象流等。\n"
                          "对于严重损坏的文件，可加 --qdf 选项进行深度修复。")

        self._make_action_bar(parent, [
            ("常规修复", self._do_repair, PRIMARY),
            ("深度修复(--qdf)", self._do_repair_deep, INFO),
        ])

    def _do_repair(self):
        if not self._check_input_output(self.repair_input, self.repair_output):
            return
        cmd = [self.qpdf_path, self.repair_input.get(), self.repair_output.get()]
        self._run_cmd(cmd, "修复完成！")

    def _do_repair_deep(self):
        if not self._check_input_output(self.repair_input, self.repair_output):
            return
        cmd = [self.qpdf_path, "--qdf", self.repair_input.get(), self.repair_output.get()]
        self._run_cmd(cmd, "深度修复完成！")

    # ==================== 批量打印 ====================
    @staticmethod
    def _get_printers():
        """获取系统所有可用打印机列表"""
        printers = []
        try:
            if sys.platform == 'win32':
                import ctypes
                buf = ctypes.create_unicode_buffer(0)
                buf_size = ctypes.wintypes.DWORD(0)
                num_printers = ctypes.wintypes.DWORD(0)
                ctypes.windll.winspool.drv.EnumPrintersW(
                    0x06, None, 2, buf, 0, ctypes.byref(buf_size), ctypes.byref(num_printers)
                )
                if buf_size.value > 0:
                    buf = ctypes.create_unicode_buffer(buf_size.value)
                    ctypes.windll.winspool.drv.EnumPrintersW(
                        0x06, None, 2, buf, buf_size,
                        ctypes.byref(buf_size), ctypes.byref(num_printers)
                    )
                    ptr_size = ctypes.sizeof(ctypes.c_void_p)
                    offset = 4 * ptr_size
                    for i in range(num_printers.value):
                        base = ctypes.addressof(buf) + i * 21 * ptr_size
                        name_ptr = ctypes.c_void_p.from_buffer_copy(
                            ctypes.string_at(base + offset, ptr_size))
                        if name_ptr.value:
                            name = ctypes.wstring_at(name_ptr.value)
                            if name:
                                printers.append(name)
                if not printers:
                    result = subprocess.run(
                        ['powershell', '-NoProfile', '-Command',
                         'Get-Printer | Select-Object -ExpandProperty Name'],
                        capture_output=True, text=True, timeout=10,
                        creationflags=_NO_WINDOW
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        printers = [n.strip() for n in result.stdout.strip().split('\n') if n.strip()]
            else:
                result = subprocess.run(
                    ['lpstat', '-p'], capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line.startswith('printer '):
                            parts = line.split()
                            if len(parts) > 1:
                                printers.append(parts[1])
        except Exception:
            pass
        return printers

    @staticmethod
    def _get_default_printer():
        """获取当前默认打印机名称"""
        try:
            if sys.platform == 'win32':
                import ctypes
                buf = ctypes.create_unicode_buffer(256)
                size = ctypes.wintypes.DWORD(256)
                ctypes.windll.winspool.drv.GetDefaultPrinterW(buf, ctypes.byref(size))
                return buf.value
            else:
                result = subprocess.run(
                    ['lpstat', '-d'], capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    line = result.stdout.strip()
                    if line.startswith('system default destination:'):
                        parts = line.split(':')
                        if len(parts) > 1:
                            return parts[1].strip()
                    return line.strip()
        except Exception:
            pass
        return ""

    @staticmethod
    def _set_default_printer(name):
        """设置默认打印机"""
        try:
            if sys.platform == 'win32':
                import ctypes
                return ctypes.windll.winspool.drv.SetDefaultPrinterW(name) != 0
            else:
                result = subprocess.run(
                    ['lpoptions', '-d', name], capture_output=True, text=True, timeout=10
                )
                return result.returncode == 0
        except Exception:
            return False

    def _build_print_page(self, parent):
        self.print_files = []

        # 打印机选择
        pf = ttk.Frame(parent)
        pf.pack(fill='x', pady=(0, 6))
        ttk.Label(pf, text="选择打印机：", width=10, anchor='e',
                  font=(UI_FONT, 9)).pack(side='left')
        self.printer_var = ttk.StringVar()
        printers = self._get_printers()
        default_printer = self._get_default_printer()
        self.printer_combo = ttk.Combobox(pf, textvariable=self.printer_var,
                                           values=printers, state='readonly', width=30)
        self.printer_combo.pack(side='left', padx=8)
        if default_printer and default_printer in printers:
            self.printer_var.set(default_printer)
        elif printers:
            self.printer_var.set(printers[0])
        ttk.Button(pf, text="刷新", command=self._refresh_printers,
                   bootstyle=INFO, width=6).pack(side='left', padx=4)

        # 文件列表区域
        lf = ttk.Labelframe(parent, text="待打印文件", padding=10)
        lf.pack(fill='both', expand=True, pady=(0, 8))

        btn_row = ttk.Frame(lf)
        btn_row.pack(fill='x', pady=(0, 6))
        ttk.Button(btn_row, text="添加文件", command=self._add_print_files,
                   bootstyle=PRIMARY, width=12).pack(side='left', padx=(0, 6))
        ttk.Button(btn_row, text="添加文件夹", command=self._add_print_folder,
                   bootstyle=INFO, width=12).pack(side='left', padx=(0, 6))
        ttk.Button(btn_row, text="清空列表", command=self._clear_print_files,
                   bootstyle=WARNING, width=10).pack(side='left')

        # 文件列表
        list_frame = ttk.Frame(lf)
        list_frame.pack(fill='both', expand=True)

        self.print_listbox = tk.Listbox(list_frame, selectmode='extended',
                                         font=(UI_FONT, 9))
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical',
                                  command=self.print_listbox.yview)
        self.print_listbox.config(yscrollcommand=scrollbar.set)
        self.print_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        ttk.Button(lf, text="删除选中", command=self._remove_selected_print,
                   bootstyle=WARNING, width=10).pack(anchor='e', pady=(4, 0))

        # 统计
        self.print_count_lbl = ttk.Label(parent, text="共 0 个文件",
                                          font=(UI_FONT, 9),
                                          bootstyle=SECONDARY)
        self.print_count_lbl.pack(anchor='w', pady=(0, 4))

        self._make_hint(parent, "说明：支持打印PDF、Word、Excel、PPT、图片等任何可打印文件\n"
                          "选择打印机后点击开始打印，将依次发送到指定打印机")

        self._make_action_bar(parent, [("开 始 打 印", self._do_print, PRIMARY)])

    def _refresh_printers(self):
        printers = self._get_printers()
        self.printer_combo.config(values=printers)
        default_printer = self._get_default_printer()
        if default_printer and default_printer in printers:
            self.printer_var.set(default_printer)
        elif printers:
            self.printer_var.set(printers[0])

    def _add_print_files(self):
        paths = filedialog.askopenfilenames(
            title="选择要打印的文件",
            filetypes=[("常用文档", "*.pdf *.doc *.docx *.xls *.xlsx *.ppt *.pptx"),
                       ("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"),
                       ("所有文件", "*.*")]
        )
        if paths:
            for p in paths:
                if p not in self.print_files:
                    self.print_files.append(p)
                    self.print_listbox.insert('end', os.path.basename(p))
            self._update_print_count()

    def _add_print_folder(self):
        folder = filedialog.askdirectory(title="选择文件夹")
        if folder:
            import glob
            extensions = ['*.pdf', '*.doc', '*.docx', '*.xls', '*.xlsx',
                          '*.ppt', '*.pptx', '*.jpg', '*.jpeg', '*.png',
                          '*.bmp', '*.gif', '*.tiff', '*.txt', '*.rtf']
            added = 0
            for ext in extensions:
                for p in sorted(glob.glob(os.path.join(folder, ext))):
                    if p not in self.print_files:
                        self.print_files.append(p)
                        self.print_listbox.insert('end', os.path.basename(p))
                        added += 1
            self._update_print_count()
            if added == 0:
                Messagebox.show_info("该文件夹下没有新的可打印文件", "提示")

    def _remove_selected_print(self):
        sel = list(self.print_listbox.curselection())
        sel.reverse()
        for i in sel:
            self.print_files.pop(i)
            self.print_listbox.delete(i)
        self._update_print_count()

    def _clear_print_files(self):
        self.print_files.clear()
        self.print_listbox.delete(0, 'end')
        self._update_print_count()

    def _update_print_count(self):
        n = len(self.print_files)
        self.print_count_lbl.config(text=f"共 {n} 个文件")

    def _do_print(self):
        if not self.print_files:
            Messagebox.show_warning("请先添加要打印的文件", "提示")
            return

        printer = self.printer_var.get()
        if not printer:
            Messagebox.show_warning("请选择打印机", "提示")
            return

        n = len(self.print_files)
        result = Messagebox.yesno(
            f"确认要打印 {n} 个文件吗？\n打印机：{printer}",
            "确认打印"
        )
        if not result:
            return

        # Windows: 保存默认打印机，切换到用户选择的，打印完恢复
        # Unix: lp -d 直接指定打印机，无需切换
        old_default = None
        printer_changed = False
        if sys.platform == 'win32':
            old_default = self._get_default_printer()
            if printer != old_default:
                printer_changed = self._set_default_printer(printer)
                if not printer_changed:
                    Messagebox.show_warning(f"无法切换到打印机：{printer}\n将使用当前默认打印机打印。", "提示")

        success, fail = 0, 0
        for file_path in self.print_files:
            if not os.path.isfile(file_path):
                fail += 1
                continue
            try:
                if sys.platform == 'win32':
                    os.startfile(file_path, "print")
                else:
                    subprocess.run(
                        ['lp', '-d', printer, file_path],
                        capture_output=True, text=True, timeout=60
                    )
                success += 1
            except Exception:
                fail += 1

        if printer_changed and old_default:
            self._set_default_printer(old_default)

        msg = f"已发送 {success} 个文件到打印机"
        if fail > 0:
            msg += f"\n{fail} 个文件打印失败（文件不存在或无法打开）"
        Messagebox.show_info(msg, "打印结果")

    # ==================== 通用方法 ====================
    def _browse_pdf(self, var, output_var=None, suffix='_out'):
        path = filedialog.askopenfilename(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if path:
            var.set(path)
            # 自动设置输出文件路径（同目录 + 后缀）
            if output_var is not None and not output_var.get():
                base, ext = os.path.splitext(path)
                output_var.set(f"{base}{suffix}{ext}")

    def _browse_save(self, var):
        path = filedialog.asksaveasfilename(
            title="保存PDF文件",
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf")]
        )
        if path:
            if not path.lower().endswith('.pdf'):
                path += '.pdf'
            var.set(path)

    def _check_input(self, input_var):
        if not input_var.get():
            Messagebox.show_warning("请选择PDF文件", "提示")
            return False
        if not os.path.isfile(input_var.get()):
            Messagebox.show_error(f"文件不存在：\n{input_var.get()}", "错误")
            return False
        if not os.path.isfile(self.qpdf_path):
            Messagebox.show_error(f"qpdf.exe 不存在：\n{self.qpdf_path}", "错误")
            return False
        return True

    def _check_input_output(self, input_var, output_var):
        if not input_var.get():
            Messagebox.show_warning("请选择输入PDF文件", "提示")
            return False
        if not output_var.get():
            Messagebox.show_warning("请指定输出PDF文件", "提示")
            return False
        if not os.path.isfile(input_var.get()):
            Messagebox.show_error(f"输入文件不存在：\n{input_var.get()}", "错误")
            return False
        if not os.path.isfile(self.qpdf_path):
            Messagebox.show_error(f"qpdf.exe 不存在：\n{self.qpdf_path}", "错误")
            return False
        return True

    def _run_cmd(self, cmd, success_msg):
        self.status_var.set("正在执行...")
        self.root.update()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                     creationflags=_NO_WINDOW)
            if result.returncode == 0:
                self.status_var.set(success_msg)
                Messagebox.show_info(success_msg, "成功", parent=self.root)
            else:
                self.status_var.set("执行失败")
                Messagebox.show_error(f"qpdf 执行失败：\n{result.stderr}", "失败", parent=self.root)
        except subprocess.TimeoutExpired:
            self.status_var.set("执行超时")
            Messagebox.show_error("qpdf 执行超时", "超时", parent=self.root)
        except Exception as e:
            self.status_var.set("执行异常")
            Messagebox.show_error(str(e), "异常", parent=self.root)

    def _run_show_cmd(self, cmd, text_widget):
        """执行命令并将结果显示在Text控件中"""
        self.status_var.set("正在查询...")
        self.root.update()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                     creationflags=_NO_WINDOW)
            info = result.stdout if result.stdout else result.stderr
            if not info:
                info = "无输出信息"
            text_widget.delete('1.0', 'end')
            text_widget.insert('1.0', info)
            self.status_var.set("查询完成")
        except subprocess.TimeoutExpired:
            self.status_var.set("查询超时")
            text_widget.delete('1.0', 'end')
            text_widget.insert('1.0', "查询超时")
        except Exception as e:
            self.status_var.set("查询异常")
            text_widget.delete('1.0', 'end')
            text_widget.insert('1.0', str(e))


if __name__ == '__main__':
    try:
        from ttkbootstrap import Window
    except ImportError:
        print('=' * 50)
        print('错误：未安装 ttkbootstrap 库！')
        print('请执行以下命令安装：')
        print('  pip install ttkbootstrap')
        print('=' * 50)
        input('按回车键退出...')
        sys.exit(1)

    try:
        root = Window(themename="cosmo", title="PDF工具箱", size=(780, 560),
                      resizable=(True, True))
        app = PdfToolApp(root)
        root.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("发生错误，按回车键退出...")
