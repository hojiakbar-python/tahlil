"""Run the classifier on the sample images and print a comparison table."""
from pathlib import Path

from PIL import Image

from xray_classifier import XRayClassifier, load_image

SAMPLES = {
    "Sogʻlom": "namunalar/soglom.png",
    "Pnevmoniya (kasal)": "namunalar/pnevmoniya.jpg",
    "Pnevmotoraks (kasal)": "namunalar/pnevmotoraks.jpg",
    "Tuberkulyoz (kasal)": "namunalar/tuberkulyoz.jpg",
}


def main() -> None:
    print("Model yuklanmoqda...")
    clf = XRayClassifier()
    clf.load()
    print("Model tayyor.\n")

    header = f"{'Namuna':<24} | {'TB %':>6} | {'Pnevm %':>8} | {'Pnvtks %':>9} | Xulosa"
    print(header)
    print("-" * len(header))

    for label, path in SAMPLES.items():
        if not Path(path).exists():
            print(f"{label:<24} | YOʻQ ({path})")
            continue
        img = load_image(path)
        pred = clf.predict(img, with_heatmap=False)
        tb = pred.tuberkulyoz * 100
        pn = pred.pnevmoniya * 100
        px = pred.pnevmotoraks * 100
        flags = []
        if pred.tuberkulyoz >= 0.5:
            flags.append("TB?")
        if pred.pnevmoniya >= 0.5:
            flags.append("Pnvm?")
        if pred.pnevmotoraks >= 0.5:
            flags.append("Pntx?")
        verdict = ", ".join(flags) if flags else "Belgi yo'q"
        print(f"{label:<24} | {tb:>6.1f} | {pn:>8.1f} | {px:>9.1f} | {verdict}")

    print("\nEslatma: TB qiymati 3 ta proksi belgi (Consolidation/Infiltration/Lung Opacity) o'rtachasi.")


if __name__ == "__main__":
    main()
