#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 将qpdf和PDF工具箱打包成单个可执行文件
支持 Windows / macOS / Linux

特性:
  - 自动检测本地 qpdf，支持缓存，避免重复下载
  - 首次运行自动下载 qpdf 和字体（缓存到本地，后续秒打包）
  - 支持 GitHub Actions CI/CD
  - 无需手动修改脚本即可在不同机器上使用

使用方法:
  1. 安装依赖:  pip install pyinstaller
   2. 运行打包:  python build.py
  3. 打包结果在 dist/ 目录

环境变量:
  QPDF_DIR     - 指定 qpdf 安装目录（如 C:\\qpdf-12.3.2-msvc64）
                 不设置则自动查找缓存或下载
  QPDF_VERSION - qpdf 版本号（默认 12.3.2）
"""

import os
import sys
import shutil
import subprocess
import urllib.request
import platform
import zipfile
import glob

# ==================== 平台检测 ====================

SYSTEM = platform.system()  # Windows / Darwin / Linux
MACHINE = platform.machine().lower()  # AMD64 / arm64 / x86_64

IS_WIN = SYSTEM == 'Windows'
IS_MAC = SYSTEM == 'Darwin'
IS_LINUX = SYSTEM == 'Linux'

if IS_WIN:
    QPDF_BIN = 'qpdf.exe'
    ADD_DATA_SEP = ';'
    QPDF_ARCHIVE = 'qpdf-{version}-msvc64.zip'
    QPDF_DIR_NAME = 'qpdf-{version}-msvc64'
elif IS_MAC:
    QPDF_BIN = 'qpdf'
    ADD_DATA_SEP = ':'
    QPDF_ARCHIVE = None  # macOS 无预编译二进制，使用 Homebrew
    QPDF_DIR_NAME = 'qpdf-{version}'
else:  # Linux
    QPDF_BIN = 'qpdf'
    ADD_DATA_SEP = ':'
    QPDF_ARCHIVE = 'qpdf-{version}-bin-linux-x86_64.zip'
    QPDF_DIR_NAME = 'qpdf-{version}-linux-x86_64'

# ==================== 配置 ====================

QPDF_VERSION = os.environ.get("QPDF_VERSION", "12.3.2")
QPDF_DIR_ENV = os.environ.get("QPDF_DIR", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(BASE_DIR, "pdf_toolbox.py")
FA_TTF = os.path.join(BASE_DIR, "fa-solid-900.ttf")
OUTPUT_NAME = "PDF_Toolbox"

CACHE_DIR = os.path.join(BASE_DIR, "qpdf_cache")
TEMP_QPDF_DIR = os.path.join(BASE_DIR, "qpdf_temp")

# GitHub Release 下载地址
QPDF_DOWNLOAD_URL = (
    "https://github.com/qpdf/qpdf/releases/download/v{version}/"
    "{archive}"
)

FONT_DOWNLOAD_URL = (
    "https://raw.githubusercontent.com/FortAwesome/"
    "Font-Awesome/6.x/webfonts/fa-solid-900.ttf"
)


def _qpdf_archive():
    """返回当前平台对应的 qpdf 压缩包文件名"""
    return QPDF_ARCHIVE.format(version=QPDF_VERSION) if QPDF_ARCHIVE else None


def _qpdf_dir_name():
    """返回当前平台对应的 qpdf 目录名"""
    return QPDF_DIR_NAME.format(version=QPDF_VERSION)


# ==================== 搜索路径（按平台） ====================

def _build_search_paths():
    """构建平台相关的 qpdf 搜索路径"""
    paths = []

    if IS_WIN:
        paths.extend([
            r"C:\Program Files\qpdf %s\bin\%s" % (QPDF_VERSION, QPDF_BIN),
            r"C:\Program Files\qpdf %s\bin\%s" % ("", QPDF_BIN),
            r"C:\Program Files\qpdf\bin\%s" % QPDF_BIN,
            r"C:\qpdf-%s-msvc64\bin\%s" % (QPDF_VERSION, QPDF_BIN),
            r"D:\qpdf-%s-msvc64\bin\%s" % (QPDF_VERSION, QPDF_BIN),
        ])
    elif IS_MAC:
        # Homebrew (Intel)
        paths.append("/usr/local/bin/%s" % QPDF_BIN)
        # Homebrew (Apple Silicon)
        paths.append("/opt/homebrew/bin/%s" % QPDF_BIN)
        # MacPorts
        paths.append("/opt/local/bin/%s" % QPDF_BIN)
    else:  # Linux
        paths.extend([
            "/usr/bin/%s" % QPDF_BIN,
            "/usr/local/bin/%s" % QPDF_BIN,
        ])

    # 通用：脚本上级目录 / 同级目录
    dir_name = _qpdf_dir_name()
    paths.append(lambda: os.path.join(os.path.dirname(BASE_DIR), dir_name, "bin", QPDF_BIN))
    paths.append(lambda: os.path.join(BASE_DIR, dir_name, "bin", QPDF_BIN))

    return paths


def _find_qpdf_bin_in_dir(root_dir):
    """在目录中递归查找 qpdf 可执行文件"""
    for f in glob.glob(os.path.join(root_dir, "**", QPDF_BIN), recursive=True):
        return f
    return None


# ==================== 工具函数 ====================

def log(msg):
    print(f"[build] {msg}")


def find_qpdf():
    """查找已安装的 qpdf，返回完整路径或 None"""
    if QPDF_DIR_ENV:
        path = os.path.join(QPDF_DIR_ENV, "bin", QPDF_BIN)
        if os.path.isfile(path):
            log(f"找到 qpdf (来自环境变量): {path}")
            return path
        log(f"环境变量 QPDF_DIR 指向的路径无效: {path}")

    for entry in _build_search_paths():
        if callable(entry):
            path = entry()
            if path and os.path.isfile(path):
                log(f"找到 qpdf (自动扫描): {path}")
                return path
        else:
            if os.path.isfile(entry):
                log(f"找到 qpdf (默认路径): {entry}")
                return entry

    return None


def find_cached_qpdf():
    """在缓存目录中查找 qpdf，返回完整路径或 None"""
    cache_dir = os.path.join(CACHE_DIR, _qpdf_dir_name(), "bin", QPDF_BIN)
    if os.path.isfile(cache_dir):
        log(f"找到缓存的 qpdf: {cache_dir}")
        return cache_dir
    # 递归搜索
    result = _find_qpdf_bin_in_dir(CACHE_DIR)
    if result:
        log(f"找到缓存的 qpdf: {result}")
    return result


def download_file(url, dest, desc="文件"):
    """下载文件到目标路径"""
    log(f"正在下载 {desc}...")
    log(f"  来源: {url}")
    log(f"  目标: {dest}")

    os.makedirs(os.path.dirname(dest), exist_ok=True)

    def report(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(100, int(downloaded * 100 / total_size))
            if pct % 10 == 0 or downloaded == total_size:
                print(f"\r  进度: {pct}% ({downloaded // 1024}KB / {total_size // 1024}KB)", end="")
        else:
            print(f"\r  已下载: {downloaded // 1024}KB", end="")

    try:
        urllib.request.urlretrieve(url, dest, report)
        print()
        log(f"下载完成: {dest}")
        return True
    except Exception as e:
        print()
        log(f"下载失败: {e}")
        return False


def extract_zip(zip_path, dest_dir):
    """解压 zip 文件并处理嵌套目录"""
    log("正在解压...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(dest_dir)
        # 如果解压后多一层目录，展平
        items = os.listdir(dest_dir)
        if len(items) == 1 and os.path.isdir(os.path.join(dest_dir, items[0])):
            inner = os.path.join(dest_dir, items[0])
            for item in os.listdir(inner):
                shutil.move(os.path.join(inner, item), os.path.join(dest_dir, item))
            os.rmdir(inner)
        return True
    except Exception as e:
        log(f"解压失败: {e}")
        return False


def download_and_cache_qpdf():
    """下载 qpdf 并缓存到本地（Windows/Linux）；macOS 需通过 Homebrew 安装）"""
    if IS_MAC:
        log("macOS 平台：请先通过 Homebrew 安装 qpdf")
        log("  brew install qpdf")
        log("或设置 QPDF_DIR 环境变量指向 qpdf 安装目录")
        return None

    cache_subdir = os.path.join(CACHE_DIR, _qpdf_dir_name())
    qpdf_path = os.path.join(cache_subdir, "bin", QPDF_BIN)
    if os.path.isfile(qpdf_path):
        log("qpdf 已缓存，跳过下载")
        return cache_subdir

    archive_name = _qpdf_archive()
    if not archive_name:
        return None

    zip_path = os.path.join(CACHE_DIR, archive_name)
    url = QPDF_DOWNLOAD_URL.format(version=QPDF_VERSION, archive=archive_name)

    if not download_file(url, zip_path, f"qpdf v{QPDF_VERSION} ({SYSTEM})"):
        log("下载失败，尝试使用国内镜像...")
        fallback_urls = [
            f"https://mirror.ghproxy.com/{url}",
        ]
        for fb_url in fallback_urls:
            if download_file(fb_url, zip_path, f"qpdf v{QPDF_VERSION} (镜像)"):
                break
        else:
            log("所有下载源均失败，请手动下载后解压到:")
            log(f"  {cache_subdir}")
            log("下载地址: " + url)
            return None

    if not extract_zip(zip_path, cache_subdir):
        shutil.rmtree(cache_subdir, ignore_errors=True)
        return None

    os.remove(zip_path)

    if os.path.isfile(qpdf_path):
        log(f"qpdf 已缓存到: {cache_subdir}")
        return cache_subdir
    else:
        log("解压后未找到 qpdf，缓存可能不完整")
        return None


def ensure_font():
    """确保字体文件存在，不存在则下载"""
    if os.path.isfile(FA_TTF):
        log(f"字体文件已存在: {FA_TTF}")
        return True
    log("Font Awesome 字体未找到，正在下载...")
    return download_file(FONT_DOWNLOAD_URL, FA_TTF, "fa-solid-900.ttf")


def build():
    """执行 PyInstaller 打包"""
    if os.path.exists(TEMP_QPDF_DIR):
        shutil.rmtree(TEMP_QPDF_DIR)

    # 获取 qpdf 路径
    qpdf_path = find_qpdf() or find_cached_qpdf()

    if not qpdf_path:
        log("未找到本地 qpdf，正在下载并缓存...")
        cache_dir = download_and_cache_qpdf()
        if cache_dir:
            qpdf_path = os.path.join(cache_dir, "bin", QPDF_BIN)

    if not qpdf_path or not os.path.isfile(qpdf_path):
        log("错误: 无法获取 qpdf，打包终止")
        sys.exit(1)

    log(f"使用 qpdf: {qpdf_path}")

    # 复制 qpdf bin/ 目录内容到临时位置（去掉 bin/ 层级）
    qpdf_root = os.path.dirname(os.path.dirname(qpdf_path))
    qpdf_bin = os.path.join(qpdf_root, 'bin')
    log(f"正在复制 qpdf: {qpdf_bin} -> {TEMP_QPDF_DIR}")
    shutil.copytree(qpdf_bin, TEMP_QPDF_DIR)

    # 构建 PyInstaller 命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--name", OUTPUT_NAME,
        "--add-data", f"{TEMP_QPDF_DIR}{ADD_DATA_SEP}qpdf",
        "--hidden-import", "ttkbootstrap",
        "--hidden-import", "PIL",
        "--collect-all", "ttkbootstrap",
    ]

    if os.path.isfile(FA_TTF):
        cmd.extend(["--add-data", f"{FA_TTF}{ADD_DATA_SEP}."])

    cmd.append(SCRIPT)

    log(f"正在打包: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if os.path.exists(TEMP_QPDF_DIR):
        shutil.rmtree(TEMP_QPDF_DIR)

    if result.returncode == 0:
        if IS_WIN:
            log(f"\n打包成功！可执行文件在: dist/{OUTPUT_NAME}/{OUTPUT_NAME}.exe")
        elif IS_MAC:
            log(f"\n打包成功！应用在: dist/{OUTPUT_NAME}.app/")
            log("或 one-folder 模式: dist/PDF_Toolbox/")
        else:
            log(f"\n打包成功！可执行文件在: dist/{OUTPUT_NAME}/{OUTPUT_NAME}")
        log("可将输出目录分发给其他人使用")
    else:
        log("\n打包失败，请检查错误信息")
        sys.exit(1)


def main():
    no_pause = "--no-pause" in sys.argv

    log("=" * 50)
    log(f"PDF工具箱 打包脚本 (qpdf v{QPDF_VERSION})")
    log(f"系统: {SYSTEM} {platform.machine()} {platform.release()}")
    log("=" * 50)

    ensure_font()
    build()

    if not no_pause:
        input("按回车退出...")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        if "--no-pause" not in sys.argv:
            input("发生错误，按回车退出...")
