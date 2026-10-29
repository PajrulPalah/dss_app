"""
Engine SAW (Simple Additive Weighting) untuk DSS Calculator.
Semua fungsi bersifat murni (pure) dan tidak mengimpor streamlit.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import BENEFIT, COST
from engine.models import Problem, SAWResult


def _normalisasi_kolom(
    kolom: pd.Series,
    tipe: str,
    peringatan: list[str],
    nama_kolom: str,
) -> tuple[pd.Series, float]:
    """
    Normalisasi satu kolom berdasarkan tipe kriteria.
    
    Parameters
    ----------
    kolom : pd.Series
        Nilai satu kolom kriteria.
    tipe : str
        'Benefit' atau 'Cost'.
    peringatan : list[str]
        Daftar yang diisi jika ada peringatan.
    nama_kolom : str
        Nama kolom untuk pesan peringatan.

    Returns
    -------
    (pd.Series, float)
        Kolom ternormalisasi dan nilai pembagi.
    """
    if tipe == BENEFIT:
        pembagi = float(kolom.max())
        if pembagi <= 0:
            peringatan.append(
                f"Kriteria '{nama_kolom}' (Benefit) memiliki nilai maksimum = {pembagi:.4f} ≤ 0. "
                f"Normalisasi tidak dapat dilakukan secara bermakna. "
                f"Pertimbangkan mengeliminasi kriteria ini atau mengubah data."
            )
            if pembagi == 0:
                return pd.Series(0.0, index=kolom.index), 0.0
        return kolom / pembagi, pembagi

    else:  # COST
        pembagi = float(kolom.min())
        if pembagi == 0:
            peringatan.append(
                f"Kriteria '{nama_kolom}' (Cost) memiliki nilai minimum = 0. "
                f"Pembagian nol tidak dapat dilakukan. "
                f"Sel dengan nilai 0 akan menghasilkan NaN dan diberi nilai 0. "
                f"Pertimbangkan menggunakan nilai pengganti kecil (mis. 0,01)."
            )
            # Hindari pembagian nol: di mana kolom == 0, set r = 0
            r = kolom.copy().astype(float)
            mask_nol = kolom == 0
            r[~mask_nol] = pembagi / kolom[~mask_nol]
            r[mask_nol] = 0.0
            return r, pembagi
        elif pembagi < 0:
            peringatan.append(
                f"Kriteria '{nama_kolom}' (Cost) memiliki nilai minimum = {pembagi:.4f} < 0. "
                f"Normalisasi Cost dengan nilai negatif mungkin tidak bermakna. "
                f"Hasilnya ditampilkan, namun interpretasi harus hati-hati."
            )
        return pembagi / kolom, pembagi


def hitung_saw(problem: Problem) -> SAWResult:
    """
    Hitung SAW (Simple Additive Weighting) untuk masalah MADM.

    Rumus:
    - Benefit: r_ij = x_ij / max_j(x)
    - Cost   : r_ij = min_j(x) / x_ij
    - V_i    = Σ_j (w_j * r_ij)

    Parameters
    ----------
    problem : Problem
        Masalah MADM dengan alternatif, kriteria, dan matriks keputusan.

    Returns
    -------
    SAWResult
        Hasil lengkap SAW beserta semua langkah antara.
    """
    peringatan: list[str] = []
    bobot = problem.bobot_ternormalisasi
    kode = problem.kode_kriteria
    tipe = problem.tipe_kriteria
    matriks = problem.matriks[kode].copy().astype(float)

    # Periksa kolom konstan
    for i, col in enumerate(kode):
        if matriks[col].nunique() <= 1:
            peringatan.append(
                f"Kolom '{col}' bernilai konstan ({matriks[col].iloc[0]:.4f}). "
                f"Normalisasi SAW menghasilkan 1 untuk semua alternatif pada kriteria ini."
            )

    # Normalisasi kolom per kolom
    pembagi_dict: dict[str, float] = {}
    r_dict: dict[str, pd.Series] = {}

    for i, col in enumerate(kode):
        r_col, pembagi = _normalisasi_kolom(matriks[col], tipe[i], peringatan, col)
        pembagi_dict[col] = pembagi
        r_dict[col] = r_col

    pembagi_series = pd.Series(pembagi_dict, name="Pembagi")
    matriks_r = pd.DataFrame(r_dict, index=matriks.index)

    # Matriks kontribusi w * r
    matriks_wr = matriks_r.multiply(bobot, axis="columns")
    matriks_wr.columns = kode

    # Skor V
    v = matriks_wr.sum(axis=1)
    v.name = "V"

    # Peringkat (tie = metode 'min')
    peringkat = v.rank(ascending=False, method="min").astype(int)
    peringkat.name = "Peringkat"

    return SAWResult(
        problem=problem,
        bobot=bobot,
        pembagi=pembagi_series,
        matriks_r=matriks_r,
        matriks_wr=matriks_wr,
        v=v,
        peringkat=peringkat,
        peringatan=peringatan,
    )
