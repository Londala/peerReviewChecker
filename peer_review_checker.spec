import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
IS_MAC = sys.platform == "darwin"

datas = collect_data_files("customtkinter")

a = Analysis(
    ["gui.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if IS_MAC:
    # macOS: onedir exe + .app bundle (onefile + .app is unsupported)
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="PeerReviewChecker",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="PeerReviewChecker",
    )
    app = BUNDLE(
        coll,
        name="PeerReviewChecker.app",
        icon=None,
        bundle_identifier="com.peerreviewchecker",
    )
else:
    # Windows / Linux: single-file executable
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="PeerReviewChecker",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
