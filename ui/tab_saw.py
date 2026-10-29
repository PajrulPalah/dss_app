"""
Komponen UI untuk Tab 3: Hasil SAW.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from engine.models import Problem, SAWResult
from engine.saw import hitung_saw
from config import DEFAULT_DECIMAL_PLACES, BENEFIT


def _format_num(v: float, dp: int) -> str:
    return f"{v:.{dp}f}"


def render_tab_saw(state: dict) -> None:
    """Render Tab 3: Hasil SAW."""
    problem: Problem = state.get("problem")
    if problem is None:
        st.warning("⚠️ Lengkapi data di Tab 1 dan Tab 2 terlebih dahulu.")
        return

    dp = state.get("decimal_places", DEFAULT_DECIMAL_PLACES)
    tampil_rinci = state.get("tampil_rinci", True)

    # Hitung SAW
    try:
        hasil = hitung_saw(problem)
        state["hasil_saw"] = hasil
    except Exception as e:
        st.error(f"❌ Error saat menghitung SAW: {e}")
        state["hasil_saw"] = None
        return

    # Tampilkan peringatan
    for w in hasil.peringatan:
        st.warning(w)

    bobot = hasil.bobot
    kode = problem.kode_kriteria
    tipe = problem.tipe_kriteria
    n_crit = len(kode)
    n_alt = len(problem.alternatif)

    # ---- LANGKAH 1: Pembagi ----
    st.markdown("## Langkah 1: Normalisasi — Nilai Pembagi")
    st.info(
        "**Rumus:** Benefit → Pembagi = max(kolom); Cost → Pembagi = min(kolom)  \n"
        "Normalisasi: Benefit → r = x / max; Cost → r = min / x"
    )

    df_pembagi = pd.DataFrame({
        "Kode": kode,
        "Nama": [k.nama for k in problem.kriteria],
        "Tipe": tipe,
        "Bobot (w)": [f"{bobot[i]:.{dp}f}" for i in range(n_crit)],
        "Pembagi (max/min)": [f"{hasil.pembagi[kode[i]]:.{dp}f}" for i in range(n_crit)],
    })
    st.dataframe(df_pembagi, use_container_width=True, hide_index=True)

    # ---- LANGKAH 2: Matriks R ----
    st.markdown("## Langkah 2: Matriks R (Ternormalisasi)")

    df_r = hasil.matriks_r.copy().round(dp)
    st.dataframe(df_r.style.format(f"{{:.{dp}f}}").highlight_max(axis=0, color="#D9EAEC"), use_container_width=True)

    # Contoh hitung interaktif
    if tampil_rinci:
        with st.expander("🔍 Contoh Perhitungan r per Sel (Pilih Alternatif & Kriteria)", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                alt_sel = st.selectbox("Alternatif", problem.alternatif, key="saw_alt_sel")
            with col2:
                crit_sel = st.selectbox("Kriteria", kode, key="saw_crit_sel")

            if alt_sel and crit_sel:
                idx_crit = kode.index(crit_sel)
                tipe_sel = tipe[idx_crit]
                x = float(problem.matriks.loc[alt_sel, crit_sel])
                pembagi = float(hasil.pembagi[crit_sel])
                r = float(hasil.matriks_r.loc[alt_sel, crit_sel])

                if tipe_sel == BENEFIT:
                    st.latex(
                        rf"r_{{{alt_sel},{crit_sel}}} = \frac{{x}}{{\max}} = "
                        rf"\frac{{{x:.{dp}f}}}{{{pembagi:.{dp}f}}} = {r:.{dp}f}"
                    )
                else:
                    st.latex(
                        rf"r_{{{alt_sel},{crit_sel}}} = \frac{{\min}}{{x}} = "
                        rf"\frac{{{pembagi:.{dp}f}}}{{{x:.{dp}f}}} = {r:.{dp}f}"
                    )

    # ---- LANGKAH 3: Kontribusi dan V ----
    st.markdown("## Langkah 3: Kontribusi w×r dan Skor V")
    st.info("**Rumus:** V_i = Σ_j (w_j × r_ij)")

    # Tabel w*r
    df_wr = hasil.matriks_wr.copy().round(dp)
    st.markdown("**Matriks Kontribusi (w × r):**")
    st.dataframe(df_wr.style.format(f"{{:.{dp}f}}"), use_container_width=True)

    # Tabel V dan Peringkat
    df_v = pd.DataFrame({
        "Alternatif": problem.alternatif,
        "Skor V": [f"{hasil.v.loc[alt]:.{dp}f}" for alt in problem.alternatif],
        "Peringkat": [int(hasil.peringkat.loc[alt]) for alt in problem.alternatif],
    }).sort_values("Peringkat").reset_index(drop=True)
    st.markdown("**Tabel Skor V dan Peringkat:**")
    st.dataframe(df_v, use_container_width=True, hide_index=True)

    # Contoh hitung V untuk alternatif terpilih
    if tampil_rinci:
        with st.expander("🔍 Contoh Perhitungan V (Pilih Alternatif)", expanded=False):
            alt_v = st.selectbox("Alternatif", problem.alternatif, key="saw_alt_v")
            if alt_v:
                parts = []
                total = 0.0
                for j, col in enumerate(kode):
                    w = bobot[j]
                    r = float(hasil.matriks_r.loc[alt_v, col])
                    wr = w * r
                    total += wr
                    parts.append(f"({w:.{dp}f} × {r:.{dp}f})")
                rumus_str = " + ".join(parts)
                v_val = float(hasil.v.loc[alt_v])
                st.markdown(f"**V({alt_v}) = {rumus_str} = {v_val:.{dp}f}**")

    # ---- GRAFIK ----
    st.markdown("## 📊 Visualisasi Hasil SAW")
    col1, col2 = st.columns([1, 1])

    with col1:
        # Bar chart V
        df_bar = pd.DataFrame({
            "Alternatif": problem.alternatif,
            "V": [float(hasil.v.loc[alt]) for alt in problem.alternatif],
        }).sort_values("V", ascending=True)
        fig_bar = px.bar(
            df_bar, x="V", y="Alternatif", orientation="h",
            title="Skor V (SAW)",
            color="V", color_continuous_scale="Teal",
            text=df_bar["V"].apply(lambda x: f"{x:.{dp}f}"),
        )
        fig_bar.update_layout(height=300, coloraxis_showscale=False)
        st.plotly_chart(fig_bar, use_container_width=True, key="saw_bar_v")

    with col2:
        # Stacked bar kontribusi
        df_stack = hasil.matriks_wr.copy()
        df_stack.index = problem.alternatif
        fig_stack = go.Figure()
        colors = px.colors.qualitative.Set2
        for j, col in enumerate(kode):
            fig_stack.add_trace(go.Bar(
                name=col,
                x=df_stack.index.tolist(),
                y=df_stack[col].tolist(),
                marker_color=colors[j % len(colors)],
            ))
        fig_stack.update_layout(
            barmode="stack",
            title="Kontribusi Tiap Kriteria terhadap V",
            height=300,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_stack, use_container_width=True, key="saw_stack")

    # ---- METRIK ----
    st.markdown("## 🏆 Ringkasan")
    best_alt = hasil.peringkat.idxmin()
    worst_alt = hasil.peringkat.idxmax()
    best_v = float(hasil.v.loc[best_alt])
    worst_v = float(hasil.v.loc[worst_alt])

    c1, c2, c3 = st.columns(3)
    c1.metric("🥇 Alternatif Terbaik (SAW)", best_alt, f"V = {best_v:.{dp}f}")
    c2.metric("⚠️ Perlu Perhatian (SAW)", worst_alt, f"V = {worst_v:.{dp}f}")
    c3.metric("Selisih Skor", f"{best_v - worst_v:.{dp}f}")
