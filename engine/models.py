"""
Model data untuk DSS Calculator Engine.
Mendefinisikan dataclass: Criterion, Problem, SAWResult, WPResult.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import numpy as np

from config import BENEFIT, COST


@dataclass
class Criterion:
    """Representasi satu kriteria dalam masalah MADM."""
    kode: str
    nama: str
    tipe: str  # "Benefit" atau "Cost"
    bobot_input: float
    alasan: str = ""

    def __post_init__(self) -> None:
        if self.tipe not in (BENEFIT, COST):
            raise ValueError(f"Tipe kriteria harus '{BENEFIT}' atau '{COST}', bukan '{self.tipe}'")
        if self.bobot_input < 0:
            raise ValueError(f"Bobot input tidak boleh negatif: {self.bobot_input}")


@dataclass
class Problem:
    """
    Representasi lengkap masalah pengambilan keputusan MADM.
    
    Attributes
    ----------
    nama_kasus : str
        Nama/judul kasus pengambilan keputusan.
    alternatif : list[str]
        Daftar nama alternatif (harus unik).
    kriteria : list[Criterion]
        Daftar kriteria beserta bobot dan tipe.
    matriks : pd.DataFrame
        Matriks keputusan (index=alternatif, columns=kode kriteria).
    pengambil_keputusan : str
        Nama pengambil keputusan (opsional, untuk laporan).
    tujuan : str
        Tujuan pengambilan keputusan (opsional).
    sumber_data : str
        Sumber data (opsional).
    """
    nama_kasus: str
    alternatif: list[str]
    kriteria: list[Criterion]
    matriks: pd.DataFrame
    pengambil_keputusan: str = ""
    tujuan: str = ""
    sumber_data: str = ""

    @property
    def bobot_input(self) -> np.ndarray:
        """Array bobot input dari semua kriteria."""
        return np.array([k.bobot_input for k in self.kriteria])

    @property
    def bobot_ternormalisasi(self) -> np.ndarray:
        """Array bobot ternormalisasi: w_j = bobot_input_j / sum(bobot_input)."""
        b = self.bobot_input
        total = b.sum()
        if total == 0:
            raise ValueError("Total bobot input = 0; tidak dapat menormalisasi.")
        return b / total

    @property
    def kode_kriteria(self) -> list[str]:
        """Daftar kode kriteria."""
        return [k.kode for k in self.kriteria]

    @property
    def tipe_kriteria(self) -> list[str]:
        """Daftar tipe kriteria."""
        return [k.tipe for k in self.kriteria]


@dataclass
class AdjustedCell:
    """Informasi sel yang disesuaikan pada WP (nilai <= 0 diganti)."""
    alternatif: str
    kriteria: str
    nilai_asli: float
    nilai_baru: float


@dataclass
class SAWResult:
    """
    Hasil lengkap perhitungan SAW beserta semua langkah antara.
    
    Attributes
    ----------
    problem : Problem
        Masalah yang dihitung.
    bobot : np.ndarray
        Bobot ternormalisasi.
    pembagi : pd.Series
        Nilai pembagi normalisasi (max untuk Benefit, min untuk Cost).
    matriks_r : pd.DataFrame
        Matriks ternormalisasi R.
    matriks_wr : pd.DataFrame
        Matriks kontribusi w*r per sel.
    v : pd.Series
        Skor preferensi V per alternatif.
    peringkat : pd.Series
        Peringkat per alternatif (1 = terbaik).
    peringatan : list[str]
        Daftar peringatan (jika ada).
    """
    problem: Problem
    bobot: np.ndarray
    pembagi: pd.Series
    matriks_r: pd.DataFrame
    matriks_wr: pd.DataFrame
    v: pd.Series
    peringkat: pd.Series
    peringatan: list[str] = field(default_factory=list)


@dataclass
class WPResult:
    """
    Hasil lengkap perhitungan WP beserta semua langkah antara.
    
    Attributes
    ----------
    problem : Problem
        Masalah yang dihitung.
    bobot : np.ndarray
        Bobot ternormalisasi.
    pangkat : np.ndarray
        Pangkat per kriteria (+w untuk Benefit, -w untuk Cost).
    matriks_adjusted : pd.DataFrame
        Matriks setelah penggantian nilai <= 0.
    sel_disesuaikan : list[AdjustedCell]
        Daftar sel yang nilainya diganti.
    matriks_xpangkat : pd.DataFrame
        Rincian x_ij^pangkat_j per sel.
    s : pd.Series
        Vektor S (produk x^pangkat).
    v : pd.Series
        Vektor V = S / sum(S).
    peringkat : pd.Series
        Peringkat per alternatif.
    peringatan : list[str]
        Daftar peringatan.
    """
    problem: Problem
    bobot: np.ndarray
    pangkat: np.ndarray
    matriks_adjusted: pd.DataFrame
    sel_disesuaikan: list[AdjustedCell]
    matriks_xpangkat: pd.DataFrame
    s: pd.Series
    v: pd.Series
    peringkat: pd.Series
    peringatan: list[str] = field(default_factory=list)
