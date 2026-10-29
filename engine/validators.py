"""
Validasi input untuk DSS Calculator Engine.
Semua fungsi mengembalikan daftar pesan error/warning berbahasa Indonesia.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Optional

from config import BENEFIT, COST, MIN_CRITERIA, MAX_CRITERIA, MIN_ALTERNATIVES


def validasi_kriteria(kriteria_list: list) -> list[str]:
    """
    Validasi daftar kriteria.
    
    Returns
    -------
    list[str]
        Daftar pesan error (kosong = valid).
    """
    errors: list[str] = []
    if len(kriteria_list) < MIN_CRITERIA:
        errors.append(f"Minimal {MIN_CRITERIA} kriteria diperlukan. Saat ini: {len(kriteria_list)}.")
    if len(kriteria_list) > MAX_CRITERIA:
        errors.append(f"Maksimal {MAX_CRITERIA} kriteria diizinkan. Saat ini: {len(kriteria_list)}.")
    
    kode_list = [k.kode for k in kriteria_list]
    if len(set(kode_list)) < len(kode_list):
        errors.append("Kode kriteria harus unik. Terdapat duplikat.")
    
    for k in kriteria_list:
        if k.bobot_input <= 0:
            errors.append(f"Bobot kriteria '{k.kode}' harus > 0. Diterima: {k.bobot_input}.")
        if k.tipe not in (BENEFIT, COST):
            errors.append(f"Tipe kriteria '{k.kode}' harus 'Benefit' atau 'Cost'. Diterima: {k.tipe}.")
    return errors


def validasi_alternatif(alternatif: list[str]) -> list[str]:
    """Validasi daftar nama alternatif."""
    errors: list[str] = []
    if len(alternatif) < MIN_ALTERNATIVES:
        errors.append(f"Minimal {MIN_ALTERNATIVES} alternatif diperlukan. Saat ini: {len(alternatif)}.")
    if len(set(alternatif)) < len(alternatif):
        errors.append("Nama alternatif harus unik. Terdapat duplikat.")
    for a in alternatif:
        if not str(a).strip():
            errors.append("Nama alternatif tidak boleh kosong.")
    return errors


def validasi_matriks(matriks: pd.DataFrame, alternatif: list[str], kode_kriteria: list[str]) -> list[str]:
    """Validasi matriks keputusan: kelengkapan, tipe numerik, konsistensi dimensi."""
    errors: list[str] = []
    
    if matriks.isnull().any().any():
        sel_kosong = []
        for col in matriks.columns:
            for idx in matriks.index[matriks[col].isnull()]:
                sel_kosong.append(f"({idx}, {col})")
        errors.append(f"Terdapat {matriks.isnull().sum().sum()} nilai kosong: {', '.join(sel_kosong[:5])}{'...' if len(sel_kosong) > 5 else ''}.")
    
    for col in matriks.columns:
        if not pd.api.types.is_numeric_dtype(matriks[col]):
            errors.append(f"Kolom '{col}' mengandung nilai non-numerik.")
    
    return errors


def periksa_nilai_wp(matriks: pd.DataFrame, tipe_kriteria: list[str], kode_kriteria: list[str]) -> list[str]:
    """
    Periksa nilai <= 0 pada matriks untuk metode WP.
    
    Returns
    -------
    list[str]
        Daftar peringatan (bukan error keras; pengguna bisa memilih penanganan).
    """
    warnings: list[str] = []
    for i, col in enumerate(kode_kriteria):
        if col not in matriks.columns:
            continue
        non_pos = matriks[col][matriks[col] <= 0]
        if len(non_pos) > 0:
            sel = [f"{idx}" for idx in non_pos.index]
            warnings.append(
                f"Kolom '{col}' memiliki nilai ≤ 0 pada alternatif: {', '.join(sel)}. "
                f"Metode WP memerlukan nilai positif."
            )
    return warnings


def periksa_kolom_konstan(matriks: pd.DataFrame, kode_kriteria: list[str]) -> list[str]:
    """Periksa kolom yang semua nilainya sama (akan menghasilkan normalisasi SAW = 1 semua)."""
    warnings: list[str] = []
    for col in kode_kriteria:
        if col not in matriks.columns:
            continue
        if matriks[col].nunique() == 1:
            warnings.append(
                f"Kolom '{col}' memiliki nilai yang sama untuk semua alternatif "
                f"(= {matriks[col].iloc[0]}). Kriteria ini tidak membedakan alternatif."
            )
    return warnings


def periksa_outlier(matriks: pd.DataFrame, kode_kriteria: list[str], faktor: float = 10.0) -> list[str]:
    """Deteksi outlier kasar: nilai > faktor * median."""
    warnings: list[str] = []
    for col in kode_kriteria:
        if col not in matriks.columns:
            continue
        med = matriks[col].abs().median()
        if med == 0:
            continue
        ekstrim = matriks[col][matriks[col].abs() > faktor * med]
        if len(ekstrim) > 0:
            warnings.append(
                f"Kolom '{col}' mungkin mengandung outlier: "
                f"{', '.join([f'{idx}={v:.2f}' for idx, v in ekstrim.items()])}."
            )
    return warnings
