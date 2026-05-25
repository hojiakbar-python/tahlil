# Tahlil — Oʻpka rentgen tahlili

Desktop ilova. Oʻpka rentgen tasvirini yuklab, quyidagi 3 kasallik boʻyicha ehtimollikni hisoblaydi:

1. **Oʻpka tuberkulyozi**
2. **Oʻpka pnevmoniyasi**
3. **Oʻpka pnevmotoraksi**

> Bu dastur faqat **dastlabki yordamchi tahlil** uchun moʻljallangan. Yakuniy tashxis shifokor tomonidan qoʻyiladi.

## Texnologiya

- **UI:** Python + [customtkinter](https://github.com/TomSchimansky/CustomTkinter)
- **Model:** [TorchXRayVision](https://github.com/mlmed/torchxrayvision) — DenseNet121 (`densenet121-res224-all`) — pretrained chest X-ray classifier
- **Paketlash:** PyInstaller

## Ishga tushirish (dev rejimida)

```bash
cd /home/kali/Desktop/tahlil
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Birinchi marta ishga tushirilganda model fayllari (~80 MB) avtomatik yuklab olinadi.

## `.exe` fayl yasash (Windows)

Windows kompyuterda:

```powershell
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --name tahlil --onefile --windowed ^
    --collect-all torchxrayvision ^
    --collect-all customtkinter ^
    --collect-submodules transformers ^
    main.py
```

Natija: `dist\tahlil.exe`

> **Eslatma:** Linuxda PyInstaller faqat Linux uchun binar yasaydi. `.exe` faylini yasash uchun Windows kompyuter yoki Wine kerak.

## Linux binar yasash

```bash
chmod +x build.sh
./build.sh
```

Natija: `dist/tahlil`

## Cheklovlar

- Model `pneumonia` va `pneumothorax` sinflarini toʻgʻridan-toʻgʻri qoʻllab-quvvatlaydi.
- Tuberkulyoz uchun `Consolidation`, `Infiltration`, `Lung Opacity` belgilari asosida proksi baho beriladi (chunki NIH datasetida toʻgʻridan-toʻgʻri TB klassi yoʻq). Aniqroq natija uchun keyinchalik maxsus TB modelini qoʻshish mumkin.
- Threshold (chegara): 0.5. Bundan yuqori qiymat — ijobiy belgi sifatida koʻrsatiladi.
