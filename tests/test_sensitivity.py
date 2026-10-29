"""
Test suite untuk analisis sensitivitas.
Validasi terhadap nilai yang ditentukan dalam spesifikasi.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import numpy as np
import pandas as pd

from engine.models import Problem, Criterion
from engine.saw import hitung_saw
from engine.sensitivity import SkenarioBobot, analisis_skenario, sweep_satu_bobot, monte_carlo

TOLERANSI = 1e-4


def buat_problem_laptop() -> Problem:
    kriteria = [
        Criterion("C1", "Harga (juta Rp)", "Cost", 0.35),
        Criterion("C2", "RAM (GB)", "Benefit", 0.30),
        Criterion("C3", "Baterai (jam)", "Benefit", 0.20),
        Criterion("C4", "Berat (kg)", "Cost", 0.15),
    ]
    alternatif = ["A1", "A2", "A3", "A4"]
    data = {
        "C1": {"A1": 9.0, "A2": 12.0, "A3": 8.0, "A4": 15.0},
        "C2": {"A1": 8.0, "A2": 16.0, "A3": 8.0, "A4": 16.0},
        "C3": {"A1": 8.0, "A2": 10.0, "A3": 6.0, "A4": 12.0},
        "C4": {"A1": 1.6, "A2": 1.8, "A3": 1.4, "A4": 1.3},
    }
    matriks = pd.DataFrame(data, index=alternatif)
    return Problem("Laptop", alternatif, kriteria, matriks)


def buat_problem_beasiswa() -> Problem:
    kriteria = [
        Criterion("C1", "IPK", "Benefit", 0.35),
        Criterion("C2", "Penghasilan OT", "Cost", 0.30),
        Criterion("C3", "Jumlah Tanggungan", "Benefit", 0.15),
        Criterion("C4", "Prestasi Non-Akademik", "Benefit", 0.20),
    ]
    alternatif = ["Andi", "Bunga", "Citra", "Dimas", "Eka"]
    data = {
        "C1": {"Andi": 3.85, "Bunga": 3.45, "Citra": 3.80, "Dimas": 3.40, "Eka": 3.90},
        "C2": {"Andi": 6.0, "Bunga": 2.5, "Citra": 4.0, "Dimas": 1.8, "Eka": 7.5},
        "C3": {"Andi": 2, "Bunga": 4, "Citra": 3, "Dimas": 5, "Eka": 1},
        "C4": {"Andi": 4, "Bunga": 3, "Citra": 5, "Dimas": 2, "Eka": 4},
    }
    matriks = pd.DataFrame(data, index=alternatif)
    return Problem("Beasiswa", alternatif, kriteria, matriks)


class TestSensitivitasLaptop:
    """Uji sensitivitas dengan data laptop."""

    def setup_method(self):
        self.problem = buat_problem_laptop()

    def test_skenario_prioritas_harga_a3_pertama(self):
        """
        Skenario bobot 0.60/0.18/0.12/0.09 pada SAW: A3 harus peringkat 1.
        V A3 = 0.8396 (dari spesifikasi).
        """
        skenario = [
            SkenarioBobot("Prioritas Harga", [0.60, 0.18, 0.12, 0.09])
        ]
        hasil = analisis_skenario(
            self.problem, skenario,
            hitung_saw_flag=True, hitung_wp_flag=False
        )
        assert len(hasil) == 1
        h = hasil[0]
        assert h.peringkat_saw is not None
        assert h.peringkat_saw["A3"] == 1, f"Peringkat A3 = {h.peringkat_saw['A3']}"

    def test_skenario_v_a3_prioritas_harga(self):
        """V A3 pada skenario Prioritas Harga ≈ 0.8396."""
        skenario = [SkenarioBobot("Prioritas Harga", [0.60, 0.18, 0.12, 0.09])]
        hasil = analisis_skenario(self.problem, skenario, hitung_saw_flag=True, hitung_wp_flag=False)
        v_a3 = float(hasil[0].v_saw["A3"])
        assert abs(v_a3 - 0.8396) < TOLERANSI, f"V A3 = {v_a3:.4f}"

    def test_skenario_a4_turun_prioritas_harga(self):
        """A4 tidak boleh peringkat 1 saat bobot harga 0.60."""
        skenario = [SkenarioBobot("Prioritas Harga", [0.60, 0.18, 0.12, 0.09])]
        hasil = analisis_skenario(self.problem, skenario, hitung_saw_flag=True, hitung_wp_flag=False)
        assert hasil[0].peringkat_saw["A4"] != 1

    def test_sweep_menghasilkan_dataframe(self):
        """Sweep satu bobot harus menghasilkan DataFrame tidak kosong."""
        hasil = sweep_satu_bobot(
            self.problem, indeks_kriteria=0, langkah=0.1,
            hitung_saw_flag=True, hitung_wp_flag=False
        )
        assert hasil.sweep_df_saw is not None
        assert len(hasil.sweep_df_saw) > 0

    def test_monte_carlo_pct_sum_100(self):
        """Persentase peringkat 1 Monte Carlo SAW harus berjumlah ~100%."""
        hasil = monte_carlo(
            self.problem, n_iter=200,
            hitung_saw_flag=True, hitung_wp_flag=False,
            seed=42
        )
        assert hasil.mc_pct_rank1 is not None
        total = hasil.mc_pct_rank1["SAW (%)"].sum()
        assert abs(total - 100.0) < 1.0, f"Total persen = {total:.2f}%"


class TestSensitivitasBeasiswa:
    """Uji sensitivitas dengan data beasiswa."""

    def setup_method(self):
        self.problem = buat_problem_beasiswa()

    def test_skenario_ekonomi_dimas_pertama(self):
        """
        Skenario bobot penghasilan 0.50 (proporsional): Dimas tetap peringkat 1.
        V Dimas = 0.8822.
        """
        # Bobot asli: 0.35, 0.30, 0.15, 0.20
        # w_C2 baru = 0.50; sisa proporsional:
        # w_C1' = 0.35 * (1-0.50) / (1-0.30) = 0.35 * 0.50/0.70 = 0.2500
        # w_C3' = 0.15 * 0.50/0.70 = 0.1071
        # w_C4' = 0.20 * 0.50/0.70 = 0.1429
        # Total = 0.50 + 0.25 + 0.1071 + 0.1429 = 1.0 ✓
        w2_baru = 0.50
        w1_baru = 0.35 * (1 - w2_baru) / (1 - 0.30)
        w3_baru = 0.15 * (1 - w2_baru) / (1 - 0.30)
        w4_baru = 0.20 * (1 - w2_baru) / (1 - 0.30)
        skenario = [SkenarioBobot("Prioritas Ekonomi", [w1_baru, w2_baru, w3_baru, w4_baru])]
        hasil = analisis_skenario(self.problem, skenario, hitung_saw_flag=True, hitung_wp_flag=False)
        assert hasil[0].peringkat_saw["Dimas"] == 1

    def test_skenario_ekonomi_v_andi(self):
        """V Andi pada skenario ekonomi ≈ 0.5539."""
        w2_baru = 0.50
        w1_baru = 0.35 * (1 - w2_baru) / (1 - 0.30)
        w3_baru = 0.15 * (1 - w2_baru) / (1 - 0.30)
        w4_baru = 0.20 * (1 - w2_baru) / (1 - 0.30)
        skenario = [SkenarioBobot("Prioritas Ekonomi", [w1_baru, w2_baru, w3_baru, w4_baru])]
        hasil = analisis_skenario(self.problem, skenario, hitung_saw_flag=True, hitung_wp_flag=False)
        v_andi = float(hasil[0].v_saw["Andi"])
        assert abs(v_andi - 0.5539) < TOLERANSI, f"V Andi = {v_andi:.4f}"

    def test_skenario_ekonomi_v_dimas(self):
        """V Dimas pada skenario ekonomi ≈ 0.8822."""
        w2_baru = 0.50
        w1_baru = 0.35 * (1 - w2_baru) / (1 - 0.30)
        w3_baru = 0.15 * (1 - w2_baru) / (1 - 0.30)
        w4_baru = 0.20 * (1 - w2_baru) / (1 - 0.30)
        skenario = [SkenarioBobot("Prioritas Ekonomi", [w1_baru, w2_baru, w3_baru, w4_baru])]
        hasil = analisis_skenario(self.problem, skenario, hitung_saw_flag=True, hitung_wp_flag=False)
        v_dimas = float(hasil[0].v_saw["Dimas"])
        assert abs(v_dimas - 0.8822) < TOLERANSI, f"V Dimas = {v_dimas:.4f}"
