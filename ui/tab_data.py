"""
Komponen UI untuk Tab 2: Data (Matriks Keputusan).
Mendukung penambahan baris alternatif tanpa batas (dinamis),
kolom alternatif eksplisit, upload Excel/CSV, dan template fleksibel.
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
    Evaluasi rumus sederhana dari kolom lain secara aman.
    Hanya mendukung operator +, -, *, /, tanda kurung, dan nama kolom.
    """
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


def _buat_template_kosong(kriteria_list: list[Criterion], alternatif_awal: list[str] | None = None) -> bytes:
    """
    Buat template Excel kosong untuk diunduh.
    Menyediakan kolom 'Alternatif' dan contoh 10 baris agar pengguna tahu
    jumlah baris tidak terbatas dan bisa ditambah sebanyak apa pun.
    """
    if alternatif_awal and len(alternatif_awal) >= 5:
        sample_alts = list(alternatif_awal)
    else:
        sample_alts = [
            "Wilayah / Alternatif 1",
            "Wilayah / Alternatif 2",
            "Wilayah / Alternatif 3",
            "Wilayah / Alternatif 4",
            "Wilayah / Alternatif 5",
            "Wilayah / Alternatif 6",
            "Wilayah / Alternatif 7",
            "Wilayah / Alternatif 8",
            "Wilayah / Alternatif 9",
            "Wilayah / Alternatif 10",
        ]

    data = {"Alternatif": sample_alts}
    for k in kriteria_list:
        data[k.kode] = [np.nan] * len(sample_alts)

    df = pd.DataFrame(data)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Data", index=False)
        # Petunjuk di sheet terpisah
        df_petunjuk = pd.DataFrame({
            "Kolom": ["Alternatif"] + [k.kode for k in kriteria_list],
            "Keterangan": ["Nama objek yang dinilai (Wilayah, Produk, Vendor, dll.)"] + [
                f"{k.nama} ({k.tipe}, bobot input: {k.bobot_input})" for k in kriteria_list
            ],
            "Catatan": ["Anda bisa menambah baris sebanyak apa pun (tidak terbatas)"] + ["Isi dengan angka numerik" for _ in kriteria_list]
        })
        df_petunjuk.to_excel(writer, sheet_name="Petunjuk", index=False)
    return buf.getvalue()


def render_tab_data(state: dict) -> None:
    """
    Render Tab 2: Data (Matriks Keputusan).
    Mendukung kolom nama alternatif langsung di tabel dan baris tak terbatas.
    """
    kriteria_list: list[Criterion] = state.get("kriteria_list", [])
    if len(kriteria_list) < 2:
        st.warning("⚠️ Tambahkan minimal 2 kriteria di Tab 1 terlebih dahulu.")
        return

    kode_list = [k.kode for k in kriteria_list]

    # Ambil alternatif dari state; jika belum ada, berikan 4 alternatif default
    alternatif_list: list[str] = state.get("alternatif", [])
    if not alternatif_list:
        alternatif_list = ["Alternatif 1", "Alternatif 2", "Alternatif 3", "Alternatif 4"]
        state["alternatif"] = alternatif_list

    # ---- PETUNJUK PENGGUNAAN ----
    st.info(
        "💡 **Fleksibel & Dinamis:** Anda bisa langsung mengetik nama alternatif (Wilayah, Produk, Pelanggan, dll.) "
        "di kolom pertama **Alternatif**, serta menambah baris baru sebanyak apa pun dengan tombol **`+` (Add row)** "
        "di bagian bawah tabel."
    )

    # ---- 1. KOLOM TURUNAN ----
    kolom_turunan: dict[str, str] = state.get("kolom_turunan", {})
    with st.expander("🔧 Kolom Turunan / Rumus Otomatis (Opsional)", expanded=bool(kolom_turunan)):
        st.caption(
            "Definisikan kolom yang dihitung dari kolom lain secara otomatis. "
            "Contoh: `C3 = C2 / C1 * 100`. Operator yang didukung: `+ - * /`"
        )
        col_kiri, col_kanan = st.columns([1, 2])
        with col_kiri:
            kolom_target = st.selectbox(
                "Kolom Turunan", kode_list, key="sel_kolom_turunan"
            )
        with col_kanan:
            rumus = st.text_input(
                "Rumus (gunakan kode kriteria)",
                value=kolom_turunan.get(kolom_target, ""),
                placeholder=f"mis. C2 / C1 * 100",
                key="input_rumus_turunan",
            )
        c1, c2, _ = st.columns([1, 1, 2])
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

    # ---- 2. UPLOAD & DOWNLOAD TEMPLATE ----
    with st.expander("📤 Upload File Excel / CSV & Unduh Template", expanded=False):
        col_up, col_dl = st.columns([3, 2])
        with col_dl:
            st.markdown("**Belum punya format Excel?**")
            st.caption("Unduh template dengan kolom yang sudah sesuai:")
            template_bytes = _buat_template_kosong(kriteria_list, alternatif_list)
            st.download_button(
                "⬇️ Unduh Template Excel (.xlsx)",
                data=template_bytes,
                file_name="template_matriks_dss.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_template_btn",
                use_container_width=True,
            )

        with col_up:
            st.markdown("**Upload Data dari Excel/CSV**")
            uploaded = st.file_uploader(
                "Pilih file (.xlsx atau .csv)",
                type=["xlsx", "csv"],
                key="upload_data_file",
            )

        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    df_up = pd.read_csv(uploaded)
                else:
                    df_up = pd.read_excel(uploaded)

                st.markdown("**Pratinjau Data:**")
                st.dataframe(df_up.head(8), use_container_width=True)

                cols_upload = list(df_up.columns)
                # Pemetaan kolom alternatif
                col_alt_pilihan = st.selectbox(
                    "Pilih Kolom yang Berisi Nama Alternatif (Wilayah/Produk/dll):",
                    cols_upload,
                    index=0,
                    key="map_col_alt",
                )

                st.markdown("**Pemetaan Kolom Kriteria:**")
                mapping_crit = {}
                col_crit_grid = st.columns(min(3, len(kriteria_list)))
                for idx_k, k in enumerate(kriteria_list):
                    with col_crit_grid[idx_k % len(col_crit_grid)]:
                        default_idx = 0
                        if k.kode in cols_upload:
                            default_idx = cols_upload.index(k.kode)
                        elif k.nama in cols_upload:
                            default_idx = cols_upload.index(k.nama)
                        pil = st.selectbox(
                            f"Kriteria {k.kode} ({k.nama})",
                            ["(Kosongkan)"] + cols_upload,
                            index=default_idx + 1 if (k.kode in cols_upload or k.nama in cols_upload) else 0,
                            key=f"map_k_{k.kode}",
                        )
                        if pil != "(Kosongkan)":
                            mapping_crit[k.kode] = pil

                if st.button("🚀 Terapkan Data Upload ke Matriks", key="btn_apply_upload_matrix", type="primary"):
                    new_alts = df_up[col_alt_pilihan].dropna().astype(str).tolist()
                    matriks_uploaded = pd.DataFrame(index=new_alts)
                    for k_kode in kode_list:
                        if k_kode in mapping_crit:
                            src_col = mapping_crit[k_kode]
                            matriks_uploaded[k_kode] = pd.to_numeric(df_up[src_col], errors="coerce").values[:len(new_alts)]
                        else:
                            matriks_uploaded[k_kode] = np.nan

                    state["alternatif"] = new_alts
                    state["matriks_raw"] = matriks_uploaded
                    state["_last_alts"] = list(new_alts)
                    state["alt_version"] = state.get("alt_version", 0) + 1
                    st.success(f"✅ Berhasil memuat {len(new_alts)} baris alternatif dari file!")
                    st.rerun()

            except Exception as ex:
                st.error(f"❌ Gagal memproses file upload: {ex}")

    # ---- 3. MATRIKS KEPUTUSAN INTERAKTIF ----
    st.markdown("### 📊 Matriks Keputusan")
    st.caption("Ketik langsung nama alternatif dan nilai kriteria. Tekan baris baru untuk menambah data tanpa batas.")

    matriks_raw: pd.DataFrame = state.get("matriks_raw", pd.DataFrame())

    # Siapkan DataFrame untuk editor dengan kolom pertama: Alternatif
    df_rows = []
    for i, alt in enumerate(alternatif_list):
        row_data = {"Alternatif": str(alt)}
        for kode in kode_list:
            if alt in matriks_raw.index and kode in matriks_raw.columns:
                row_data[kode] = matriks_raw.loc[alt, kode]
            else:
                row_data[kode] = np.nan
        df_rows.append(row_data)

    df_edit = pd.DataFrame(df_rows)
    if "Alternatif" not in df_edit.columns:
        df_edit["Alternatif"] = alternatif_list

    # Konfigurasi kolom
    col_config = {
        "Alternatif": st.column_config.TextColumn(
            "Alternatif (Wilayah / Produk / Vendor / dll)",
            help="Nama alternatif yang dinilai / diperingkat",
            width="medium",
            required=True,
        )
    }

    for k in kriteria_list:
        if k.kode in kolom_turunan:
            col_config[k.kode] = st.column_config.NumberColumn(
                f"{k.kode} - {k.nama} [Rumus]",
                help=f"Kolom turunan dihitung otomatis: {kolom_turunan[k.kode]}",
                disabled=True,
                format="%.4f",
            )
        else:
            col_config[k.kode] = st.column_config.NumberColumn(
                f"{k.kode} - {k.nama} ({k.tipe})",
                help=f"Tipe: {k.tipe}, Bobot input: {k.bobot_input}",
                format="%.4f",
            )

    # st.data_editor dengan num_rows="dynamic" (baris dinamis & tak terbatas)
    edited_matrix = st.data_editor(
        df_edit,
        use_container_width=True,
        num_rows="dynamic",
        key="editor_matriks_dinamis",
        column_config=col_config,
        hide_index=True,
    )

    # Ekstraksi alternatif dan nilai kriteria
    alt_col = edited_matrix["Alternatif"].fillna("").astype(str).str.strip().tolist()

    valid_indices = []
    final_alts = []
    for idx_row, name in enumerate(alt_col):
        # Periksa apakah ada nama atau nilai di baris tersebut
        vals = edited_matrix.iloc[idx_row][kode_list].dropna()
        if name or len(vals) > 0:
            alt_name = name if name else f"Alternatif {idx_row + 1}"
            final_alts.append(alt_name)
            valid_indices.append(idx_row)

    # Tangani deduplikasi jika ada nama yang identik
    seen_names = {}
    deduped_alts = []
    for a in final_alts:
        if a in seen_names:
            seen_names[a] += 1
            deduped_alts.append(f"{a} ({seen_names[a]})")
        else:
            seen_names[a] = 1
            deduped_alts.append(a)

    if len(deduped_alts) >= 2:
        matriks_numeric = edited_matrix.iloc[valid_indices][kode_list].copy().astype(float)
        matriks_numeric.index = deduped_alts

        # Evaluasi kolom turunan
        input_cols = {k: matriks_numeric[k] for k in kode_list if k not in kolom_turunan}
        df_eval_input = pd.DataFrame(input_cols, index=deduped_alts)

        for kode_t, rumus_t in kolom_turunan.items():
            hasil_t = _evaluasi_rumus_aman(rumus_t, df_eval_input)
            if hasil_t is not None:
                matriks_numeric[kode_t] = hasil_t.values
            else:
                st.warning(f"⚠️ Rumus '{rumus_t}' untuk '{kode_t}' menghasilkan galat atau tidak valid.")

        state["alternatif"] = deduped_alts
        state["matriks_raw"] = matriks_numeric
        if deduped_alts != state.get("_last_alts"):
            state["_last_alts"] = list(deduped_alts)
            state["alt_version"] = state.get("alt_version", 0) + 1

        # Tampilkan jika ada kolom turunan
        if kolom_turunan:
            st.markdown("**Matriks Final (termasuk hasil kolom rumus):**")
            st.dataframe(matriks_numeric.style.format("{:.4f}"), use_container_width=True)

        # ---- VALIDASI DATA ----
        st.markdown("### 🔍 Validasi Data")
        has_error = False

        errors_mat = validasi_matriks(matriks_numeric, deduped_alts, kode_list)
        for e in errors_mat:
            st.error(f"❌ {e}")
            has_error = True

        warn_konstan = periksa_kolom_konstan(matriks_numeric, kode_list)
        for w in warn_konstan:
            st.warning(f"⚠️ {w}")

        warn_wp = periksa_nilai_wp(matriks_numeric, [k.tipe for k in kriteria_list], kode_list)
        for w in warn_wp:
            st.warning(f"⚠️ {w}")

        warn_out = periksa_outlier(matriks_numeric, kode_list)
        for w in warn_out:
            st.info(f"ℹ️ {w}")

        if not has_error:
            st.success(f"✅ Data siap dihitung: {len(deduped_alts)} alternatif × {len(kode_list)} kriteria.")
            try:
                problem = Problem(
                    nama_kasus=state.get("nama_kasus", "Masalah MADM"),
                    alternatif=deduped_alts,
                    kriteria=kriteria_list,
                    matriks=matriks_numeric,
                    pengambil_keputusan=state.get("pengambil_keputusan", ""),
                    tujuan=state.get("tujuan", ""),
                    sumber_data=state.get("sumber_data", ""),
                )
                state["problem"] = problem
            except Exception as err:
                st.error(f"❌ Galat pembuatan Problem: {err}")
                state["problem"] = None
        else:
            state["problem"] = None

    else:
        st.warning(f"⚠️ Minimal 2 alternatif diperlukan. Saat ini terisi: {len(deduped_alts)} baris.")
        state["problem"] = None
