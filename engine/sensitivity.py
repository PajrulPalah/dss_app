"""
Engine Sensitivitas untuk DSS Calculator.
Analisis sensitivitas: skenario bobot, one-at-a-time sweep, Monte Carlo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import pandas as pd

from config import DEFAULT_MONTE_CARLO_ITERATIONS, DEFAULT_SENSITIVITY_STEP
from engine.models import Problem, Criterion
from engine.saw import hitung_saw
from engine.wp import hitung_wp, ZeroHandling


@dataclass
class SkenarioBobot:
    """Satu skenario bobot untuk analisis sensitivitas."""
    nama: str
    bobot_input: list[float]  # sesuai urutan kriteria problem


@dataclass
class HasilSkenario:
    """Hasil satu skenario pada SAW dan/atau WP."""
    nama_skenario: str
    bobot_ternormalisasi: np.ndarray
    v_saw: Optional[pd.Series] = None
    peringkat_saw: Optional[pd.Series] = None
    v_wp: Optional[pd.Series] = None
    peringkat_wp: Optional[pd.Series] = None


@dataclass
class HasilSensitivitas:
    """Hasil analisis sensitivitas lengkap."""
    skenario: list[HasilSkenario] = field(default_factory=list)
    sweep_kriteria: Optional[str] = None
    sweep_df_saw: Optional[pd.DataFrame] = None  # index=w_k, columns=alternatif
    sweep_df_wp: Optional[pd.DataFrame] = None
    rankflip_saw: Optional[list[float]] = None   # titik w_k di mana rank-1 berubah
    rankflip_wp: Optional[list[float]] = None
    mc_pct_rank1: Optional[pd.DataFrame] = None  # index=alternatif
    mc_avg_rank: Optional[pd.DataFrame] = None


def _buat_problem_skenario(problem: Problem, bobot_input_baru: list[float]) -> Problem:
    """Buat problem baru dengan bobot yang diganti (kriteria lain tetap)."""
    kriteria_baru = [
        Criterion(
            kode=k.kode,
            nama=k.nama,
            tipe=k.tipe,
            bobot_input=bobot_input_baru[i],
            alasan=k.alasan,
        )
        for i, k in enumerate(problem.kriteria)
    ]
    return Problem(
        nama_kasus=problem.nama_kasus,
        alternatif=problem.alternatif,
        kriteria=kriteria_baru,
        matriks=problem.matriks,
        pengambil_keputusan=problem.pengambil_keputusan,
        tujuan=problem.tujuan,
        sumber_data=problem.sumber_data,
    )


def analisis_skenario(
    problem: Problem,
    skenario_list: list[SkenarioBobot],
    hitung_saw_flag: bool = True,
    hitung_wp_flag: bool = True,
    strategi_zero: ZeroHandling = "ganti",
    nilai_pengganti: float = 0.01,
) -> list[HasilSkenario]:
    """
    Hitung SAW dan/atau WP untuk setiap skenario bobot.

    Parameters
    ----------
    problem : Problem
        Masalah dasar.
    skenario_list : list[SkenarioBobot]
        Daftar skenario bobot.
    hitung_saw_flag : bool
        Apakah menghitung SAW.
    hitung_wp_flag : bool
        Apakah menghitung WP.
    strategi_zero : str
        Strategi penanganan nilai <= 0 untuk WP.
    nilai_pengganti : float
        Nilai pengganti untuk WP.

    Returns
    -------
    list[HasilSkenario]
        Daftar hasil per skenario.
    """
    hasil_list: list[HasilSkenario] = []
    for sk in skenario_list:
        p = _buat_problem_skenario(problem, sk.bobot_input)
        bobot_norm = p.bobot_ternormalisasi
        hasil = HasilSkenario(nama_skenario=sk.nama, bobot_ternormalisasi=bobot_norm)

        if hitung_saw_flag:
            try:
                r = hitung_saw(p)
                hasil.v_saw = r.v
                hasil.peringkat_saw = r.peringkat
            except Exception as e:
                pass

        if hitung_wp_flag:
            try:
                r = hitung_wp(p, strategi_zero=strategi_zero, nilai_pengganti=nilai_pengganti)
                hasil.v_wp = r.v
                hasil.peringkat_wp = r.peringkat
            except Exception as e:
                pass

        hasil_list.append(hasil)
    return hasil_list


def sweep_satu_bobot(
    problem: Problem,
    indeks_kriteria: int,
    langkah: float = DEFAULT_SENSITIVITY_STEP,
    hitung_saw_flag: bool = True,
    hitung_wp_flag: bool = True,
    strategi_zero: ZeroHandling = "ganti",
    nilai_pengganti: float = 0.01,
) -> HasilSensitivitas:
    """
    Sweep bobot satu kriteria dari 0 sampai 1 (one-at-a-time).
    Bobot lain disesuaikan secara proporsional: w_j' = w_j * (1 - w_k') / (1 - w_k).

    Parameters
    ----------
    problem : Problem
        Masalah dasar.
    indeks_kriteria : int
        Indeks kriteria yang di-sweep.
    langkah : float
        Langkah sweep (default 0.05).

    Returns
    -------
    HasilSensitivitas
        Dengan sweep_df_saw, sweep_df_wp, rankflip_saw, rankflip_wp.
    """
    bobot_awal = problem.bobot_ternormalisasi
    w_k_awal = bobot_awal[indeks_kriteria]
    n_crit = len(problem.kriteria)
    kode = problem.kode_kriteria
    alternatif = problem.alternatif

    w_k_values = np.arange(0.0, 1.0 + langkah / 2, langkah)
    w_k_values = np.clip(w_k_values, 0.0, 1.0)

    rows_saw: list[dict] = []
    rows_wp: list[dict] = []
    rank_saw_prev: Optional[pd.Series] = None
    rank_wp_prev: Optional[pd.Series] = None
    rankflip_saw: list[float] = []
    rankflip_wp: list[float] = []

    for w_k_baru in w_k_values:
        # Hitung bobot baru (proporsional)
        bobot_baru_norm = np.zeros(n_crit)
        bobot_baru_norm[indeks_kriteria] = w_k_baru
        sisa = 1.0 - w_k_baru

        if abs(1.0 - w_k_awal) < 1e-10:
            # Bobot awal k sudah = 1, tidak bisa proporsional; bagi rata
            for j in range(n_crit):
                if j != indeks_kriteria:
                    bobot_baru_norm[j] = sisa / (n_crit - 1)
        else:
            for j in range(n_crit):
                if j != indeks_kriteria:
                    bobot_baru_norm[j] = bobot_awal[j] * sisa / (1.0 - w_k_awal)

        # Bobot input = bobot ternormalisasi langsung (sudah = 1)
        p = _buat_problem_skenario(problem, list(bobot_baru_norm))

        if hitung_saw_flag:
            try:
                r = hitung_saw(p)
                row = {"w_k": w_k_baru}
                row.update({alt: float(r.v[alt]) for alt in alternatif})
                rows_saw.append(row)
                if rank_saw_prev is not None:
                    r1_prev = rank_saw_prev.idxmin()
                    r1_curr = r.peringkat.idxmin()
                    if r1_prev != r1_curr:
                        rankflip_saw.append(float(w_k_baru))
                rank_saw_prev = r.peringkat
            except Exception:
                pass

        if hitung_wp_flag:
            try:
                r = hitung_wp(p, strategi_zero=strategi_zero, nilai_pengganti=nilai_pengganti)
                row = {"w_k": w_k_baru}
                row.update({alt: float(r.v[alt]) for alt in alternatif})
                rows_wp.append(row)
                if rank_wp_prev is not None:
                    r1_prev = rank_wp_prev.idxmin()
                    r1_curr = r.peringkat.idxmin()
                    if r1_prev != r1_curr:
                        rankflip_wp.append(float(w_k_baru))
                rank_wp_prev = r.peringkat
            except Exception:
                pass

    sweep_df_saw = pd.DataFrame(rows_saw).set_index("w_k") if rows_saw else None
    sweep_df_wp = pd.DataFrame(rows_wp).set_index("w_k") if rows_wp else None

    return HasilSensitivitas(
        sweep_kriteria=problem.kriteria[indeks_kriteria].nama,
        sweep_df_saw=sweep_df_saw,
        sweep_df_wp=sweep_df_wp,
        rankflip_saw=rankflip_saw,
        rankflip_wp=rankflip_wp,
    )


def monte_carlo(
    problem: Problem,
    n_iter: int = DEFAULT_MONTE_CARLO_ITERATIONS,
    konsentrasi: float = 5.0,
    hitung_saw_flag: bool = True,
    hitung_wp_flag: bool = True,
    strategi_zero: ZeroHandling = "ganti",
    nilai_pengganti: float = 0.01,
    seed: Optional[int] = 42,
) -> HasilSensitivitas:
    """
    Simulasi Monte Carlo: bobot acak dari distribusi Dirichlet.

    Parameters
    ----------
    problem : Problem
        Masalah dasar.
    n_iter : int
        Jumlah iterasi (default 1000).
    konsentrasi : float
        Parameter konsentrasi Dirichlet (lebih tinggi = lebih terpusat pada bobot awal).
    seed : int, optional
        Seed acak untuk reproducibility.

    Returns
    -------
    HasilSensitivitas
        Dengan mc_pct_rank1 dan mc_avg_rank.
    """
    rng = np.random.default_rng(seed)
    bobot_awal = problem.bobot_ternormalisasi
    n_crit = len(problem.kriteria)
    alternatif = problem.alternatif

    # Hitung alpha Dirichlet = konsentrasi * bobot_awal
    alpha = konsentrasi * bobot_awal

    rank1_saw = {alt: 0 for alt in alternatif}
    rank1_wp = {alt: 0 for alt in alternatif}
    sum_rank_saw = {alt: 0.0 for alt in alternatif}
    sum_rank_wp = {alt: 0.0 for alt in alternatif}

    for _ in range(n_iter):
        bobot_acak = rng.dirichlet(alpha)
        p = _buat_problem_skenario(problem, list(bobot_acak))

        if hitung_saw_flag:
            try:
                r = hitung_saw(p)
                best = r.peringkat.idxmin()
                rank1_saw[best] = rank1_saw.get(best, 0) + 1
                for alt in alternatif:
                    sum_rank_saw[alt] += float(r.peringkat[alt])
            except Exception:
                pass

        if hitung_wp_flag:
            try:
                r = hitung_wp(p, strategi_zero=strategi_zero, nilai_pengganti=nilai_pengganti)
                best = r.peringkat.idxmin()
                rank1_wp[best] = rank1_wp.get(best, 0) + 1
                for alt in alternatif:
                    sum_rank_wp[alt] += float(r.peringkat[alt])
            except Exception:
                pass

    # Konversi ke DataFrame persen
    pct_data = {}
    avg_data = {}
    if hitung_saw_flag:
        pct_data["SAW (%)"] = {alt: rank1_saw[alt] / n_iter * 100 for alt in alternatif}
        avg_data["SAW avg rank"] = {alt: sum_rank_saw[alt] / n_iter for alt in alternatif}
    if hitung_wp_flag:
        pct_data["WP (%)"] = {alt: rank1_wp[alt] / n_iter * 100 for alt in alternatif}
        avg_data["WP avg rank"] = {alt: sum_rank_wp[alt] / n_iter for alt in alternatif}

    mc_pct = pd.DataFrame(pct_data) if pct_data else None
    mc_avg = pd.DataFrame(avg_data) if avg_data else None

    return HasilSensitivitas(
        mc_pct_rank1=mc_pct,
        mc_avg_rank=mc_avg,
    )
