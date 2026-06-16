#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 将qpdf和PDF工具箱打包成单个可执行文件

特性:
  - 自动检测本地 qpdf，支持缓存，避免重复下载
  - 首次运行自动下载 qpdf 和字体（缓存到本地，后续秒打包）
  - 支持 GitHub Actions CI/CD
  - 无需手动修改脚本即可在不同机器上使用

使用方法:
  1. 安装依赖:  pip install pyinstaller
  2. 运行打包:  python build_exe.py
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

# ==================== 配置 ====================

QPDF_VERSION = os.environ.get("QPDF_VERSION", "12.3.2")
QPDF_DIR_ENV = os.environ.get("QPDF_DIR", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(BASE_DIR, "pdf_toolbox.py")
FA_TTF = os.path.join(BASE_DIR, "fa-solid-900.ttf")
OUTPUT_NAME = "PDF_Toolbox"

# 缓存目录（下载的 qpdf 解压后放这里，后续直接复用）
CACHE_DIR = os.path.join(BASE_DIR, "qpdf_cache")
# 打包时用于临时存放 bin 的目录（避免复整个 qpdf 导致路径过长）
TEMP_QPDF_DIR = os.path.join(BASE_DIR, "qpdf_temp")

# 常见 qpdf 安装路径（按优先级，带 %s 的会被替换为版本号）
DEFAULT_SEARCH_PATHS = [
    r"C:\Program Files\qpdf %s\bin\qpdf.exe",
    r"C:\Program Files\qpdf\bin\qpdf.exe",
    r"C:\qpdf-%s-msvc64\bin\qpdf.exe",
    r"D:\qpdf-%s-msvc64\bin\qpdf.exe",
    # 自动扫描脚本所在目录的上一级（方便本项目的目录结构）
    lambda: os.path.join(
        os.path.dirname(BASE_DIR), f"qpdf-{QPDF_VERSION}-msvc64", "bin", "qpdf.exe"
    ),
    # 也扫描一下 BASE_DIR 本身
    lambda: os.path.join(BASE_DIR, f"qpdf-{QPDF_VERSION}-msvc64", "bin", "qpdf.exe"),
]

# GitHub Release 下载地址
QPDF_DOWNLOAD_URL = (
    "https://github.com/qpdf/qpdf/releases/download/v{version}/"
    "qpdf-{version}-msvc64.zip"
)

FONT_DOWNLOAD_URL = (
    "https://raw.githubusercontent.com/FortAwesome/"
    "Font-Awesome/6.x/webfonts/fa-solid-900.ttf"
)


# ==================== 工具函数 ====================

def log(msg):
    print(f"[build_exe] {msg}")


def find_qpdf():
    """查找已安装的 qpdf.exe，返回路径或 None"""
    if QPDF_DIR_ENV:
        path = os.path.join(QPDF_DIR_ENV, "bin", "qpdf.exe")
        if os.path.isfile(path):
            log(f"找到 qpdf (来自环境变量): {path}")
            return path
        log(f"环境变量 QPDF_DIR 指向的路径无效: {path}")

    # 搜索常见安装路径
    for entry in DEFAULT_SEARCH_PATHS:
        if callable(entry):
            path = entry()
            if os.path.isfile(path):
                log(f"找到 qpdf (自动扫描): {path}")
                return path
            continue
        # 带 %s 的路径：先替换版本号，再试空版本
        if "%s" in entry:
            path = entry % QPDF_VERSION
            if os.path.isfile(path):
                log(f"找到 qpdf (默认路径): {path}")
                return path
            path = entry % ""
            path = path.replace("  ", " ").strip()
            if os.path.isfile(path):
                log(f"找到 qpdf (默认路径): {path}")
                return path
        else:
            if os.path.isfile(entry):
                log(f"找到 qpdf (默认路径): {entry}")
                return entry

    return None


def find_cached_qpdf():
    """在缓存目录中查找已下载的 qpdf，返回 bin 目录路径或 None"""
    pattern = os.path.join(CACHE_DIR, f"qpdf-{QPDF_VERSION}-msvc64", "bin", "qpdf.exe")
    if os.path.isfile(pattern):
        log(f"找到缓存的 qpdf: {pattern}")
        return pattern
    # 也直接搜 CACHE_DIR/**/qpdf.exe
    for f in glob.glob(os.path.join(CACHE_DIR, "**", "qpdf.exe"), recursive=True):
        log(f"找到缓存的 qpdf: {f}")
        return f
    return None


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


def download_and_cache_qpdf():
    """下载 qpdf 并缓存到本地"""
    cache_subdir = os.path.join(CACHE_DIR, f"qpdf-{QPDF_VERSION}-msvc64")
    qpdf_exe = os.path.join(cache_subdir, "bin", "qpdf.exe")
    if os.path.isfile(qpdf_exe):
        log("qpdf 已缓存，跳过下载")
        return cache_subdir

    zip_path = os.path.join(CACHE_DIR, f"qpdf-{QPDF_VERSION}-msvc64.zip")
    url = QPDF_DOWNLOAD_URL.format(version=QPDF_VERSION)

    if not download_file(url, zip_path, f"qpdf v{QPDF_VERSION}"):
        log("下载失败，尝试从国内镜像下载...")
        # 可配置国内镜像源
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

    # 解压
    log("正在解压...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(cache_subdir)
        # 如果解压后多一层目录，调整一下
        items = os.listdir(cache_subdir)
        if len(items) == 1 and os.path.isdir(os.path.join(cache_subdir, items[0])):
            inner = os.path.join(cache_subdir, items[0])
            for item in os.listdir(inner):
                shutil.move(os.path.join(inner, item), os.path.join(cache_subdir, item))
            os.rmdir(inner)
    except Exception as e:
        log(f"解压失败: {e}")
        shutil.rmtree(cache_subdir, ignore_errors=True)
        return None
    finally:
        os.remove(zip_path)

    if os.path.isfile(qpdf_exe):
        log(f"qpdf 已缓存到: {cache_subdir}")
        return cache_subdir
    else:
        log("解压后未找到 qpdf.exe，缓存可能不完整")
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
    # 清理之前的临时 qpdf
    if os.path.exists(TEMP_QPDF_DIR):
        shutil.rmtree(TEMP_QPDF_DIR)

    # 获取 qpdf bin 目录
    qpdf_bin_dir = None

    qpdf_exe = find_qpdf()
    if qpdf_exe:
        qpdf_bin_dir = os.path.dirname(qpdf_exe)
    else:
        qpdf_exe = find_cached_qpdf()
        if qpdf_exe:
            qpdf_bin_dir = os.path.dirname(qpdf_exe)
        else:
            log("未找到本地 qpdf，正在下载并缓存...")
            cache_dir = download_and_cache_qpdf()
            if cache_dir:
                qpdf_bin_dir = os.path.join(cache_dir, "bin")

    if not qpdf_bin_dir or not os.path.isdir(qpdf_bin_dir):
        log("错误: 无法获取 qpdf，打包终止")
        sys.exit(1)

    log(f"使用 qpdf 目录: {qpdf_bin_dir}")

    # 复制 bin 目录到临时位置（避免路径过长）
    log(f"正在复制 qpdf bin: {qpdf_bin_dir} -> {TEMP_QPDF_DIR}")
    shutil.copytree(qpdf_bin_dir, TEMP_QPDF_DIR)

    # 构建 PyInstaller 命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--name", OUTPUT_NAME,
        "--add-data", f"{TEMP_QPDF_DIR};qpdf",
        "--hidden-import", "ttkbootstrap",
        "--hidden-import", "PIL",
        "--collect-all", "ttkbootstrap",
    ]

    # 如果有字体文件，打包进去
    if os.path.isfile(FA_TTF):
        cmd.extend(["--add-data", f"{FA_TTF};."])

    cmd.append(SCRIPT)

    log(f"正在打包: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    # 清理临时 qpdf
    if os.path.exists(TEMP_QPDF_DIR):
        shutil.rmtree(TEMP_QPDF_DIR)

    if result.returncode == 0:
        log(f"\n打包成功！可执行文件在: dist/{OUTPUT_NAME}/{OUTPUT_NAME}.exe")
        log("可将 dist/PDF_Toolbox 整个文件夹分发给其他人使用")
    else:
        log("\n打包失败，请检查错误信息")
        sys.exit(1)


def main():
    no_pause = "--no-pause" in sys.argv

    log("=" * 50)
    log(f"PDF工具箱 打包脚本 (qpdf v{QPDF_VERSION})")
    log(f"系统: {platform.system()} {platform.release()}")
    log("=" * 50)

    # 确保字体
    ensure_font()

    # 执行打包
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
