"""
Komponen UI untuk Tab 6: Sensitivitas.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from engine.models import Problem
from engine.sensitivity import (
    SkenarioBobot, analisis_skenario, sweep_satu_bobot, monte_carlo
)
from config import DEFAULT_DECIMAL_PLACES, DEFAULT_SENSITIVITY_STEP, DEFAULT_MONTE_CARLO_ITERATIONS


def render_tab_sensitivity(state: dict) -> None:
    """Render Tab 6: Sensitivitas."""
    problem: Problem = state.get("problem")
    if problem is None:
        st.warning("⚠️ Lengkapi data di Tab 1 dan Tab 2 terlebih dahulu.")
        return

    dp = state.get("decimal_places", DEFAULT_DECIMAL_PLACES)
    metode = state.get("metode_hitung", "Keduanya")
    hitung_saw = metode in ("SAW", "Keduanya")
    hitung_wp = metode in ("WP", "Keduanya")
    strategi = state.get("strategi_zero", "ganti")
    nilai_peng = state.get("nilai_pengganti", 0.01)

    tab_a, tab_b, tab_c = st.tabs(["A. Skenario Bobot", "B. Sweep Satu Bobot", "C. Monte Carlo"])

    # ======= BAGIAN A: SKENARIO BOBOT =======
    with tab_a:
        st.markdown("### Skenario Bobot")
        st.caption("Tambahkan dan bandingkan skenario bobot berbeda. Setiap skenario menggunakan bobot input yang dinormalisasi.")

        # Inisialisasi skenario default
        if "skenario_list" not in state or not state["skenario_list"]:
            bobot_awal = list(problem.bobot_input)
            state["skenario_list"] = [
                {"nama": "Skenario Awal", "bobot": bobot_awal},
                {"nama": "Skenario 2", "bobot": bobot_awal},
            ]

        # Editor skenario
        kode = problem.kode_kriteria
        n_crit = len(kode)
        skenario_state: list[dict] = state["skenario_list"]

        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            if st.button("➕ Tambah Skenario", key="btn_add_skenario"):
                skenario_state.append({
                    "nama": f"Skenario {len(skenario_state) + 1}",
                    "bobot": list(problem.bobot_input),
                })
        with col_btn2:
            if st.button("🗑️ Hapus Skenario Terakhir", key="btn_del_skenario"):
                if len(skenario_state) > 2:
                    skenario_state.pop()

        for i, sk in enumerate(skenario_state):
            with st.expander(f"⚙️ {sk['nama']}", expanded=(i == 0)):
                sk["nama"] = st.text_input(
                    "Nama Skenario", value=sk["nama"], key=f"sk_nama_{i}"
                )
                cols = st.columns(n_crit)
                bobot_baru = []
                for j, col in enumerate(cols):
                    with col:
                        val = col.number_input(
                            kode[j],
                            value=float(sk["bobot"][j]) if j < len(sk["bobot"]) else 1.0,
                            min_value=0.0001,
                            step=0.01,
                            key=f"sk_{i}_crit_{j}",
                        )
                        bobot_baru.append(val)
                sk["bobot"] = bobot_baru
                total = sum(bobot_baru)
                st.caption(f"Total input: {total:.4f} → Σw = {sum(b/total for b in bobot_baru):.4f}")

        state["skenario_list"] = skenario_state

        if st.button("🚀 Jalankan Analisis Skenario", key="btn_run_skenario", type="primary"):
            skenario_obj = [
                SkenarioBobot(sk["nama"], sk["bobot"])
                for sk in skenario_state
            ]
            with st.spinner("Menghitung..."):
                hasil_sk = analisis_skenario(
                    problem, skenario_obj,
                    hitung_saw_flag=hitung_saw,
                    hitung_wp_flag=hitung_wp,
                    strategi_zero=strategi,
                    nilai_pengganti=nilai_peng,
                )
            state["hasil_skenario"] = hasil_sk

        hasil_sk = state.get("hasil_skenario")
        if hasil_sk:
            st.markdown("#### Tabel Peringkat per Skenario")
            for metode_lbl, attr_v, attr_r in [
                ("SAW", "v_saw", "peringkat_saw"),
                ("WP", "v_wp", "peringkat_wp"),
            ]:
                if not any(getattr(h, attr_r) is not None for h in hasil_sk):
                    continue
                rows = []
                for h in hasil_sk:
                    r = getattr(h, attr_r)
                    v = getattr(h, attr_v)
                    if r is None:
                        continue
                    row = {"Skenario": h.nama_skenario}
                    for alt in problem.alternatif:
                        row[alt] = f"#{int(r.loc[alt])} (V={float(v.loc[alt]):.{dp}f})"
                    rows.append(row)
                if rows:
                    st.markdown(f"**{metode_lbl}:**")
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                    # Heatmap peringkat
                    rank_matrix = []
                    nama_sk = []
                    for h in hasil_sk:
                        r = getattr(h, attr_r)
                        if r is None:
                            continue
                        rank_matrix.append([int(r.loc[alt]) for alt in problem.alternatif])
                        nama_sk.append(h.nama_skenario)
                    if rank_matrix:
                        fig_heat = px.imshow(
                            rank_matrix,
                            x=problem.alternatif,
                            y=nama_sk,
                            text_auto=True,
                            color_continuous_scale="RdYlGn_r",
                            title=f"Heatmap Peringkat {metode_lbl}",
                            labels={"color": "Peringkat"},
                        )
                        fig_heat.update_layout(height=200 + 40 * len(nama_sk))
                        st.plotly_chart(fig_heat, use_container_width=True, key=f"heat_{metode_lbl}")

    # ======= BAGIAN B: SWEEP SATU BOBOT =======
    with tab_b:
        st.markdown("### Sweep Satu Bobot (One-at-a-Time)")
        st.caption(
            "Geser bobot satu kriteria dari 0 ke 1; bobot lain disesuaikan proporsional. "
            "Lihat kapan peringkat-1 berubah (rank-flip)."
        )

        kode_labels = [f"{k.kode} - {k.nama}" for k in problem.kriteria]
        crit_sel_idx = st.selectbox(
            "Pilih Kriteria untuk di-sweep",
            range(len(kode_labels)),
            format_func=lambda i: kode_labels[i],
            key="sweep_crit_sel",
        )
        langkah = st.slider(
            "Langkah sweep", min_value=0.01, max_value=0.2,
            value=DEFAULT_SENSITIVITY_STEP, step=0.01, key="sweep_step"
        )

        if st.button("▶️ Jalankan Sweep", key="btn_sweep", type="primary"):
            with st.spinner("Menghitung sweep..."):
                hasil_sweep = sweep_satu_bobot(
                    problem, crit_sel_idx, langkah=langkah,
                    hitung_saw_flag=hitung_saw,
                    hitung_wp_flag=hitung_wp,
                    strategi_zero=strategi,
                    nilai_pengganti=nilai_peng,
                )
            state["hasil_sweep"] = hasil_sweep

        hasil_sweep = state.get("hasil_sweep")
        if hasil_sweep:
            krit_nama = problem.kriteria[crit_sel_idx].nama

            for metode_lbl, df_sweep, rankflip in [
                ("SAW", hasil_sweep.sweep_df_saw, hasil_sweep.rankflip_saw),
                ("WP", hasil_sweep.sweep_df_wp, hasil_sweep.rankflip_wp),
            ]:
                if df_sweep is None:
                    continue
                st.markdown(f"#### {metode_lbl}: V vs Bobot '{krit_nama}'")
                fig = go.Figure()
                colors = px.colors.qualitative.Set2
                for i, alt in enumerate(problem.alternatif):
                    if alt not in df_sweep.columns:
                        continue
                    fig.add_trace(go.Scatter(
                        x=df_sweep.index.tolist(),
                        y=df_sweep[alt].tolist(),
                        name=alt,
                        mode="lines+markers",
                        line=dict(color=colors[i % len(colors)], width=2),
                    ))
                # Tandai rank-flip
                if rankflip:
                    for rf in rankflip:
                        fig.add_vline(
                            x=rf, line_dash="dash", line_color="red",
                            annotation_text=f"Rank-flip @ {rf:.2f}",
                            annotation_position="top right",
                        )
                fig.update_layout(
                    xaxis_title=f"Bobot '{krit_nama}'",
                    yaxis_title="V",
                    height=350,
                )
                st.plotly_chart(fig, use_container_width=True, key=f"sweep_{metode_lbl}")

                if rankflip:
                    st.warning(
                        f"⚠️ **{metode_lbl}:** Rank-flip terdeteksi pada bobot = {', '.join([f'{r:.2f}' for r in rankflip])}. "
                        f"Pada titik ini peringkat-1 berubah."
                    )
                else:
                    st.success(f"✅ **{metode_lbl}:** Tidak ada rank-flip — peringkat-1 stabil.")

    # ======= BAGIAN C: MONTE CARLO =======
    with tab_c:
        st.markdown("### Simulasi Monte Carlo (Robustness Analysis)")
        st.caption(
            "Bobot acak dari distribusi Dirichlet berpusat pada bobot awal. "
            "Hitung persentase tiap alternatif menjadi peringkat-1."
        )

        col1, col2 = st.columns(2)
        with col1:
            n_iter = st.number_input(
                "Jumlah Iterasi", min_value=100, max_value=10000,
                value=DEFAULT_MONTE_CARLO_ITERATIONS, step=100, key="mc_iter"
            )
        with col2:
            konsentrasi = st.slider(
                "Konsentrasi Dirichlet (lebih tinggi = lebih terpusat pada bobot awal)",
                min_value=1.0, max_value=50.0, value=5.0, step=1.0, key="mc_konsentrasi"
            )

        if st.button("🎲 Jalankan Monte Carlo", key="btn_mc", type="primary"):
            with st.spinner(f"Menjalankan {n_iter} iterasi Monte Carlo..."):
                hasil_mc = monte_carlo(
                    problem, n_iter=int(n_iter), konsentrasi=konsentrasi,
                    hitung_saw_flag=hitung_saw,
                    hitung_wp_flag=hitung_wp,
                    strategi_zero=strategi,
                    nilai_pengganti=nilai_peng,
                    seed=42,
                )
            state["hasil_mc"] = hasil_mc

        hasil_mc = state.get("hasil_mc")
        if hasil_mc:
            if hasil_mc.mc_pct_rank1 is not None:
                st.markdown("#### Persentase Peringkat-1 per Alternatif")
                df_pct = hasil_mc.mc_pct_rank1
                st.dataframe(df_pct.style.format("{:.1f}%"), use_container_width=True)

                # Bar chart
                fig_mc = px.bar(
                    df_pct,
                    barmode="group",
                    title=f"Persentase Peringkat-1 ({n_iter} iterasi Monte Carlo)",
                    labels={"value": "% Peringkat 1", "index": "Alternatif"},
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig_mc.update_layout(height=350)
                st.plotly_chart(fig_mc, use_container_width=True, key="mc_bar")

            if hasil_mc.mc_avg_rank is not None:
                st.markdown("#### Rata-Rata Peringkat per Alternatif")
                st.dataframe(hasil_mc.mc_avg_rank.style.format("{:.2f}"), use_container_width=True)

            # Kesimpulan robustness
            if hasil_mc.mc_pct_rank1 is not None:
                for col in hasil_mc.mc_pct_rank1.columns:
                    best_pct = float(hasil_mc.mc_pct_rank1[col].max())
                    best_alt_mc = hasil_mc.mc_pct_rank1[col].idxmax()
                    if best_pct >= 70:
                        st.success(
                            f"✅ **{col}: Robust!** '{best_alt_mc}' menempati peringkat-1 "
                            f"pada {best_pct:.1f}% dari {n_iter} simulasi."
                        )
                    elif best_pct >= 40:
                        st.info(
                            f"ℹ️ **{col}: Cukup Robust.** '{best_alt_mc}' menempati peringkat-1 "
                            f"pada {best_pct:.1f}% simulasi. Pengambilan keputusan perlu lebih hati-hati."
                        )
                    else:
                        st.warning(
                            f"⚠️ **{col}: Tidak Robust.** Tidak ada alternatif yang dominan "
                            f"(terbaik: '{best_alt_mc}' hanya {best_pct:.1f}% simulasi). "
                            f"Pertimbangkan ulang bobot kriteria."
                        )
