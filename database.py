"""SQLite-backed history of analyses."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "tahlil_tarix.db"


@dataclass
class HistoryRow:
    id: int
    sana: str
    bemor_ismi: str
    yosh: str
    jinsi: str
    shifokor: str
    rasm_yoli: str
    tb: float
    pnevmoniya: float
    pnevmotoraks: float
    xulosa: str
    pdf_yoli: str


def init_db(path: Path = DB_PATH) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tahlillar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sana TEXT NOT NULL,
                bemor_ismi TEXT,
                yosh TEXT,
                jinsi TEXT,
                shifokor TEXT,
                rasm_yoli TEXT,
                tb REAL,
                pnevmoniya REAL,
                pnevmotoraks REAL,
                xulosa TEXT,
                pdf_yoli TEXT
            )
            """
        )
        conn.commit()


def insert_record(
    *,
    bemor_ismi: str,
    yosh: str,
    jinsi: str,
    shifokor: str,
    rasm_yoli: str,
    tb: float,
    pnevmoniya: float,
    pnevmotoraks: float,
    xulosa: str,
    pdf_yoli: str = "",
    path: Path = DB_PATH,
) -> int:
    sana = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(path) as conn:
        cur = conn.execute(
            """
            INSERT INTO tahlillar
            (sana, bemor_ismi, yosh, jinsi, shifokor, rasm_yoli,
             tb, pnevmoniya, pnevmotoraks, xulosa, pdf_yoli)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sana, bemor_ismi, yosh, jinsi, shifokor, rasm_yoli,
             tb, pnevmoniya, pnevmotoraks, xulosa, pdf_yoli),
        )
        conn.commit()
        return cur.lastrowid


def update_pdf_path(record_id: int, pdf_yoli: str, path: Path = DB_PATH) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE tahlillar SET pdf_yoli = ? WHERE id = ?", (pdf_yoli, record_id))
        conn.commit()


def fetch_all(search: str = "", path: Path = DB_PATH) -> list[HistoryRow]:
    query = "SELECT id, sana, bemor_ismi, yosh, jinsi, shifokor, rasm_yoli, tb, pnevmoniya, pnevmotoraks, xulosa, pdf_yoli FROM tahlillar"
    args: tuple = ()
    if search:
        query += " WHERE bemor_ismi LIKE ? OR shifokor LIKE ?"
        wildcard = f"%{search}%"
        args = (wildcard, wildcard)
    query += " ORDER BY id DESC"
    with sqlite3.connect(path) as conn:
        rows = conn.execute(query, args).fetchall()
    return [HistoryRow(*r) for r in rows]


def delete_record(record_id: int, path: Path = DB_PATH) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM tahlillar WHERE id = ?", (record_id,))
        conn.commit()
