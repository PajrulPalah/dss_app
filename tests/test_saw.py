"""
Test suite untuk engine SAW.
Validasi terhadap nilai yang ditentukan dalam spesifikasi.
Toleransi: 1e-4.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import numpy as np
import pandas as pd

from engine.models import Problem, Criterion
from engine.saw import hitung_saw

TOLERANSI = 1e-4


def buat_problem_laptop() -> Problem:
    """Problem laptop mahasiswa untuk pengujian SAW."""
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
    return Problem(
        nama_kasus="Laptop Test",
        alternatif=alternatif,
        kriteria=kriteria,
        matriks=matriks,
    )


def buat_problem_beasiswa() -> Problem:
    """Problem beasiswa untuk pengujian SAW."""
    kriteria = [
        Criterion("C1", "IPK", "Benefit", 0.35),
        Criterion("C2", "Penghasilan OT (juta/bln)", "Cost", 0.30),
        Criterion("C3", "Jumlah Tanggungan", "Benefit", 0.15),
        Criterion("C4", "Prestasi Non-Akademik (1-5)", "Benefit", 0.20),
    ]
    alternatif = ["Andi", "Bunga", "Citra", "Dimas", "Eka"]
    data = {
        "C1": {"Andi": 3.85, "Bunga": 3.45, "Citra": 3.80, "Dimas": 3.40, "Eka": 3.90},
        "C2": {"Andi": 6.0, "Bunga": 2.5, "Citra": 4.0, "Dimas": 1.8, "Eka": 7.5},
        "C3": {"Andi": 2, "Bunga": 4, "Citra": 3, "Dimas": 5, "Eka": 1},
        "C4": {"Andi": 4, "Bunga": 3, "Citra": 5, "Dimas": 2, "Eka": 4},
    }
    matriks = pd.DataFrame(data, index=alternatif)
    return Problem(
        nama_kasus="Beasiswa Test",
        alternatif=alternatif,
        kriteria=kriteria,
        matriks=matriks,
    )


class TestSAWLaptop:
    """Uji SAW dengan data laptop mahasiswa."""

    def setup_method(self):
        self.problem = buat_problem_laptop()
        self.hasil = hitung_saw(self.problem)

    def test_bobot_normalisasi_sum_satu(self):
        """Bobot ternormalisasi harus berjumlah 1."""
        assert abs(self.hasil.bobot.sum() - 1.0) < TOLERANSI

    def test_v_a1(self):
        """V A1 = 0.7163."""
        assert abs(self.hasil.v["A1"] - 0.7163) < TOLERANSI, f"V A1 = {self.hasil.v['A1']:.4f}"

    def test_v_a2(self):
        """V A2 = 0.8083."""
        assert abs(self.hasil.v["A2"] - 0.8083) < TOLERANSI, f"V A2 = {self.hasil.v['A2']:.4f}"

    def test_v_a3(self):
        """V A3 = 0.7393."""
        assert abs(self.hasil.v["A3"] - 0.7393) < TOLERANSI, f"V A3 = {self.hasil.v['A3']:.4f}"

    def test_v_a4(self):
        """V A4 = 0.8367."""
        assert abs(self.hasil.v["A4"] - 0.8367) < TOLERANSI, f"V A4 = {self.hasil.v['A4']:.4f}"

    def test_peringkat_a4_pertama(self):
        """A4 harus peringkat 1."""
        assert self.hasil.peringkat["A4"] == 1

    def test_peringkat_a1_terakhir(self):
        """A1 harus peringkat 4."""
        assert self.hasil.peringkat["A1"] == 4

    def test_peringkat_a2_kedua(self):
        """A2 harus peringkat 2."""
        assert self.hasil.peringkat["A2"] == 2

    def test_peringkat_a3_ketiga(self):
        """A3 harus peringkat 3."""
        assert self.hasil.peringkat["A3"] == 3

    def test_matriks_r_positif(self):
        """Semua nilai R harus antara 0 dan 1 untuk data positif."""
        assert (self.hasil.matriks_r >= 0).all().all()
        assert (self.hasil.matriks_r <= 1.0 + TOLERANSI).all().all()

    def test_v_antara_nol_satu(self):
        """V harus antara 0 dan 1 untuk data positif."""
        assert (self.hasil.v >= 0).all()
        assert (self.hasil.v <= 1.0 + TOLERANSI).all()


class TestSAWBeasiswa:
    """Uji SAW dengan data beasiswa."""

    def setup_method(self):
        self.problem = buat_problem_beasiswa()
        self.hasil = hitung_saw(self.problem)

    def test_v_andi(self):
        """V Andi = 0.6555."""
        assert abs(self.hasil.v["Andi"] - 0.6555) < TOLERANSI, f"V Andi = {self.hasil.v['Andi']:.4f}"

    def test_v_bunga(self):
        """V Bunga = 0.7656."""
        assert abs(self.hasil.v["Bunga"] - 0.7656) < TOLERANSI, f"V Bunga = {self.hasil.v['Bunga']:.4f}"

    def test_v_citra(self):
        """V Citra = 0.7660."""
        assert abs(self.hasil.v["Citra"] - 0.7660) < TOLERANSI, f"V Citra = {self.hasil.v['Citra']:.4f}"

    def test_v_dimas(self):
        """V Dimas = 0.8351."""
        assert abs(self.hasil.v["Dimas"] - 0.8351) < TOLERANSI, f"V Dimas = {self.hasil.v['Dimas']:.4f}"

    def test_v_eka(self):
        """V Eka = 0.6120."""
        assert abs(self.hasil.v["Eka"] - 0.6120) < TOLERANSI, f"V Eka = {self.hasil.v['Eka']:.4f}"

    def test_peringkat_dimas_pertama(self):
        """Dimas harus peringkat 1."""
        assert self.hasil.peringkat["Dimas"] == 1

    def test_peringkat_eka_terakhir(self):
        """Eka harus peringkat 5."""
        assert self.hasil.peringkat["Eka"] == 5


class TestSAWEdgeCases:
    """Uji kasus tepi SAW."""

    def test_bobot_input_non_100_ternormalisasi(self):
        """Bobot input 20/30/50 (total=100) dan 2/3/5 (total=10) harus menghasilkan bobot sama."""
        kriteria_a = [
            Criterion("C1", "K1", "Benefit", 20),
            Criterion("C2", "K2", "Benefit", 30),
            Criterion("C3", "K3", "Benefit", 50),
        ]
        kriteria_b = [
            Criterion("C1", "K1", "Benefit", 2),
            Criterion("C2", "K2", "Benefit", 3),
            Criterion("C3", "K3", "Benefit", 5),
        ]
        matriks = pd.DataFrame({
            "C1": {"A1": 1.0, "A2": 2.0},
            "C2": {"A1": 3.0, "A2": 4.0},
            "C3": {"A1": 5.0, "A2": 6.0},
        }, index=["A1", "A2"])
        p_a = Problem("test", ["A1", "A2"], kriteria_a, matriks)
        p_b = Problem("test", ["A1", "A2"], kriteria_b, matriks)
        h_a = hitung_saw(p_a)
        h_b = hitung_saw(p_b)
        np.testing.assert_allclose(h_a.v.values, h_b.v.values, atol=TOLERANSI)

    def test_kolom_konstan_tidak_crash(self):
        """Kolom bernilai sama semua tidak boleh crash; menghasilkan r = 1.0."""
        kriteria = [
            Criterion("C1", "Konstan", "Benefit", 0.5),
            Criterion("C2", "Normal", "Benefit", 0.5),
        ]
        matriks = pd.DataFrame({
            "C1": {"A1": 5.0, "A2": 5.0},
            "C2": {"A1": 3.0, "A2": 6.0},
        }, index=["A1", "A2"])
        p = Problem("test", ["A1", "A2"], kriteria, matriks)
        h = hitung_saw(p)
        # Harus tidak crash dan menghasilkan r = 1.0 untuk kolom konstan
        assert h.matriks_r["C1"].eq(1.0).all()

    def test_tie_ranking_method_min(self):
        """Tie harus menggunakan metode 'min' (peringkat sama)."""
        kriteria = [Criterion("C1", "K1", "Benefit", 1.0)]
        matriks = pd.DataFrame({
            "C1": {"A1": 5.0, "A2": 5.0, "A3": 3.0},
        }, index=["A1", "A2", "A3"])
        p = Problem("test", ["A1", "A2", "A3"], kriteria, matriks)
        h = hitung_saw(p)
        assert h.peringkat["A1"] == 1
        assert h.peringkat["A2"] == 1  # tie → min = 1
        assert h.peringkat["A3"] == 3
