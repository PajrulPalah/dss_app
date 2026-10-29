"""
Komponen UI untuk Tab 1: Definisi Masalah.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import (
    BENEFIT, COST, DEFAULT_DECIMAL_PLACES, MIN_CRITERIA, MAX_CRITERIA,
    PRESET_EMPTY, PRESET_SUPERSTORE, PRESET_LAPTOP, PRESET_BEASISWA
)
from engine.models import Criterion


def _format_pct(v: float, dp: int) -> str:
    return f"{v:.{dp}%}"


def render_tab_problem(state: dict) -> None:
    """
    Render Tab 1: Definisi Masalah.
    Memperbarui state['problem_info'] dan state['kriteria_list'].
    """
    st.markdown("### 📋 Informasi Kasus")
    col1, col2 = st.columns(2)
    with col1:
        state["nama_kasus"] = st.text_input(
            "Nama Kasus / Judul",
            value=state.get("nama_kasus", ""),
            placeholder="mis. Pemilihan Laptop Terbaik",
            key="input_nama_kasus",
        )
        state["pengambil_keputusan"] = st.text_input(
            "Pengambil Keputusan",
            value=state.get("pengambil_keputusan", ""),
            placeholder="mis. Komite Pemilihan",
            key="input_pk",
        )
    with col2:
        state["tujuan"] = st.text_area(
            "Tujuan Pengambilan Keputusan",
            value=state.get("tujuan", ""),
            height=68,
            placeholder="mis. Memilih laptop dengan nilai terbaik untuk mahasiswa",
            key="input_tujuan",
        )
        state["sumber_data"] = st.text_input(
            "Sumber Data",
            value=state.get("sumber_data", ""),
            placeholder="mis. Survei pasar 2024",
            key="input_sumber",
        )

    st.divider()

    # ---- EDITOR KRITERIA ----
    st.markdown("### ⚙️ Kriteria")
    st.caption("Tambah/hapus baris di bawah. Bobot input bebas (mis. 20/30/50 atau 0,35/0,30/0,20/0,15).")

    # Buat DataFrame dari state
    kriteria_list: list[Criterion] = state.get("kriteria_list", [])
    df_crit = pd.DataFrame([
        {
            "Kode": k.kode,
            "Nama Kriteria": k.nama,
            "Tipe": k.tipe,
            "Bobot Input": k.bobot_input,
            "Alasan Bobot": k.alasan,
        }
        for k in kriteria_list
    ])

    edited = st.data_editor(
        df_crit,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_kriteria",
        column_config={
            "Kode": st.column_config.TextColumn("Kode", width="small"),
            "Nama Kriteria": st.column_config.TextColumn("Nama Kriteria", width="medium"),
            "Tipe": st.column_config.SelectboxColumn(
                "Tipe", options=[BENEFIT, COST], width="small"
            ),
            "Bobot Input": st.column_config.NumberColumn(
                "Bobot Input", min_value=0.0001, format="%.4f", width="small"
            ),
            "Alasan Bobot": st.column_config.TextColumn("Alasan Bobot", width="large"),
        },
        hide_index=True,
    )

    # Perbarui state dari editor
    new_kriteria: list[Criterion] = []
    errors_crit: list[str] = []

    for i, row in edited.iterrows():
        kode = str(row.get("Kode", f"C{i+1}")).strip()
        if not kode:
            kode = f"C{i+1}"
        nama = str(row.get("Nama Kriteria", "")).strip()
        if not nama:
            nama = kode
        tipe = str(row.get("Tipe", BENEFIT))
        if tipe not in (BENEFIT, COST):
            tipe = BENEFIT
        try:
            bobot = float(row.get("Bobot Input", 1.0))
            if bobot <= 0:
                errors_crit.append(f"Bobot '{kode}' harus > 0.")
                bobot = 1.0
        except (ValueError, TypeError):
            bobot = 1.0
        alasan = str(row.get("Alasan Bobot", "")).strip()
        new_kriteria.append(Criterion(kode, nama, tipe, bobot, alasan))

    state["kriteria_list"] = new_kriteria

    # Validasi
    if errors_crit:
        for e in errors_crit:
            st.warning(f"⚠️ {e}")

    n = len(new_kriteria)
    if n < MIN_CRITERIA:
        st.error(f"❌ Minimal {MIN_CRITERIA} kriteria diperlukan. Saat ini: {n}.")
    elif n > MAX_CRITERIA:
        st.warning(f"⚠️ Maksimal {MAX_CRITERIA} kriteria direkomendasikan. Saat ini: {n}.")

    # ---- BOBOT TERNORMALISASI ----
    if n >= MIN_CRITERIA:
        total_input = sum(k.bobot_input for k in new_kriteria)
        bobot_norm = [k.bobot_input / total_input for k in new_kriteria]

        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("**Bobot Ternormalisasi:**")
            norm_data = pd.DataFrame({
                "Kode": [k.kode for k in new_kriteria],
                "Nama": [k.nama for k in new_kriteria],
                "Bobot Input": [k.bobot_input for k in new_kriteria],
                "w (Normalisasi)": [round(w, 6) for w in bobot_norm],
            })
            st.dataframe(norm_data, use_container_width=True, hide_index=True)
            dp = state.get("decimal_places", DEFAULT_DECIMAL_PLACES)
            st.success(f"✅ Total bobot = 1.0000 (Σw = {sum(bobot_norm):.{dp}f})")

        with c2:
            # Donut chart bobot
            fig = go.Figure(go.Pie(
                labels=[k.nama for k in new_kriteria],
                values=bobot_norm,
                hole=0.5,
                textinfo="label+percent",
                marker_colors=px.colors.sequential.Teal,
            ))
            fig.update_layout(
                title="Distribusi Bobot Kriteria",
                height=300,
                margin=dict(t=40, b=10, l=10, r=10),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, key="chart_bobot_donut")

    st.divider()

    # ---- DAFTAR ALTERNATIF ----
    st.markdown("### 🏢 Alternatif")
    st.caption("Satu nama per baris. Nama harus unik.")

    alternatif = state.get("alternatif", [])
    alt_text = "\n".join(alternatif)
    alt_input = st.text_area(
        "Daftar Alternatif (satu nama per baris)",
        value=alt_text,
        height=120,
        key="input_alternatif",
        placeholder="mis.\nWest\nEast\nCentral\nSouth",
    )
    alt_list = [a.strip() for a in alt_input.split("\n") if a.strip()]

    if len(alt_list) < 2:
        st.error("❌ Minimal 2 alternatif diperlukan.")
    elif len(set(alt_list)) < len(alt_list):
        st.error("❌ Nama alternatif harus unik. Terdapat duplikat.")
    else:
        st.success(f"✅ {len(alt_list)} alternatif terdaftar.")

    state["alternatif"] = alt_list
