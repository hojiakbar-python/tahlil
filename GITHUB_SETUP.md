# GitHub Actions orqali Windows `.exe` yasash

GitHub Actions har push'da Windows runner ishga tushirib, `tahlil.exe` faylini yasab beradi. Bepul (oylik 2000 daqiqa public repo uchun).

## 1-qadam: Loyihani GitHub'ga yuklash

```bash
cd /home/kali/Desktop/tahlil

# Git init
git init
git add .
git commit -m "Tahlil — oʻpka rentgen tahlili dasturi"

# GitHub'da yangi repo yarating (https://github.com/new), masalan: tahlil
# Soʻngra push:
git branch -M main
git remote add origin https://github.com/SIZNING_USERNAMINGIZ/tahlil.git
git push -u origin main
```

## 2-qadam: Workflow avtomatik ishga tushadi

`git push` qilishingiz bilan GitHub Actions avtomatik ishga tushadi:

1. **github.com/USERNAME/tahlil/actions** sahifasiga oʻting
2. **"Build Windows EXE"** workflow'i ishga tushganini koʻrasiz
3. **5–15 daqiqa** kutiladi (torch katta — birinchi build sekinroq)
4. Yashil ✓ chiqsa — tayyor

## 3-qadam: `.exe` faylini yuklab olish

1. Tugagan workflow ustiga bosing
2. Pastda **"Artifacts"** boʻlimi
3. **`tahlil-windows-exe`** ni yuklab oling (ZIP)
4. ZIP'dan `tahlil.exe` chiqaring

## Release yaratish (ixtiyoriy)

Versiya tag bilan push qilsangiz, avtomatik GitHub Release yaratiladi va `.exe` unga biriktiriladi:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Soʻngra: `github.com/USERNAME/tahlil/releases` sahifasidan yuklab olish mumkin.

## Workflow nima qiladi?

`.github/workflows/build-windows.yml`:

1. Windows runner'da Python 3.11 oʻrnatadi
2. `requirements.txt`'dan barcha kutubxonalarni oʻrnatadi
3. PyInstaller bilan `--onefile --windowed` qoʻyilgan `.exe` yasaydi
4. Keraksiz paketlarni (matplotlib, pandas, IPython, ...) chiqarib tashlaydi — hajm kichikroq
5. Tayyor `.exe`ni Artifacts'ga yuklaydi

## Kutilayotgan hajm

`tahlil.exe` taxminan **400–800 MB** boʻladi (torch katta).

## Muammolar

### Workflow ishga tushmadi
- `.github/workflows/build-windows.yml` repo'da bormi tekshiring
- Actions yoqilganligini tekshiring: Settings → Actions → General → "Allow all actions"

### Build muvaffaqiyatsiz
- Logs'ga qarang. Odatda paket versiyalarida muammo boʻladi
- `requirements.txt`'da versiyalarni qatʼiy belgilash mumkin (`==` bilan)

### `.exe` ishlamayapti
- Birinchi ishga tushirilganda Windows Defender tekshirishi mumkin
- Antivirus PyInstaller-binar'larini koʻpincha "shubhali" deb baholaydi (false positive) — ishonchli signature kerak boʻlsa, kelajakda code-signing qoʻshish mumkin
