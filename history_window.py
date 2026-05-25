"""Top-level window for browsing past analyses."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tkinter import messagebox, ttk

import customtkinter as ctk

import database


def _open_file(path: str) -> None:
    if not path or not Path(path).exists():
        messagebox.showwarning("Yo'q", "Fayl topilmadi.")
        return
    if sys.platform.startswith("linux"):
        subprocess.Popen(["xdg-open", path])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]


class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, master) -> None:
        super().__init__(master)
        self.title("Tahlillar tarixi")
        self.geometry("1000x600")
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="Qidiruv (bemor / shifokor):").grid(row=0, column=0, padx=(10, 5), pady=10)
        self.search_var = ctk.StringVar()
        entry = ctk.CTkEntry(top, textvariable=self.search_var, placeholder_text="ism kiriting...")
        entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        entry.bind("<Return>", lambda _e: self.refresh())

        ctk.CTkButton(top, text="Qidirish", command=self.refresh, width=100).grid(row=0, column=2, padx=5)
        ctk.CTkButton(top, text="Yangilash", command=lambda: (self.search_var.set(""), self.refresh()), width=100).grid(row=0, column=3, padx=5)

        # Use ttk.Treeview inside a frame (customtkinter has no native table)
        table_frame = ctk.CTkFrame(self)
        table_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "sana", "bemor", "yosh", "jinsi", "shifokor", "tb", "pnevmoniya", "pnevmotoraks")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=20)
        headings = {
            "id": "ID",
            "sana": "Sana",
            "bemor": "Bemor",
            "yosh": "Yosh",
            "jinsi": "Jinsi",
            "shifokor": "Shifokor",
            "tb": "TB %",
            "pnevmoniya": "Pnevmoniya %",
            "pnevmotoraks": "Pnevmotoraks %",
        }
        widths = {"id": 50, "sana": 140, "bemor": 180, "yosh": 60, "jinsi": 80, "shifokor": 140, "tb": 70, "pnevmoniya": 110, "pnevmotoraks": 120}
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")

        # Bottom buttons
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        ctk.CTkButton(btns, text="Rasmni ochish", command=self._open_image).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="PDF ochish", command=self._open_pdf).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="O'chirish", command=self._delete, fg_color="#aa3333", hover_color="#882222").pack(side="left", padx=5)
        ctk.CTkButton(btns, text="Yopish", command=self.destroy).pack(side="right", padx=5)

        self.refresh()

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = database.fetch_all(self.search_var.get().strip())
        for r in rows:
            self.tree.insert(
                "",
                "end",
                values=(
                    r.id,
                    r.sana,
                    r.bemor_ismi,
                    r.yosh,
                    r.jinsi,
                    r.shifokor,
                    f"{r.tb * 100:.1f}",
                    f"{r.pnevmoniya * 100:.1f}",
                    f"{r.pnevmotoraks * 100:.1f}",
                ),
            )

    def _selected_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Tanlang", "Avval jadvaldan yozuvni tanlang.")
            return None
        return int(self.tree.item(sel[0], "values")[0])

    def _selected_row(self):
        rid = self._selected_id()
        if rid is None:
            return None
        for r in database.fetch_all():
            if r.id == rid:
                return r
        return None

    def _open_image(self) -> None:
        r = self._selected_row()
        if r:
            _open_file(r.rasm_yoli)

    def _open_pdf(self) -> None:
        r = self._selected_row()
        if r:
            _open_file(r.pdf_yoli)

    def _delete(self) -> None:
        rid = self._selected_id()
        if rid is None:
            return
        if messagebox.askyesno("Tasdiqlash", f"#{rid} yozuvni o'chirishni xohlaysizmi?"):
            database.delete_record(rid)
            self.refresh()
