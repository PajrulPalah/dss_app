"""
Test suite untuk engine WP.
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
from engine.wp import hitung_wp

TOLERANSI = 1e-4


def buat_problem_superstore() -> Problem:
    """
    Problem Superstore untuk validasi WP.
    Profit Ratio dan Sales per Customer dihitung dari kolom lain.
    """
    alternatif = ["West", "East", "Central", "South"]
    # Data input mentah
    sales = {"West": 107483.0, "East": 41705.0, "Central": 14007.0, "South": 17309.0}
    profit = {"West": 19663.0, "East": 4985.0, "Central": -3634.0, "South": 2219.0}
    qty = {"West": 1898.0, "East": 543.0, "Central": 350.0, "South": 262.0}
    pelanggan = {"West": 170.0, "East": 41.0, "Central": 37.0, "South": 24.0}

    # Kolom turunan
    profit_ratio = {alt: profit[alt] / sales[alt] * 100 for alt in alternatif}
    sales_per_cust = {alt: sales[alt] / pelanggan[alt] for alt in alternatif}

    kriteria = [
        Criterion("C1", "Sales", "Benefit", 20),
        Criterion("C2", "Profit", "Benefit", 30),
        Criterion("C3", "Profit Ratio (%)", "Benefit", 25),
        Criterion("C4", "Sales per Customer", "Benefit", 10),
        Criterion("C5", "Quantity", "Benefit", 5),
        Criterion("C6", "Jumlah Pelanggan", "Benefit", 10),
    ]
    matriks = pd.DataFrame({
        "C1": sales,
        "C2": profit,
        "C3": profit_ratio,
        "C4": sales_per_cust,
        "C5": qty,
        "C6": pelanggan,
    }, index=alternatif)

    return Problem(
        nama_kasus="Superstore Test",
        alternatif=alternatif,
        kriteria=kriteria,
        matriks=matriks,
    )


def buat_problem_laptop() -> Problem:
    """Problem laptop mahasiswa untuk pengujian WP."""
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
        nama_kasus="Laptop WP Test",
        alternatif=alternatif,
        kriteria=kriteria,
        matriks=matriks,
    )


class TestWPSuperstore:
    """Uji WP dengan data Superstore (nilai pengganti 0.01)."""

    def setup_method(self):
        self.problem = buat_problem_superstore()
        self.hasil = hitung_wp(self.problem, strategi_zero="ganti", nilai_pengganti=0.01)

    def test_bobot_sum_satu(self):
        assert abs(self.hasil.bobot.sum() - 1.0) < TOLERANSI

    def test_s_west(self):
        assert abs(self.hasil.s["West"] - 1892.2965) < 0.5, f"S West = {self.hasil.s['West']:.4f}"

    def test_s_east(self):
        assert abs(self.hasil.s["East"] - 797.0127) < 0.5, f"S East = {self.hasil.s['East']:.4f}"

    def test_s_central(self):
        assert abs(self.hasil.s["Central"] - 1.8668) < 0.1, f"S Central = {self.hasil.s['Central']:.4f}"

    def test_s_south(self):
        assert abs(self.hasil.s["South"] - 471.2107) < 0.5, f"S South = {self.hasil.s['South']:.4f}"

    def test_total_s(self):
        total = self.hasil.s.sum()
        assert abs(total - 3162.3867) < 1.0, f"Total S = {total:.4f}"

    def test_v_west(self):
        assert abs(self.hasil.v["West"] - 0.5984) < TOLERANSI, f"V West = {self.hasil.v['West']:.4f}"

    def test_v_east(self):
        assert abs(self.hasil.v["East"] - 0.2520) < TOLERANSI, f"V East = {self.hasil.v['East']:.4f}"

    def test_v_central(self):
        assert abs(self.hasil.v["Central"] - 0.0006) < TOLERANSI, f"V Central = {self.hasil.v['Central']:.4f}"

    def test_v_south(self):
        assert abs(self.hasil.v["South"] - 0.1490) < TOLERANSI, f"V South = {self.hasil.v['South']:.4f}"

    def test_sum_v_satu(self):
        """sum(V) harus = 1."""
        assert abs(self.hasil.v.sum() - 1.0) < TOLERANSI

    def test_peringkat_west_pertama(self):
        assert self.hasil.peringkat["West"] == 1

    def test_peringkat_east_kedua(self):
        assert self.hasil.peringkat["East"] == 2

    def test_peringkat_south_ketiga(self):
        assert self.hasil.peringkat["South"] == 3

    def test_peringkat_central_keempat(self):
        assert self.hasil.peringkat["Central"] == 4

    def test_ada_sel_disesuaikan(self):
        """Harus ada sel yang disesuaikan (Central profit negatif)."""
        assert len(self.hasil.sel_disesuaikan) > 0

    def test_central_profit_diganti(self):
        """Central di kolom C2 (Profit) harus diganti karena negatif."""
        sel = [s for s in self.hasil.sel_disesuaikan if s.alternatif == "Central" and s.kriteria == "C2"]
        assert len(sel) == 1
        assert abs(sel[0].nilai_asli - (-3634.0)) < TOLERANSI
        assert abs(sel[0].nilai_baru - 0.01) < TOLERANSI


class TestWPLaptop:
    """Uji WP dengan data laptop mahasiswa."""

    def setup_method(self):
        self.problem = buat_problem_laptop()
        self.hasil = hitung_wp(self.problem, strategi_zero="ganti", nilai_pengganti=0.01)

    def test_s_a1(self):
        assert abs(self.hasil.s["A1"] - 1.2216) < TOLERANSI, f"S A1 = {self.hasil.s['A1']:.4f}"

    def test_s_a2(self):
        assert abs(self.hasil.s["A2"] - 1.3971) < TOLERANSI, f"S A2 = {self.hasil.s['A2']:.4f}"

    def test_s_a3(self):
        assert abs(self.hasil.s["A3"] - 1.2262) < TOLERANSI, f"S A3 = {self.hasil.s['A3']:.4f}"

    def test_s_a4(self):
        assert abs(self.hasil.s["A4"] - 1.4072) < TOLERANSI, f"S A4 = {self.hasil.s['A4']:.4f}"

    def test_total_s(self):
        total = self.hasil.s.sum()
        assert abs(total - 5.2521) < TOLERANSI, f"Total S = {total:.4f}"

    def test_v_a4(self):
        assert abs(self.hasil.v["A4"] - 0.2679) < TOLERANSI, f"V A4 = {self.hasil.v['A4']:.4f}"

    def test_v_a2(self):
        assert abs(self.hasil.v["A2"] - 0.2660) < TOLERANSI, f"V A2 = {self.hasil.v['A2']:.4f}"

    def test_v_a3(self):
        assert abs(self.hasil.v["A3"] - 0.2335) < TOLERANSI, f"V A3 = {self.hasil.v['A3']:.4f}"

    def test_v_a1(self):
        assert abs(self.hasil.v["A1"] - 0.2326) < TOLERANSI, f"V A1 = {self.hasil.v['A1']:.4f}"

    def test_sum_v_satu(self):
        assert abs(self.hasil.v.sum() - 1.0) < TOLERANSI

    def test_peringkat_a4_pertama(self):
        assert self.hasil.peringkat["A4"] == 1


class TestWPEdgeCases:
    """Uji kasus tepi WP."""

    def test_strategi_tolak_error(self):
        """Strategi 'tolak' harus melempar ValueError untuk nilai <= 0."""
        kriteria = [Criterion("C1", "K1", "Benefit", 1.0)]
        matriks = pd.DataFrame({"C1": {"A1": -5.0, "A2": 3.0}}, index=["A1", "A2"])
        p = Problem("test", ["A1", "A2"], kriteria, matriks)
        with pytest.raises(ValueError):
            hitung_wp(p, strategi_zero="tolak")

    def test_strategi_geser(self):
        """Strategi 'geser' harus menggeser seluruh kolom agar min = nilai_pengganti."""
        kriteria = [Criterion("C1", "K1", "Benefit", 1.0)]
        matriks = pd.DataFrame({"C1": {"A1": -2.0, "A2": 3.0}}, index=["A1", "A2"])
        p = Problem("test", ["A1", "A2"], kriteria, matriks)
        h = hitung_wp(p, strategi_zero="geser", nilai_pengganti=0.01)
        # Minimum kolom setelah geser harus = 0.01
        assert abs(float(h.matriks_adjusted["C1"].min()) - 0.01) < TOLERANSI

    def test_sum_v_wp_selalu_satu(self):
        """sum(V) WP harus selalu = 1."""
        kriteria = [
            Criterion("C1", "K1", "Benefit", 0.5),
            Criterion("C2", "K2", "Cost", 0.5),
        ]
        matriks = pd.DataFrame({
            "C1": {"A1": 4.0, "A2": 6.0, "A3": 8.0},
            "C2": {"A1": 2.0, "A2": 3.0, "A3": 1.0},
        }, index=["A1", "A2", "A3"])
        p = Problem("test", ["A1", "A2", "A3"], kriteria, matriks)
        h = hitung_wp(p)
        assert abs(h.v.sum() - 1.0) < TOLERANSI
