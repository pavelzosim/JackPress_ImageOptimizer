# -*- mode: python -*-
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

a = Analysis(
    ['main.py', 'gui_pics_rc.py'],  # Добавлен ресурсный файл
    pathex=[],
    binaries=[],
    datas=[
        ('tools/*.exe', 'tools'),
        ('images/*.ico', 'images'),    # Добавьте иконки
        ('images/*.png', 'images'),    # Добавьте изображения
        ('ui_mainwindow.py', '.')
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
        'PIL',
        'PyQt5.sip'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

# Добавьте это для ресурсов PyQt
a.datas += collect_data_files('PyQt5', True)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='JackPress2000',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    onefile=True,
    icon='images/app_icon.ico'  # Исправленный путь к иконке
)