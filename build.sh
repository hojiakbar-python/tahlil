#!/usr/bin/env bash
# Tahlil dasturini bitta executable faylga paketlash uchun skript.
# Linux uchun ELF binar, Windows uchun .exe yaratish uchun Windowsda yoki Wine ostida ishga tushiring.
set -e

pyinstaller \
    --name tahlil \
    --onefile \
    --windowed \
    --collect-all torchxrayvision \
    --collect-all customtkinter \
    --collect-submodules transformers \
    main.py

echo "Tayyor: dist/tahlil (yoki Windowsda dist/tahlil.exe)"
