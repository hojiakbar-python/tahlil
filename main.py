"""Tahlil — Oʻpka rentgen tasvirini tahlil qilish dasturi."""
from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False
    TkinterDnD = None  # type: ignore

import database
import pdf_report
from history_window import HistoryWindow
from xray_classifier import XRayClassifier, load_image, overlay_heatmap

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DEFAULT_THRESHOLD = 0.5
MIN_THRESHOLD = 0.30
MAX_THRESHOLD = 0.70
PDF_OUTPUT_DIR = Path(__file__).parent / "hisobotlar"


class _Root(ctk.CTk, TkinterDnD.DnDWrapper if DND_AVAILABLE else object):  # type: ignore
    def __init__(self) -> None:
        super().__init__()
        if DND_AVAILABLE:
            self.TkdndVersion = TkinterDnD._require(self)  # type: ignore[attr-defined]


class TahlilApp(_Root):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tahlil — Oʻpka rentgen tahlili")
        self.geometry("1180x760")
        self.minsize(1050, 700)

        database.init_db()
        PDF_OUTPUT_DIR.mkdir(exist_ok=True)

        self.classifier = XRayClassifier()
        self.current_image_path: Path | None = None
        self.current_image: Image.Image | None = None
        self.current_prediction = None
        self.current_heatmap_image: Image.Image | None = None
        self.last_record_id: int | None = None
        self.show_heatmap = ctk.BooleanVar(value=True)
        self.threshold = ctk.DoubleVar(value=DEFAULT_THRESHOLD)

        self._build_ui()
        self._load_model_async()

    # ----- UI -----
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            self,
            text="Oʻpka rentgen tasvirini tahlil qilish",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 5), sticky="w")

        # ---- LEFT: image area ----
        self.image_frame = ctk.CTkFrame(self)
        self.image_frame.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="nsew")
        self.image_frame.grid_rowconfigure(1, weight=1)
        self.image_frame.grid_columnconfigure(0, weight=1)

        top_row = ctk.CTkFrame(self.image_frame, fg_color="transparent")
        top_row.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        top_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top_row, text="Rentgen tasviri", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w")
        self.heatmap_switch = ctk.CTkSwitch(
            top_row, text="Issiqlik xaritasi", variable=self.show_heatmap, command=self._refresh_image
        )
        self.heatmap_switch.grid(row=0, column=1, sticky="e")

        placeholder = "Rasm tanlanmagan"
        if DND_AVAILABLE:
            placeholder += "\n(rasmni shu yerga sudrab tashlang yoki tugma orqali tanlang)"
        self.image_label = ctk.CTkLabel(
            self.image_frame,
            text=placeholder,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            fg_color=("#e0e0e0", "#1f1f1f"),
        )
        self.image_label.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        if DND_AVAILABLE:
            self.image_label.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
            self.image_label.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore[attr-defined]

        # ---- RIGHT: patient info + results ----
        right = ctk.CTkFrame(self)
        right.grid(row=1, column=1, padx=(10, 20), pady=10, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        # Patient info
        info = ctk.CTkFrame(right)
        info.grid(row=0, column=0, padx=15, pady=(15, 8), sticky="ew")
        info.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(info, text="Bemor maʼlumotlari", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=10, pady=(10, 8), sticky="w"
        )

        self.patient_name = ctk.StringVar()
        self.patient_age = ctk.StringVar()
        self.patient_gender = ctk.StringVar(value="—")
        self.doctor_name = ctk.StringVar()

        fields = [
            ("Ismi:", self.patient_name, "entry"),
            ("Yoshi:", self.patient_age, "entry"),
            ("Jinsi:", self.patient_gender, "combo"),
            ("Shifokor:", self.doctor_name, "entry"),
        ]
        for i, (label, var, kind) in enumerate(fields, start=1):
            ctk.CTkLabel(info, text=label).grid(row=i, column=0, padx=10, pady=4, sticky="e")
            if kind == "entry":
                ctk.CTkEntry(info, textvariable=var).grid(row=i, column=1, padx=10, pady=4, sticky="ew")
            else:
                ctk.CTkOptionMenu(info, variable=var, values=["—", "Erkak", "Ayol"]).grid(
                    row=i, column=1, padx=10, pady=4, sticky="ew"
                )

        # Results
        ctk.CTkLabel(right, text="Tahlil natijasi", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=1, column=0, padx=25, pady=(10, 5), sticky="w"
        )

        results = ctk.CTkFrame(right)
        results.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="nsew")
        results.grid_columnconfigure(0, weight=1)

        self.disease_rows: dict[str, tuple[ctk.CTkProgressBar, ctk.CTkLabel]] = {}
        diseases = ["Oʻpka tuberkulyozi", "Oʻpka pnevmoniyasi", "Oʻpka pnevmotoraksi"]
        for i, name in enumerate(diseases):
            row = ctk.CTkFrame(results, fg_color="transparent")
            row.grid(row=i, column=0, padx=15, pady=8, sticky="ew")
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=name, font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="w")
            pct_label = ctk.CTkLabel(row, text="—", font=ctk.CTkFont(size=13))
            pct_label.grid(row=0, column=1, sticky="e")
            bar = ctk.CTkProgressBar(row, height=12)
            bar.set(0)
            bar.grid(row=1, column=0, columnspan=2, pady=(4, 0), sticky="ew")
            self.disease_rows[name] = (bar, pct_label)

        # Threshold slider
        thr_row = ctk.CTkFrame(results, fg_color="transparent")
        thr_row.grid(row=len(diseases), column=0, padx=15, pady=(8, 0), sticky="ew")
        thr_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(thr_row, text="Sezgirlik chegarasi:", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
        self.threshold_value_label = ctk.CTkLabel(
            thr_row, text=f"{DEFAULT_THRESHOLD * 100:.0f}%", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.threshold_value_label.grid(row=0, column=2, sticky="e")
        self.threshold_slider = ctk.CTkSlider(
            thr_row,
            from_=MIN_THRESHOLD,
            to=MAX_THRESHOLD,
            variable=self.threshold,
            number_of_steps=int((MAX_THRESHOLD - MIN_THRESHOLD) * 100),
            command=self._on_threshold_change,
        )
        self.threshold_slider.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 0))

        self.verdict_label = ctk.CTkLabel(
            results,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            wraplength=380,
            justify="left",
        )
        self.verdict_label.grid(row=len(diseases) + 1, column=0, padx=15, pady=(12, 10), sticky="w")

        # ---- BOTTOM: controls ----
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="ew")
        controls.grid_columnconfigure(5, weight=1)

        self.select_btn = ctk.CTkButton(controls, text="Rasm tanlash", command=self.on_select)
        self.select_btn.grid(row=0, column=0, padx=(0, 8))

        self.analyze_btn = ctk.CTkButton(controls, text="Tahlil qilish", command=self.on_analyze, state="disabled")
        self.analyze_btn.grid(row=0, column=1, padx=8)

        self.pdf_btn = ctk.CTkButton(controls, text="PDF saqlash", command=self.on_save_pdf, state="disabled")
        self.pdf_btn.grid(row=0, column=2, padx=8)

        self.history_btn = ctk.CTkButton(controls, text="Tarix", command=self.on_history)
        self.history_btn.grid(row=0, column=3, padx=8)

        self.clear_btn = ctk.CTkButton(controls, text="Tozalash", command=self.on_clear, fg_color="#555", hover_color="#444")
        self.clear_btn.grid(row=0, column=4, padx=8)

        self.status_label = ctk.CTkLabel(controls, text="Model yuklanmoqda…", anchor="e")
        self.status_label.grid(row=0, column=5, sticky="e", padx=10)

    # ----- model loading -----
    def _load_model_async(self) -> None:
        def worker() -> None:
            try:
                self.classifier.load()
                self.after(0, lambda: self.status_label.configure(text="Tayyor"))
                self.after(0, self._refresh_analyze_state)
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Xato", f"Modelni yuklab boʻlmadi:\n{exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_analyze_state(self) -> None:
        ready = self.current_image is not None and self.status_label.cget("text") == "Tayyor"
        self.analyze_btn.configure(state="normal" if ready else "disabled")

    # ----- image selection -----
    def on_select(self) -> None:
        path = filedialog.askopenfilename(
            title="Rentgen rasmni tanlang",
            filetypes=[("Rasmlar", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"), ("Barchasi", "*.*")],
        )
        if path:
            self._load_path(path)

    def _on_drop(self, event) -> None:
        raw = event.data.strip()
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        path = raw.split("} {")[0].strip("{}")
        if path:
            self._load_path(path)

    def _load_path(self, path: str) -> None:
        try:
            img = Image.open(path).convert("RGB")
        except Exception as exc:
            messagebox.showerror("Xato", f"Rasmni ochib boʻlmadi:\n{exc}")
            return
        self.current_image_path = Path(path)
        self.current_image = img
        self.current_prediction = None
        self.current_heatmap_image = None
        self.last_record_id = None
        self.pdf_btn.configure(state="disabled")
        self.verdict_label.configure(text="")
        for bar, pct in self.disease_rows.values():
            bar.set(0)
            pct.configure(text="—")
        self._refresh_image()
        self._refresh_analyze_state()

    def _refresh_image(self) -> None:
        if self.current_image is None:
            return
        if self.show_heatmap.get() and self.current_heatmap_image is not None:
            display = self.current_heatmap_image
        else:
            display = self.current_image
        preview = display.copy()
        preview.thumbnail((620, 620))
        self.preview_imgtk = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
        self.image_label.configure(image=self.preview_imgtk, text="")

    # ----- analysis -----
    def on_analyze(self) -> None:
        if self.current_image is None:
            return
        self.analyze_btn.configure(state="disabled")
        self.status_label.configure(text="Tahlil qilinmoqda…")

        img = self.current_image

        def worker() -> None:
            try:
                pred = self.classifier.predict(img, with_heatmap=True)
                self.after(0, lambda: self._show_result(pred))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Xato", f"Tahlil davomida xato:\n{exc}"))
            finally:
                self.after(0, lambda: self.status_label.configure(text="Tayyor"))
                self.after(0, self._refresh_analyze_state)

        threading.Thread(target=worker, daemon=True).start()

    def _show_result(self, pred) -> None:
        self.current_prediction = pred
        scores = pred.as_dict()
        for name, value in scores.items():
            bar, pct = self.disease_rows[name]
            bar.set(min(max(value, 0.0), 1.0))
            pct.configure(text=f"{value * 100:.1f}%")
        self._update_verdict()
        if pred.heatmap is not None and self.current_image is not None:
            try:
                self.current_heatmap_image = overlay_heatmap(self.current_image, pred.heatmap)
            except Exception:
                self.current_heatmap_image = None
        self._refresh_image()
        self.pdf_btn.configure(state="normal")
        self._save_to_history(self.verdict_label.cget("text"))

    def _update_verdict(self) -> None:
        if self.current_prediction is None:
            return
        thr = self.threshold.get()
        positives = [name for name, value in self.current_prediction.as_dict().items() if value >= thr]
        if positives:
            text = (
                f"Ehtimoliy belgilar aniqlandi (chegara {thr * 100:.0f}%): "
                + ", ".join(positives)
                + ".\nEslatma: bu dastur dastlabki tahlil uchun, yakuniy tashxis shifokor tomonidan qoʻyiladi."
            )
            self.verdict_label.configure(text=text, text_color="#ff7a59")
        else:
            text = (
                f"Berilgan kasalliklar boʻyicha jiddiy belgilar topilmadi (chegara {thr * 100:.0f}%).\n"
                "Eslatma: bu dastur dastlabki tahlil uchun, yakuniy tashxis shifokor tomonidan qoʻyiladi."
            )
            self.verdict_label.configure(text=text, text_color="#5cd6a0")

    def _on_threshold_change(self, value: float) -> None:
        self.threshold_value_label.configure(text=f"{float(value) * 100:.0f}%")
        self._update_verdict()

    # ----- history & pdf -----
    def _save_to_history(self, xulosa: str) -> None:
        if self.current_prediction is None or self.current_image_path is None:
            return
        rec_id = database.insert_record(
            bemor_ismi=self.patient_name.get().strip(),
            yosh=self.patient_age.get().strip(),
            jinsi=self.patient_gender.get(),
            shifokor=self.doctor_name.get().strip(),
            rasm_yoli=str(self.current_image_path),
            tb=self.current_prediction.tuberkulyoz,
            pnevmoniya=self.current_prediction.pnevmoniya,
            pnevmotoraks=self.current_prediction.pnevmotoraks,
            xulosa=xulosa,
        )
        self.last_record_id = rec_id

    def on_save_pdf(self) -> None:
        if self.current_prediction is None or self.current_image is None:
            return
        default_name = pdf_report.default_filename(self.patient_name.get())
        target = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=default_name,
            initialdir=str(PDF_OUTPUT_DIR),
            filetypes=[("PDF fayl", "*.pdf")],
        )
        if not target:
            return
        try:
            pdf_report.build_report(
                output_path=target,
                bemor_ismi=self.patient_name.get().strip(),
                yosh=self.patient_age.get().strip(),
                jinsi=self.patient_gender.get(),
                shifokor=self.doctor_name.get().strip(),
                sana=datetime.now().strftime("%Y-%m-%d %H:%M"),
                scores=self.current_prediction.as_dict(),
                xulosa=self.verdict_label.cget("text"),
                original_image=self.current_image,
                heatmap_image=self.current_heatmap_image,
            )
        except Exception as exc:
            messagebox.showerror("Xato", f"PDF yaratib boʻlmadi:\n{exc}")
            return
        if self.last_record_id is not None:
            database.update_pdf_path(self.last_record_id, target)
        messagebox.showinfo("Saqlandi", f"PDF saqlandi:\n{target}")

    def on_history(self) -> None:
        HistoryWindow(self)

    def on_clear(self) -> None:
        self.current_image_path = None
        self.current_image = None
        self.current_prediction = None
        self.current_heatmap_image = None
        self.last_record_id = None
        self.patient_name.set("")
        self.patient_age.set("")
        self.patient_gender.set("—")
        self.doctor_name.set("")
        self.verdict_label.configure(text="")
        for bar, pct in self.disease_rows.values():
            bar.set(0)
            pct.configure(text="—")
        self.image_label.configure(image=None, text="Rasm tanlanmagan")
        self.pdf_btn.configure(state="disabled")
        self._refresh_analyze_state()


def main() -> None:
    app = TahlilApp()
    app.mainloop()


if __name__ == "__main__":
    main()
