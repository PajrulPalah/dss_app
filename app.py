"""
DSS Calculator Engine — Entry Point Streamlit
Aplikasi simulasi MADM (SAW dan WP) berbahasa Indonesia.
Jalankan: streamlit run app.py
"""
from __future__ import annotations

import json
import sys
import os

# Pastikan direktori dss_app ada di path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
import streamlit as st

from config import (
    BENEFIT, COST, DEFAULT_DECIMAL_PLACES, DEFAULT_REPLACEMENT_VALUE,
    PRESET_EMPTY, PRESET_SUPERSTORE, PRESET_LAPTOP, PRESET_BEASISWA,
    COLOR_PRIMARY, COLOR_ACCENT,
)
from engine.models import Criterion, Problem

# ==================== KONFIGURASI HALAMAN ====================
st.set_page_config(
    page_title="DSS Calculator Engine",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "DSS Calculator Engine v1.0 — Alat MADM (SAW & WP) Berbahasa Indonesia",
    },
)

# ==================== CSS KUSTOM ====================
st.markdown(
    f"""
    <style>
    .main .block-container {{ padding-top: 1rem; }}
    h1 {{ color: {COLOR_PRIMARY}; }}
    h2 {{ color: {COLOR_PRIMARY}; border-bottom: 2px solid {COLOR_ACCENT}; padding-bottom: 4px; }}
    h3 {{ color: {COLOR_PRIMARY}; }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        background-color: {COLOR_ACCENT};
        border-radius: 8px;
        padding: 4px;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 6px;
        font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {COLOR_PRIMARY};
        color: white;
    }}
    .metric-container {{ background-color: {COLOR_ACCENT}; border-radius: 8px; padding: 8px; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================== MUAT PRESET ====================
def _muat_preset_json(nama_file: str) -> dict:
    """Muat file preset JSON dari folder presets/."""
    path = os.path.join(os.path.dirname(__file__), "presets", nama_file)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _terapkan_preset(state: dict, nama_preset: str) -> None:
    """Terapkan data preset ke session state."""
    if nama_preset == PRESET_EMPTY:
        state["nama_kasus"] = ""
        state["pengambil_keputusan"] = ""
        state["tujuan"] = ""
        state["sumber_data"] = ""
        state["alternatif"] = ["A1", "A2", "A3"]
        state["kriteria_list"] = [
            Criterion("C1", "Kriteria 1", BENEFIT, 1.0),
            Criterion("C2", "Kriteria 2", BENEFIT, 1.0),
        ]
        state["matriks_raw"] = pd.DataFrame()
        state["kolom_turunan"] = {}
        state["problem"] = None
        state["hasil_saw"] = None
        state["hasil_wp"] = None
        return

    file_map = {
        PRESET_SUPERSTORE: "superstore.json",
        PRESET_LAPTOP: "laptop.json",
        PRESET_BEASISWA: "beasiswa.json",
    }
    fname = file_map.get(nama_preset)
    if not fname:
        return

    data = _muat_preset_json(fname)
    if not data:
        st.error(f"❌ Gagal memuat preset '{nama_preset}'.")
        return

    state["nama_kasus"] = data.get("nama_kasus", "")
    state["pengambil_keputusan"] = data.get("pengambil_keputusan", "")
    state["tujuan"] = data.get("tujuan", "")
    state["sumber_data"] = data.get("sumber_data", "")
    state["alternatif"] = data.get("alternatif", [])
    state["kolom_turunan"] = data.get("kolom_turunan", {})

    kriteria_raw = data.get("kriteria", [])
    state["kriteria_list"] = [
        Criterion(
            kode=k["kode"],
            nama=k["nama"],
            tipe=k["tipe"],
            bobot_input=k["bobot_input"],
            alasan=k.get("alasan", ""),
        )
        for k in kriteria_raw
    ]

    # Bangun matriks
    alternatif = state["alternatif"]
    kode_list = [k.kode for k in state["kriteria_list"]]
    matriks_data = data.get("matriks", {})

    # Hitung nilai turunan
    matriks_dict = {}
    kolom_turunan = state["kolom_turunan"]

    # Pertama, isi kolom non-turunan
    for kode in kode_list:
        if kode not in kolom_turunan:
            col_data = matriks_data.get(kode, {})
            matriks_dict[kode] = [col_data.get(alt, np.nan) for alt in alternatif]

    df_input = pd.DataFrame(matriks_dict, index=alternatif)

    # Hitung kolom turunan dengan pandas.eval
    for kode_t, rumus_t in kolom_turunan.items():
        try:
            col_result = df_input.eval(rumus_t)
            df_input[kode_t] = col_result
        except Exception:
            df_input[kode_t] = np.nan

    # Pastikan semua kolom ada
    for kode in kode_list:
        if kode not in df_input.columns:
            df_input[kode] = np.nan

    state["matriks_raw"] = df_input[kode_list].astype(float)
    state["problem"] = None
    state["hasil_saw"] = None
    state["hasil_wp"] = None
    state["skenario_list"] = []

    # Skenario sensitivitas dari preset
    if "skenario_sensitivitas" in data:
        state["skenario_list"] = [
            {"nama": sk["nama"], "bobot": sk["bobot_input"]}
            for sk in data["skenario_sensitivitas"]
        ]

    # Pengaturan WP dari preset
    state["strategi_zero"] = data.get("strategi_zero", "ganti")
    state["nilai_pengganti"] = data.get("nilai_pengganti", DEFAULT_REPLACEMENT_VALUE)

    # Metode
    metode_preset = data.get("metode", "Keduanya")
    state["metode_hitung"] = metode_preset


# ==================== INISIALISASI SESSION STATE ====================
def _init_state() -> dict:
    """Inisialisasi atau kembalikan session state."""
    if "dss_state" not in st.session_state:
        st.session_state["dss_state"] = {
            "nama_kasus": "",
            "pengambil_keputusan": "",
            "tujuan": "",
            "sumber_data": "",
            "alternatif": ["A1", "A2", "A3"],
            "kriteria_list": [
                Criterion("C1", "Kriteria 1", BENEFIT, 1.0),
                Criterion("C2", "Kriteria 2", BENEFIT, 1.0),
            ],
            "matriks_raw": pd.DataFrame(),
            "kolom_turunan": {},
            "problem": None,
            "hasil_saw": None,
            "hasil_wp": None,
            "metode_hitung": "Keduanya",
            "decimal_places": DEFAULT_DECIMAL_PLACES,
            "tampil_rinci": True,
            "strategi_zero": "ganti",
            "nilai_pengganti": DEFAULT_REPLACEMENT_VALUE,
            "skenario_list": [],
            "hasil_skenario": None,
            "hasil_sweep": None,
            "hasil_mc": None,
            "teks_kesimpulan": "",
            "preset_aktif": PRESET_EMPTY,
        }
    return st.session_state["dss_state"]


# ==================== SIDEBAR ====================
def _render_sidebar(state: dict) -> None:
    """Render sidebar dengan pengaturan utama."""
    with st.sidebar:
        st.markdown(
            f"<h2 style='color:{COLOR_PRIMARY};text-align:center;'>🧮 DSS Engine</h2>",
            unsafe_allow_html=True,
        )
        st.caption("Multi-Attribute Decision Making (MADM)")
        st.divider()

        # Pilih metode
        metode = st.selectbox(
            "⚙️ Metode Perhitungan",
            ["SAW", "WP", "Keduanya"],
            index=["SAW", "WP", "Keduanya"].index(state.get("metode_hitung", "Keduanya")),
            key="sb_metode",
        )
        state["metode_hitung"] = metode

        st.divider()

        # Pilih preset
        st.markdown("**📂 Preset Contoh Data**")
        preset_options = [PRESET_EMPTY, PRESET_SUPERSTORE, PRESET_LAPTOP, PRESET_BEASISWA]
        preset_sel = st.selectbox(
            "Pilih Preset",
            preset_options,
            index=preset_options.index(state.get("preset_aktif", PRESET_EMPTY)),
            key="sb_preset",
        )

        if st.button("✅ Terapkan Preset", key="btn_preset", use_container_width=True):
            _terapkan_preset(state, preset_sel)
            state["preset_aktif"] = preset_sel
            st.success(f"Preset '{preset_sel}' diterapkan!")
            st.rerun()

        st.divider()

        # Pengaturan lanjutan
        with st.expander("🔧 Pengaturan Lanjutan", expanded=False):
            state["decimal_places"] = st.number_input(
                "Jumlah Desimal Tampilan",
                min_value=2, max_value=8,
                value=state.get("decimal_places", DEFAULT_DECIMAL_PLACES),
                key="adv_dp",
            )
            state["tampil_rinci"] = st.toggle(
                "Tampilkan Langkah Rinci",
                value=state.get("tampil_rinci", True),
                key="adv_rinci",
            )
            st.markdown("**Penanganan Nilai ≤ 0 (WP):**")
            strategi_opts = {"ganti": "Ganti dengan nilai pengganti", "geser": "Geser seluruh kolom", "tolak": "Tolak dan tampilkan error"}
            strategi_val = state.get("strategi_zero", "ganti")
            state["strategi_zero"] = st.selectbox(
                "Strategi",
                list(strategi_opts.keys()),
                format_func=lambda k: strategi_opts[k],
                index=list(strategi_opts.keys()).index(strategi_val),
                key="adv_strategi",
            )
            state["nilai_pengganti"] = st.number_input(
                "Nilai Pengganti (untuk strategi 'ganti'/'geser')",
                min_value=0.0001, max_value=1.0,
                value=float(state.get("nilai_pengganti", DEFAULT_REPLACEMENT_VALUE)),
                format="%.4f",
                key="adv_peng",
            )

        st.divider()

        # Reset
        if st.button("🔄 Reset Semua", key="btn_reset", use_container_width=True):
            st.session_state.pop("dss_state", None)
            st.rerun()

        st.divider()
        st.caption("📦 DSS Calculator Engine v1.0")
        st.caption("🎓 Untuk Mahasiswa Magister Manajemen")


# ==================== MAIN APP ====================
def main() -> None:
    """Entry point utama aplikasi."""
    state = _init_state()
    _render_sidebar(state)

    # Header
    st.markdown(
        f"<h1 style='color:{COLOR_PRIMARY};'>🧮 DSS Calculator Engine</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Alat simulasi **Multi-Attribute Decision Making (MADM)** — SAW dan WP. "
        "Setiap langkah perhitungan ditampilkan lengkap dengan rumus dan angka antara."
    )

    metode = state.get("metode_hitung", "Keduanya")

    # Tentukan tab yang ditampilkan
    tab_names = [
        "1. Definisi Masalah",
        "2. Data",
    ]
    if metode in ("SAW", "Keduanya"):
        tab_names.append("3. Hasil SAW")
    if metode in ("WP", "Keduanya"):
        tab_names.append("4. Hasil WP")
    if metode == "Keduanya":
        tab_names.append("5. Perbandingan SAW vs WP")
    tab_names += [
        "6. Sensitivitas",
        "7. Kesimpulan & Ekspor",
        "8. Panduan & Rumus",
    ]

    tabs = st.tabs(tab_names)
    tab_idx = 0

    # Import UI komponen
    from ui.tab_problem import render_tab_problem
    from ui.tab_data import render_tab_data
    from ui.tab_saw import render_tab_saw
    from ui.tab_wp import render_tab_wp
    from ui.tab_comparison import render_tab_comparison
    from ui.tab_sensitivity import render_tab_sensitivity
    from ui.tab_conclusion import render_tab_conclusion
    from ui.tab_guide import render_tab_guide

    with tabs[tab_idx]:  # Tab 1: Definisi Masalah
        render_tab_problem(state)
    tab_idx += 1

    with tabs[tab_idx]:  # Tab 2: Data
        render_tab_data(state)
    tab_idx += 1

    if metode in ("SAW", "Keduanya"):
        with tabs[tab_idx]:  # Tab 3: Hasil SAW
            render_tab_saw(state)
        tab_idx += 1

    if metode in ("WP", "Keduanya"):
        with tabs[tab_idx]:  # Tab 4: Hasil WP
            render_tab_wp(state)
        tab_idx += 1

    if metode == "Keduanya":
        with tabs[tab_idx]:  # Tab 5: Perbandingan
            render_tab_comparison(state)
        tab_idx += 1

    with tabs[tab_idx]:  # Tab 6: Sensitivitas
        render_tab_sensitivity(state)
    tab_idx += 1

    with tabs[tab_idx]:  # Tab 7: Kesimpulan & Ekspor
        render_tab_conclusion(state)
    tab_idx += 1

    with tabs[tab_idx]:  # Tab 8: Panduan & Rumus
        render_tab_guide()


if __name__ == "__main__":
    main()
