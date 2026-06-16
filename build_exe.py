#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 将qpdf和pdf_rotate_tool打包成单个可执行文件
在Windows上运行此脚本即可

使用方法:
1. 先安装PyInstaller:  pip install pyinstaller
2. 运行此脚本:         python build_exe.py
3. 打包结果在 dist/ 目录下
"""

import os
import shutil
import subprocess
import sys

# 配置 - qpdf安装路径
QPDF_DIR = r"D:\qpdf-12.3.2-msvc64"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(BASE_DIR, "pdf_rotate_tool.py")
FA_TTF = os.path.join(BASE_DIR, "fa-solid-900.ttf")
OUTPUT_NAME = "PDF工具箱"

def main():
    # 检查qpdf目录
    if not os.path.isdir(QPDF_DIR):
        print(f"错误: qpdf目录不存在: {QPDF_DIR}")
        print("请修改脚本中的 QPDF_DIR 变量为实际的qpdf安装路径")
        input("按回车退出...")
        return

    # 检查qpdf.exe是否存在
    qpdf_exe = os.path.join(QPDF_DIR, "bin", "qpdf.exe")
    if not os.path.isfile(qpdf_exe):
        print(f"错误: 找不到qpdf.exe: {qpdf_exe}")
        input("按回车退出...")
        return

    # 检查PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("正在安装 PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller",
                        "-i", "https://yumserver.dahuatech.com/pypi/simple/",
                        "--trusted-host", "yumserver.dahuatech.com"], check=True)

    # 只复制bin目录到临时位置（避免复制整个qpdf目录导致无限递归或路径过长）
    temp_qpdf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qpdf_temp")
    if os.path.exists(temp_qpdf):
        shutil.rmtree(temp_qpdf)

    qpdf_bin = os.path.join(QPDF_DIR, "bin")
    print(f"正在复制qpdf bin: {qpdf_bin} -> {temp_qpdf}")
    shutil.copytree(qpdf_bin, temp_qpdf)

    # 检查Font Awesome字体文件
    if not os.path.isfile(FA_TTF):
        print(f"警告: Font Awesome字体文件不存在: {FA_TTF}")
        print("图标将使用系统字体或Canvas手绘模式")

    # 用PyInstaller打包
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--windowed",                          # 无命令行窗口
        "--name", OUTPUT_NAME,
        "--add-data", f"{temp_qpdf};qpdf",     # 将qpdf目录打包进去
        "--add-data", f"{FA_TTF};.",           # Font Awesome图标字体
        "--hidden-import", "ttkbootstrap",     # ttkbootstrap主题库
        "--hidden-import", "PIL",              # pillow图像库
        "--collect-all", "ttkbootstrap",       # 收集ttkbootstrap所有主题文件
        SCRIPT
    ]

    print(f"正在打包: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    # 清理临时qpdf
    if os.path.exists(temp_qpdf):
        shutil.rmtree(temp_qpdf)

    if result.returncode == 0:
        print(f"\n打包成功！可执行文件在: dist/{OUTPUT_NAME}/{OUTPUT_NAME}.exe")
        print(f"可以将 dist/{OUTPUT_NAME} 整个文件夹分发给其他人使用")
    else:
        print("\n打包失败，请检查错误信息")

    input("按回车退出...")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("发生错误，按回车退出...")
