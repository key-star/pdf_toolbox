# PDF工具箱

Cross-platform (Windows/macOS/Linux) Python/tkinter GUI wrapping **qpdf** for PDF operations.

## Key files

| File | Purpose |
|------|---------|
| `pdf_toolbox.py` | Main application (all logic) |
| `pdf_toolbox.pyw` | Windows-only copy for windowed mode (no console) |
| `build_exe.py` | PyInstaller build script (cross-platform) |
| `fa-solid-900.ttf` | Font Awesome icon font (bundled) |

## Dependencies

- `ttkbootstrap` (tkinter Material Design theme) — `pip install ttkbootstrap`
- `qpdf` — install per platform:
  - Windows: `build_exe.py` auto-downloads and caches
  - macOS: `brew install qpdf`
  - UOS/Debian: `sudo apt install qpdf`
- Font Awesome icons from `fa-solid-900.ttf` (falls back to system Segoe/MDL2 or Canvas-drawn icons)

## Platform adaptation

- Fonts: `UI_FONT` / `UI_FONT_FIXED` per platform (`Microsoft YaHei UI`, `PingFang SC`, `Noto Sans CJK SC`)
- Printing: Windows uses `os.startfile(file, "print")` + Win32 printer APIs; macOS/Linux uses `lp` / `lpstat`
- `subprocess.CREATE_NO_WINDOW` used only on Windows (`_NO_WINDOW`)
- qpdf binary name: `qpdf.exe` on Windows, `qpdf` on Unix (`QPDF_EXE`)

## qpdf path resolution

1. PyInstaller-frozen: `{exe_dir}/qpdf/`, `{exe_dir}/_internal/qpdf/`, `{MEIPASS}/qpdf/`
2. Adjacent project dirs: `../qpdf-12.3.2-msvc64/bin/`, `../qpdf-12.3.2-linux-x86_64/bin/`
3. System paths: Program Files (Windows), Homebrew (macOS), `/usr/bin` (Linux)
4. `qpdf_cache/` (from `build_exe.py` download)
5. `shutil.which('qpdf')` — PATH fallback

## Architecture

- Single class `PdfToolApp` managing all state as instance attributes
- Pages created via builder pattern in `_create_pages()`, shown/hidden via `pack`/`pack_forget`
- All PDF operations invoke `qpdf` via `subprocess.run` (120s timeout, 30s for queries)
- Page deletion uses qpdf's `r{pages}` exclude syntax (e.g. `r2,r4-6`)
- Window geometry saved to `{APPDATA,~/.config,~/Library}/PDF工具箱/config.json`
- Icon font priority: Font Awesome > Segoe Fluent Icons (Windows only) > MDL2 Assets > Canvas fallback
