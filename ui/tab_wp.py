"""
Komponen UI untuk Tab 4: Hasil WP.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from engine.models import Problem, WPResult
from engine.wp import hitung_wp, ZeroHandling
from config import DEFAULT_DECIMAL_PLACES, DEFAULT_REPLACEMENT_VALUE


def render_tab_wp(state: dict) -> None:
    """Render Tab 4: Hasil WP."""
    problem: Problem = state.get("problem")
    if problem is None:
        st.warning("⚠️ Lengkapi data di Tab 1 dan Tab 2 terlebih dahulu.")
        return

    dp = state.get("decimal_places", DEFAULT_DECIMAL_PLACES)
    tampil_rinci = state.get("tampil_rinci", True)
    strategi: ZeroHandling = state.get("strategi_zero", "ganti")
    nilai_peng = state.get("nilai_pengganti", DEFAULT_REPLACEMENT_VALUE)

    # Hitung WP
    try:
        hasil = hitung_wp(problem, strategi_zero=strategi, nilai_pengganti=nilai_peng)
        state["hasil_wp"] = hasil
    except ValueError as e:
        st.error(f"❌ Error: {e}")
        state["hasil_wp"] = None
        return
    except Exception as e:
        st.error(f"❌ Error saat menghitung WP: {e}")
        state["hasil_wp"] = None
        return

    # Tampilkan peringatan
    for w in hasil.peringatan:
        st.warning(w)

    bobot = hasil.bobot
    pangkat = hasil.pangkat
    kode = problem.kode_kriteria
    n_crit = len(kode)

    # ---- TABEL PANGKAT ----
    st.markdown("## Langkah 1: Pangkat per Kriteria")
    st.info("**Rumus:** Benefit → pangkat = +w; Cost → pangkat = −w")

    df_pangkat = pd.DataFrame({
        "Kode": kode,
        "Nama": [k.nama for k in problem.kriteria],
        "Tipe": problem.tipe_kriteria,
        "Bobot w": [f"{bobot[i]:.{dp}f}" for i in range(n_crit)],
        "Pangkat": [f"{pangkat[i]:+.{dp}f}" for i in range(n_crit)],
    })
    st.dataframe(df_pangkat, use_container_width=True, hide_index=True)

    # ---- SEL YANG DISESUAIKAN ----
    if hasil.sel_disesuaikan:
        st.markdown("## ⚠️ Sel yang Disesuaikan (Nilai ≤ 0 Diganti)")
        with st.expander(f"Lihat {len(hasil.sel_disesuaikan)} sel yang diubah", expanded=True):
            df_adj = pd.DataFrame([
                {
                    "Alternatif": s.alternatif,
                    "Kriteria": s.kriteria,
                    "Nilai Asli": f"{s.nilai_asli:.{dp}f}",
                    "Nilai Baru": f"{s.nilai_baru:.{dp}f}",
                }
                for s in hasil.sel_disesuaikan
            ])
            st.dataframe(df_adj, use_container_width=True, hide_index=True)
            st.error(
                "⚠️ **Catatan Edukatif:** WP menggunakan perkalian dengan pangkat, "
                "sehingga nilai buruk pada SATU kriteria saja dapat mengakibatkan S yang sangat kecil. "
                "Contoh: Central dengan profit negatif (diganti 0,01) mendapat S ≈ 1,87 "
                "dibanding West yang S ≈ 1892. Penggantian nilai ini SANGAT memengaruhi peringkat!"
            )

    # ---- MATRIKS YANG DISESUAIKAN ----
    st.markdown("## Langkah 2: Matriks Disesuaikan & x^pangkat")
    st.dataframe(
        hasil.matriks_adjusted.round(dp).style.format(f"{{:.{dp}f}}"),
        use_container_width=True,
    )

    with st.expander("Rincian x_ij^pangkat_j per Sel", expanded=False):
        st.dataframe(
            hasil.matriks_xpangkat.round(dp).style.format(f"{{:.{dp}f}}"),
            use_container_width=True,
        )

    # ---- VEKTOR S DAN V ----
    st.markdown("## Langkah 3: Vektor S dan V")
    st.info("**Rumus:** S_i = ∏_j x_ij^(pangkat_j); V_i = S_i / Σ S")

    df_sv = pd.DataFrame({
        "Alternatif": problem.alternatif,
        "S": [f"{float(hasil.s.loc[alt]):.{dp}f}" for alt in problem.alternatif],
        "V": [f"{float(hasil.v.loc[alt]):.{dp}f}" for alt in problem.alternatif],
        "Peringkat": [int(hasil.peringkat.loc[alt]) for alt in problem.alternatif],
    }).sort_values("Peringkat").reset_index(drop=True)
    st.dataframe(df_sv, use_container_width=True, hide_index=True)

    total_s = float(hasil.s.sum())
    st.markdown(f"**Total Σ S = {total_s:.{dp}f}** | **Σ V = {float(hasil.v.sum()):.{dp}f}** *(harus = 1)*")

    # Contoh hitung S dan V untuk alternatif terpilih
    if tampil_rinci:
        with st.expander("🔍 Contoh Perhitungan S dan V (Pilih Alternatif)", expanded=False):
            alt_wp = st.selectbox("Alternatif", problem.alternatif, key="wp_alt_sel")
            if alt_wp:
                parts_s = []
                for j, col in enumerate(kode):
                    x = float(hasil.matriks_adjusted.loc[alt_wp, col])
                    p = pangkat[j]
                    xp = float(hasil.matriks_xpangkat.loc[alt_wp, col])
                    parts_s.append(f"{x:.{dp}f}^({p:+.{dp}f}) = {xp:.{dp}f}")
                s_val = float(hasil.s.loc[alt_wp])
                v_val = float(hasil.v.loc[alt_wp])
                st.markdown("**S = " + " × ".join([f"{float(hasil.matriks_xpangkat.loc[alt_wp, c]):.{dp}f}" for c in kode]) + f" = {s_val:.{dp}f}**")
                for p in parts_s:
                    st.caption(f"  • {p}")
                st.markdown(f"**V = S / Σ S = {s_val:.{dp}f} / {total_s:.{dp}f} = {v_val:.{dp}f}**")

    # ---- GRAFIK ----
    st.markdown("## 📊 Visualisasi Hasil WP")
    col1, col2 = st.columns([1, 1])

    with col1:
        df_bar = pd.DataFrame({
            "Alternatif": problem.alternatif,
            "V": [float(hasil.v.loc[alt]) for alt in problem.alternatif],
        }).sort_values("V", ascending=True)
        fig_bar = px.bar(
            df_bar, x="V", y="Alternatif", orientation="h",
            title="Skor V (WP) — Total = 1",
            color="V", color_continuous_scale="Teal",
            text=df_bar["V"].apply(lambda x: f"{x:.{dp}f}"),
        )
        fig_bar.update_layout(height=300, coloraxis_showscale=False)
        st.plotly_chart(fig_bar, use_container_width=True, key="wp_bar_v")

    with col2:
        st.info(
            "💡 **Sifat WP:** Skor V bersifat relatif (total = 1). "
            "Nilai buruk pada satu kriteria dihukum lebih berat dibandingkan SAW "
            "karena WP menggunakan perkalian, bukan penjumlahan."
        )
        # Bar chart S
        df_s = pd.DataFrame({
            "Alternatif": problem.alternatif,
            "S": [float(hasil.s.loc[alt]) for alt in problem.alternatif],
        }).sort_values("S", ascending=True)
        fig_s = px.bar(
            df_s, x="S", y="Alternatif", orientation="h",
            title="Vektor S (WP)",
            color="S", color_continuous_scale="Blues",
            text=df_s["S"].apply(lambda x: f"{x:.{dp}f}"),
        )
        fig_s.update_layout(height=300, coloraxis_showscale=False)
        st.plotly_chart(fig_s, use_container_width=True, key="wp_bar_s")

    # ---- METRIK ----
    st.markdown("## 🏆 Ringkasan WP")
    best_alt = hasil.peringkat.idxmin()
    worst_alt = hasil.peringkat.idxmax()
    c1, c2, c3 = st.columns(3)
    c1.metric("🥇 Alternatif Terbaik (WP)", best_alt, f"V = {float(hasil.v.loc[best_alt]):.{dp}f}")
    c2.metric("⚠️ Perlu Perhatian (WP)", worst_alt, f"V = {float(hasil.v.loc[worst_alt]):.{dp}f}")
    c3.metric("Σ V", f"{float(hasil.v.sum()):.{dp}f}", "Harus = 1")
