"""
Engine WP (Weighted Product) untuk DSS Calculator.
Semua fungsi bersifat murni (pure) dan tidak mengimpor streamlit.
"""
from __future__ import annotations

from typing import Literal
import numpy as np
import pandas as pd

from config import BENEFIT, COST, DEFAULT_REPLACEMENT_VALUE
from engine.models import Problem, WPResult, AdjustedCell


ZeroHandling = Literal["ganti", "geser", "tolak"]


def _sesuaikan_matriks(
    matriks: pd.DataFrame,
    kode: list[str],
    strategi: ZeroHandling,
    nilai_pengganti: float,
    peringatan: list[str],
) -> tuple[pd.DataFrame, list[AdjustedCell]]:
    """
    Tangani nilai <= 0 pada matriks untuk metode WP.

    Parameters
    ----------
    matriks : pd.DataFrame
        Matriks keputusan asli.
    kode : list[str]
        Kode kolom kriteria.
    strategi : str
        'ganti': ganti nilai <= 0 dengan nilai_pengganti.
        'geser': geser seluruh kolom agar min = nilai_pengganti.
        'tolak': lempar ValueError jika ada nilai <= 0.
    nilai_pengganti : float
        Nilai pengganti untuk nilai <= 0 (default 0.01).
    peringatan : list[str]
        Daftar yang diisi dengan peringatan.

    Returns
    -------
    (pd.DataFrame, list[AdjustedCell])
        Matriks yang sudah disesuaikan dan daftar sel yang diubah.
    """
    adj = matriks.copy().astype(float)
    sel_disesuaikan: list[AdjustedCell] = []

    for col in kode:
        mask_nonpos = adj[col] <= 0
        if not mask_nonpos.any():
            continue

        if strategi == "tolak":
            nilai_buruk = adj[col][mask_nonpos].to_dict()
            raise ValueError(
                f"Kolom '{col}' memiliki nilai ≤ 0: {nilai_buruk}. "
                f"Metode WP tidak dapat dijalankan. Ubah data atau pilih strategi 'ganti'/'geser'."
            )

        elif strategi == "ganti":
            for idx in adj.index[mask_nonpos]:
                nilai_asli = float(adj.loc[idx, col])
                adj.loc[idx, col] = nilai_pengganti
                sel_disesuaikan.append(AdjustedCell(
                    alternatif=str(idx),
                    kriteria=col,
                    nilai_asli=nilai_asli,
                    nilai_baru=nilai_pengganti,
                ))
            peringatan.append(
                f"⚠️ Kolom '{col}': {mask_nonpos.sum()} nilai ≤ 0 diganti dengan {nilai_pengganti}. "
                f"Penggantian ini SANGAT memengaruhi hasil WP — alternatif dengan nilai yang diganti "
                f"mendapat S yang sangat kecil (hampir nol dalam perbandingan)."
            )

        elif strategi == "geser":
            min_val = float(adj[col].min())
            geser = nilai_pengganti - min_val
            nilai_asli_dict = adj[col][mask_nonpos].to_dict()
            adj[col] = adj[col] + geser
            for idx, nilai_asli in nilai_asli_dict.items():
                sel_disesuaikan.append(AdjustedCell(
                    alternatif=str(idx),
                    kriteria=col,
                    nilai_asli=nilai_asli,
                    nilai_baru=float(adj.loc[idx, col]),
                ))
            peringatan.append(
                f"⚠️ Kolom '{col}': seluruh kolom digeser +{geser:.4f} agar minimum = {nilai_pengganti}. "
                f"Pergeseran mengubah selisih relatif antar alternatif; interpretasikan dengan hati-hati."
            )

    return adj, sel_disesuaikan


def hitung_wp(
    problem: Problem,
    strategi_zero: ZeroHandling = "ganti",
    nilai_pengganti: float = DEFAULT_REPLACEMENT_VALUE,
) -> WPResult:
    """
    Hitung WP (Weighted Product) untuk masalah MADM.

    Rumus:
    - Pangkat: Benefit → +w_j; Cost → -w_j
    - S_i = ∏_j x_ij^(pangkat_j)  [dihitung di log-space untuk stabilitas]
    - V_i = S_i / Σ S

    Parameters
    ----------
    problem : Problem
        Masalah MADM.
    strategi_zero : str
        Cara menangani nilai <= 0: 'ganti', 'geser', atau 'tolak'.
    nilai_pengganti : float
        Nilai pengganti untuk strategi 'ganti' (default 0.01).

    Returns
    -------
    WPResult
        Hasil lengkap WP beserta semua langkah antara.
    """
    peringatan: list[str] = []
    bobot = problem.bobot_ternormalisasi
    kode = problem.kode_kriteria
    tipe = problem.tipe_kriteria
    matriks_raw = problem.matriks[kode].copy().astype(float)

    # Pangkat: +w untuk Benefit, -w untuk Cost
    pangkat = np.array([
        bobot[i] if tipe[i] == BENEFIT else -bobot[i]
        for i in range(len(kode))
    ])

    # Sesuaikan nilai <= 0
    matriks_adj, sel_disesuaikan = _sesuaikan_matriks(
        matriks_raw, kode, strategi_zero, nilai_pengganti, peringatan
    )

    # Hitung x_ij^pangkat_j per sel (untuk tampilan rinci)
    xpangkat_dict: dict[str, pd.Series] = {}
    for i, col in enumerate(kode):
        xpangkat_dict[col] = matriks_adj[col].apply(lambda x, p=pangkat[i]: x ** p)
    matriks_xpangkat = pd.DataFrame(xpangkat_dict, index=matriks_adj.index)

    # Hitung S_i di log-space untuk stabilitas numerik
    # S_i = exp(Σ_j pangkat_j * ln(x_ij_adj))
    log_matriks = np.log(matriks_adj.values)  # shape: (n_alt, n_crit)
    log_s = log_matriks.dot(pangkat)          # shape: (n_alt,)
    s_values = np.exp(log_s)

    s = pd.Series(s_values, index=matriks_adj.index, name="S")

    # Hitung V = S / sum(S)
    total_s = s.sum()
    if total_s == 0:
        peringatan.append(
            "Total Σ S = 0; tidak dapat menghitung V. Periksa data dan strategi penanganan nilai ≤ 0."
        )
        v = pd.Series(0.0, index=s.index, name="V")
    else:
        v = s / total_s
        v.name = "V"

    # Peringkat
    peringkat = v.rank(ascending=False, method="min").astype(int)
    peringkat.name = "Peringkat"

    return WPResult(
        problem=problem,
        bobot=bobot,
        pangkat=pangkat,
        matriks_adjusted=matriks_adj,
        sel_disesuaikan=sel_disesuaikan,
        matriks_xpangkat=matriks_xpangkat,
        s=s,
        v=v,
        peringkat=peringkat,
        peringatan=peringatan,
    )
