"""
Komponen UI untuk Tab 2: Data (Matriks Keputusan).
"""
from __future__ import annotations

import io
import re
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st

from engine.models import Criterion, Problem
from engine.validators import (
    validasi_matriks, periksa_nilai_wp, periksa_kolom_konstan, periksa_outlier
)
from config import DEFAULT_REPLACEMENT_VALUE


def _evaluasi_rumus_aman(ekspresi: str, df: pd.DataFrame) -> Optional[pd.Series]:
    """
    Evaluasi rumus sederhana dari kolom lain.
    Hanya mendukung: +, -, *, /, dan nama kolom.
    TIDAK menggunakan eval() pada input mentah; menggunakan pandas.eval terbatas.

    Parameters
    ----------
    ekspresi : str
        Mis. "C2 / C1 * 100"
    df : pd.DataFrame
        DataFrame tempat kolom dicari.

    Returns
    -------
    pd.Series atau None
    """
    # Bersihkan ekspresi: hanya izinkan karakter aman
    ekspresi_bersih = ekspresi.strip()
    pattern_aman = re.compile(r'^[\w\s\+\-\*\/\(\)\.]+$')
    if not pattern_aman.match(ekspresi_bersih):
        return None
    try:
        result = df.eval(ekspresi_bersih)
        if isinstance(result, pd.Series):
            return result
        return None
    except Exception:
        return None


def _buat_template_kosong(alternatif: list[str], kriteria_list: list[Criterion]) -> bytes:
    """Buat template Excel kosong untuk diunduh."""
    df = pd.DataFrame(
        index=alternatif,
        columns=[k.kode for k in kriteria_list],
    )
    df.index.name = "Alternatif"
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Data")
    return buf.getvalue()


def render_tab_data(state: dict) -> None:
    """
    Render Tab 2: Data (Matriks Keputusan).
    Memperbarui state['matriks'] dan state['problem'].
    """
    kriteria_list: list[Criterion] = state.get("kriteria_list", [])
    alternatif: list[str] = state.get("alternatif", [])

    if len(kriteria_list) < 2:
        st.warning("⚠️ Tambahkan minimal 2 kriteria di Tab 1 terlebih dahulu.")
        return
    if len(alternatif) < 2:
        st.warning("⚠️ Tambahkan minimal 2 alternatif di Tab 1 terlebih dahulu.")
        return

    kode_list = [k.kode for k in kriteria_list]

    # ---- KOLOM TURUNAN ----
    kolom_turunan: dict[str, str] = state.get("kolom_turunan", {})
    with st.expander("🔧 Kolom Turunan (Opsional)", expanded=bool(kolom_turunan)):
        st.caption(
            "Definisikan kolom yang dihitung dari kolom lain. "
            "Contoh: `C3 = C2 / C1 * 100`. "
            "Operator yang diizinkan: `+ - * /`"
        )
        kode_turunan_opts = kode_list
        col_kiri, col_kanan = st.columns([1, 2])
        with col_kiri:
            kolom_target = st.selectbox(
                "Kolom Turunan", kode_turunan_opts, key="sel_kolom_turunan"
            )
        with col_kanan:
            rumus = st.text_input(
                "Rumus (gunakan kode kolom lain)",
                value=kolom_turunan.get(kolom_target, ""),
                placeholder=f"mis. C2 / C1 * 100",
                key="input_rumus_turunan",
            )
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            if st.button("Simpan Rumus", key="btn_simpan_rumus"):
                if rumus.strip():
                    kolom_turunan[kolom_target] = rumus.strip()
                    st.success(f"Rumus '{kolom_target} = {rumus}' disimpan.")
        with c2:
            if st.button("Hapus Rumus", key="btn_hapus_rumus"):
                kolom_turunan.pop(kolom_target, None)
                st.info(f"Rumus untuk '{kolom_target}' dihapus.")
        if kolom_turunan:
            st.markdown("**Rumus aktif:**")
            for k, v in kolom_turunan.items():
                st.code(f"{k} = {v}")
        state["kolom_turunan"] = kolom_turunan

    # ---- UPLOAD DATA ----
    with st.expander("📤 Upload Data dari File (.xlsx / .csv)", expanded=False):
        uploaded = st.file_uploader(
            "Upload file (alternatif di kolom pertama, kriteria di kolom berikutnya)",
            type=["xlsx", "csv"],
            key="upload_data",
        )
        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    df_up = pd.read_csv(uploaded, index_col=0)
                else:
                    df_up = pd.read_excel(uploaded, index_col=0)
                st.markdown("**Pratinjau data yang diupload:**")
                st.dataframe(df_up.head(10), use_container_width=True)

                # Pemetaan kolom
                st.markdown("**Pemetaan kolom ke kriteria:**")
                mapping = {}
                cols_upload = list(df_up.columns)
                for k in kriteria_list:
                    pil = st.selectbox(
                        f"Kolom untuk '{k.kode} - {k.nama}'",
                        ["(tidak dipetakan)"] + cols_upload,
                        key=f"map_{k.kode}",
                    )
                    if pil != "(tidak dipetakan)":
                        mapping[k.kode] = pil

                if st.button("Terapkan Upload", key="btn_apply_upload"):
                    matriks_baru = pd.DataFrame(index=df_up.index)
                    for kode, col_src in mapping.items():
                        matriks_baru[kode] = pd.to_numeric(df_up[col_src], errors="coerce")
                    state["matriks_raw"] = matriks_baru
                    state["alternatif"] = list(df_up.index.astype(str))
                    st.success("✅ Data berhasil diterapkan.")
            except Exception as e:
                st.error(f"❌ Gagal membaca file: {e}")

        # Tombol unduh template
        template_bytes = _buat_template_kosong(alternatif, kriteria_list)
        st.download_button(
            "⬇️ Unduh Template Kosong",
            data=template_bytes,
            file_name="template_dss.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_template",
        )

    # ---- EDITOR MATRIKS ----
    st.markdown("### 📊 Matriks Keputusan")

    # Bangun DataFrame awal dari state atau default
    matriks_raw: pd.DataFrame = state.get("matriks_raw", pd.DataFrame())

    # Sesuaikan index ke alternatif aktif
    df_edit = pd.DataFrame(index=alternatif, columns=kode_list, dtype=float)
    for alt in alternatif:
        for kode in kode_list:
            if alt in matriks_raw.index and kode in matriks_raw.columns:
                df_edit.loc[alt, kode] = matriks_raw.loc[alt, kode]
            else:
                df_edit.loc[alt, kode] = np.nan

    # Kolom turunan: tandai sebagai read-only
    col_config = {}
    disabled_cols = []
    for k in kriteria_list:
        if k.kode in kolom_turunan:
            col_config[k.kode] = st.column_config.NumberColumn(
                f"{k.kode} {k.nama} [Turunan]",
                disabled=True,
                format="%.4f",
            )
            disabled_cols.append(k.kode)
        else:
            col_config[k.kode] = st.column_config.NumberColumn(
                f"{k.kode} {k.nama} ({k.tipe})",
                format="%.4f",
            )

    edited_matrix = st.data_editor(
        df_edit,
        use_container_width=True,
        num_rows="fixed",
        key="editor_matriks",
        column_config=col_config,
    )

    # Hitung kolom turunan
    matriks_final = edited_matrix.copy().astype(float)

    # Hitung kolom turunan dari kolom input terlebih dahulu
    input_cols = {k: matriks_final[k] for k in kode_list if k not in kolom_turunan}
    df_untuk_eval = pd.DataFrame(input_cols, index=alternatif)
    for kode_t, rumus_t in kolom_turunan.items():
        hasil_t = _evaluasi_rumus_aman(rumus_t, df_untuk_eval)
        if hasil_t is not None:
            matriks_final[kode_t] = hasil_t.values
            st.caption(f"ℹ️ Kolom '{kode_t}' dihitung dari rumus: `{rumus_t}`")
        else:
            st.warning(f"⚠️ Rumus '{rumus_t}' untuk '{kode_t}' tidak valid atau error.")

    state["matriks_raw"] = matriks_final

    # ---- TAMPILKAN MATRIKS FINAL ----
    if kolom_turunan:
        st.markdown("**Matriks Lengkap (termasuk kolom turunan):**")
        st.dataframe(matriks_final.style.format("{:.4f}"), use_container_width=True)

    # ---- VALIDASI ----
    st.markdown("### 🔍 Validasi Data")
    has_error = False
    has_warning = False

    # Cek nilai kosong
    errors_mat = validasi_matriks(matriks_final, alternatif, kode_list)
    for e in errors_mat:
        st.error(f"❌ {e}")
        has_error = True

    # Cek kolom konstan
    warn_konstan = periksa_kolom_konstan(matriks_final, kode_list)
    for w in warn_konstan:
        st.warning(f"⚠️ {w}")
        has_warning = True

    # Cek nilai <= 0 untuk WP
    warn_wp = periksa_nilai_wp(matriks_final, [k.tipe for k in kriteria_list], kode_list)
    for w in warn_wp:
        st.warning(f"⚠️ {w}")
        has_warning = True

    # Cek outlier
    warn_out = periksa_outlier(matriks_final, kode_list)
    for w in warn_out:
        st.info(f"ℹ️ Outlier potensial: {w}")

    if not has_error and not has_warning:
        st.success("✅ Data valid dan siap dihitung.")
    elif not has_error:
        st.info("ℹ️ Data mengandung peringatan di atas. Perhitungan tetap bisa dilanjutkan.")

    # ---- BUAT PROBLEM ----
    if not has_error and len(alternatif) >= 2 and len(kriteria_list) >= 2:
        try:
            matriks_idx = matriks_final.copy()
            matriks_idx.index = alternatif
            problem = Problem(
                nama_kasus=state.get("nama_kasus", "Masalah DSS"),
                alternatif=alternatif,
                kriteria=kriteria_list,
                matriks=matriks_idx,
                pengambil_keputusan=state.get("pengambil_keputusan", ""),
                tujuan=state.get("tujuan", ""),
                sumber_data=state.get("sumber_data", ""),
            )
            state["problem"] = problem
        except Exception as e:
            st.error(f"❌ Gagal membuat objek Problem: {e}")
            state["problem"] = None
    else:
        state["problem"] = None
