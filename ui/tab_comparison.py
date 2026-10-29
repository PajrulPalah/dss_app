"""
Komponen UI untuk Tab 5: Perbandingan SAW vs WP.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from engine.models import Problem, SAWResult, WPResult
from config import DEFAULT_DECIMAL_PLACES


def _narasi_perbandingan(
    problem: Problem,
    hasil_saw: SAWResult,
    hasil_wp: WPResult,
    dp: int,
) -> str:
    """Buat narasi otomatis perbandingan SAW vs WP."""
    best_saw = hasil_saw.peringkat.idxmin()
    best_wp = hasil_wp.peringkat.idxmin()

    if best_saw == best_wp:
        narasi = (
            f"✅ **Kedua metode sepakat:** '{best_saw}' adalah alternatif terbaik "
            f"(V_SAW = {float(hasil_saw.v.loc[best_saw]):.{dp}f}, "
            f"V_WP = {float(hasil_wp.v.loc[best_saw]):.{dp}f}). "
            f"Konsistensi kedua metode meningkatkan kepercayaan pada rekomendasi ini."
        )
    else:
        best_wp_v_saw = float(hasil_saw.v.loc[best_wp])
        narasi = (
            f"⚠️ **Kedua metode tidak sepakat:** SAW memilih **'{best_saw}'**, "
            f"sedangkan WP memilih **'{best_wp}'**. "
            f"Kemungkinan penyebab: '{best_wp}' memiliki nilai ekstrem rendah pada salah satu kriteria "
            f"yang dihukum lebih berat oleh WP (perkalian pangkat), "
            f"sedangkan SAW (penjumlahan bobot) lebih toleran terhadap nilai rendah di satu kriteria. "
            f"Periksa sel-sel yang disesuaikan pada hasil WP."
        )

    # Hitung perbedaan peringkat
    perbedaan = sum(
        1 for alt in problem.alternatif
        if int(hasil_saw.peringkat.loc[alt]) != int(hasil_wp.peringkat.loc[alt])
    )
    if perbedaan == 0:
        narasi += " Seluruh urutan peringkat identik di kedua metode."
    elif perbedaan <= len(problem.alternatif) // 2:
        narasi += f" Terdapat {perbedaan} alternatif dengan peringkat berbeda."
    else:
        narasi += f" Terdapat {perbedaan} alternatif dengan peringkat berbeda — hasil cukup sensitif terhadap pemilihan metode."

    return narasi


def render_tab_comparison(state: dict) -> None:
    """Render Tab 5: Perbandingan SAW vs WP."""
    hasil_saw: SAWResult = state.get("hasil_saw")
    hasil_wp: WPResult = state.get("hasil_wp")

    if hasil_saw is None and hasil_wp is None:
        st.warning("⚠️ Jalankan perhitungan SAW dan/atau WP terlebih dahulu di Tab 3 dan 4.")
        return

    if hasil_saw is None:
        st.info("ℹ️ Hanya hasil WP tersedia.")
        return

    if hasil_wp is None:
        st.info("ℹ️ Hanya hasil SAW tersedia.")
        return

    problem: Problem = state.get("problem")
    dp = state.get("decimal_places", DEFAULT_DECIMAL_PLACES)

    # ---- TABEL PERBANDINGAN ----
    st.markdown("## 📊 Tabel Perbandingan SAW vs WP")

    rows = []
    for alt in problem.alternatif:
        rank_saw = int(hasil_saw.peringkat.loc[alt])
        rank_wp = int(hasil_wp.peringkat.loc[alt])
        selisih = rank_saw - rank_wp
        rows.append({
            "Alternatif": alt,
            "V SAW": f"{float(hasil_saw.v.loc[alt]):.{dp}f}",
            "Peringkat SAW": rank_saw,
            "V WP": f"{float(hasil_wp.v.loc[alt]):.{dp}f}",
            "Peringkat WP": rank_wp,
            "Selisih Peringkat": selisih,
            "Status": "✅ Sama" if selisih == 0 else f"⚠️ Berbeda ({'+' if selisih > 0 else ''}{selisih})",
        })
    df_comp = pd.DataFrame(rows)
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

    # ---- NARASI OTOMATIS ----
    st.markdown("### 📝 Interpretasi Otomatis")
    narasi = _narasi_perbandingan(problem, hasil_saw, hasil_wp, dp)
    st.markdown(narasi)

    # ---- GRAFIK BERDAMPINGAN ----
    st.markdown("## 📈 Visualisasi Perbandingan")
    col1, col2 = st.columns([1, 1])

    with col1:
        # Bar chart berdampingan (V dinormalisasi ke rentang [0,1])
        v_saw = np.array([float(hasil_saw.v.loc[alt]) for alt in problem.alternatif])
        v_wp = np.array([float(hasil_wp.v.loc[alt]) for alt in problem.alternatif])
        v_saw_norm = v_saw / v_saw.max() if v_saw.max() > 0 else v_saw
        v_wp_norm = v_wp / v_wp.max() if v_wp.max() > 0 else v_wp

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name="SAW (dinormalisasi)",
            x=problem.alternatif,
            y=v_saw_norm.tolist(),
            marker_color="#0F4C5C",
            text=[f"{v:.{dp}f}" for v in v_saw_norm],
            textposition="outside",
        ))
        fig_bar.add_trace(go.Bar(
            name="WP (dinormalisasi)",
            x=problem.alternatif,
            y=v_wp_norm.tolist(),
            marker_color="#5BA4B0",
            text=[f"{v:.{dp}f}" for v in v_wp_norm],
            textposition="outside",
        ))
        fig_bar.update_layout(
            barmode="group",
            title="Skor V Dinormalisasi (SAW vs WP)",
            yaxis_title="V / max(V)",
            height=350,
        )
        st.plotly_chart(fig_bar, use_container_width=True, key="comp_bar")

    with col2:
        # Slope chart peringkat
        ranks_saw = [int(hasil_saw.peringkat.loc[alt]) for alt in problem.alternatif]
        ranks_wp = [int(hasil_wp.peringkat.loc[alt]) for alt in problem.alternatif]

        fig_slope = go.Figure()
        colors_slope = px.colors.qualitative.Set2
        for i, alt in enumerate(problem.alternatif):
            color = colors_slope[i % len(colors_slope)]
            fig_slope.add_trace(go.Scatter(
                x=["SAW", "WP"],
                y=[ranks_saw[i], ranks_wp[i]],
                mode="lines+markers+text",
                name=alt,
                line=dict(color=color, width=2),
                marker=dict(size=10, color=color),
                text=[str(ranks_saw[i]), str(ranks_wp[i])],
                textposition="middle right",
            ))
        fig_slope.update_layout(
            title="Slope Chart Peringkat (SAW vs WP)",
            yaxis=dict(autorange="reversed", tickmode="linear", tick0=1, dtick=1),
            yaxis_title="Peringkat (1 = terbaik)",
            height=350,
        )
        st.plotly_chart(fig_slope, use_container_width=True, key="comp_slope")
