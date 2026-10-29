"""
Komponen UI untuk Tab 7: Kesimpulan dan Ekspor.
"""
from __future__ import annotations

import io
import pandas as pd
import streamlit as st

from engine.models import Problem, SAWResult, WPResult
from engine.exporters import ekspor_excel, ekspor_csv_ranking, ekspor_markdown
from config import DEFAULT_DECIMAL_PLACES


def _kesimpulan_otomatis(
    problem: Problem,
    hasil_saw: SAWResult | None,
    hasil_wp: WPResult | None,
    dp: int,
) -> str:
    """Hasilkan teks kesimpulan otomatis berbasis data."""
    lines = [f"# Kesimpulan Analisis DSS: {problem.nama_kasus}", ""]

    # Metode yang digunakan
    metode_dipakai = []
    if hasil_saw:
        metode_dipakai.append("SAW (Simple Additive Weighting)")
    if hasil_wp:
        metode_dipakai.append("WP (Weighted Product)")
    lines.append(f"**Metode yang digunakan:** {' dan '.join(metode_dipakai)}")
    lines.append(f"**Jumlah alternatif:** {len(problem.alternatif)}")
    lines.append(f"**Jumlah kriteria:** {len(problem.kriteria)}")
    lines.append("")

    if hasil_saw:
        best_saw = hasil_saw.peringkat.idxmin()
        worst_saw = hasil_saw.peringkat.idxmax()
        lines.append(f"### Hasil SAW")
        lines.append(
            f"- **Alternatif terbaik:** {best_saw} (V = {float(hasil_saw.v.loc[best_saw]):.{dp}f})"
        )
        lines.append(
            f"- **Perlu perhatian:** {worst_saw} (V = {float(hasil_saw.v.loc[worst_saw]):.{dp}f})"
        )
        lines.append("")

    if hasil_wp:
        best_wp = hasil_wp.peringkat.idxmin()
        worst_wp = hasil_wp.peringkat.idxmax()
        lines.append(f"### Hasil WP")
        lines.append(
            f"- **Alternatif terbaik:** {best_wp} (V = {float(hasil_wp.v.loc[best_wp]):.{dp}f})"
        )
        lines.append(
            f"- **Perlu perhatian:** {worst_wp} (V = {float(hasil_wp.v.loc[worst_wp]):.{dp}f})"
        )
        if hasil_wp.sel_disesuaikan:
            lines.append(
                f"- **Catatan:** {len(hasil_wp.sel_disesuaikan)} sel dengan nilai ≤ 0 "
                f"disesuaikan untuk keperluan WP. Lihat Tab 4 untuk detail."
            )
        lines.append("")

    if hasil_saw and hasil_wp:
        best_saw = hasil_saw.peringkat.idxmin()
        best_wp = hasil_wp.peringkat.idxmin()
        if best_saw == best_wp:
            lines.append(
                f"### ✅ Rekomendasi: **{best_saw}**\n"
                f"Kedua metode sepakat. Kepercayaan pada rekomendasi ini lebih tinggi."
            )
        else:
            lines.append(
                f"### ⚠️ Ketidaksepakatan Metode\n"
                f"SAW → {best_saw}; WP → {best_wp}. "
                f"Pertimbangkan analisis sensitivitas untuk memahami penyebab perbedaan."
            )

    lines += [
        "",
        "### Kekuatan dan Keterbatasan",
        "**SAW:**",
        "- ✅ Mudah dipahami dan diterapkan",
        "- ✅ Cocok untuk kriteria dengan satuan berbeda setelah normalisasi",
        "- ⚠️ Normalisasi linear mengasumsikan hubungan proporsional",
        "",
        "**WP:**",
        "- ✅ Menghukum nilai ekstrem lebih ketat (perkalian pangkat)",
        "- ✅ Tidak memerlukan normalisasi terpisah",
        "- ⚠️ Sensitif terhadap nilai sangat kecil atau negatif",
        "- ⚠️ Sulit menjelaskan kepada pemangku kepentingan non-teknis",
        "",
        "**Catatan:** Bobot adalah *asumsi* pengambil keputusan, bukan berasal dari data.",
        "Ubah bobot untuk melihat dampaknya menggunakan Tab 6 (Sensitivitas).",
    ]

    return "\n".join(lines)


def render_tab_conclusion(state: dict) -> None:
    """Render Tab 7: Kesimpulan dan Ekspor."""
    problem: Problem = state.get("problem")
    hasil_saw: SAWResult | None = state.get("hasil_saw")
    hasil_wp: WPResult | None = state.get("hasil_wp")
    dp = state.get("decimal_places", DEFAULT_DECIMAL_PLACES)

    if problem is None:
        st.warning("⚠️ Lengkapi data terlebih dahulu.")
        return

    # ---- KESIMPULAN ----
    st.markdown("## 📋 Ringkasan Otomatis")

    if hasil_saw is None and hasil_wp is None:
        st.info("ℹ️ Jalankan perhitungan SAW dan/atau WP di Tab 3 dan 4 untuk melihat kesimpulan.")
    else:
        # Metrik ringkasan
        col1, col2, col3 = st.columns(3)
        if hasil_saw:
            best = hasil_saw.peringkat.idxmin()
            col1.metric("🥇 SAW: Alternatif Terbaik", best, f"V = {float(hasil_saw.v.loc[best]):.{dp}f}")
        if hasil_wp:
            best = hasil_wp.peringkat.idxmin()
            col2.metric("🥇 WP: Alternatif Terbaik", best, f"V = {float(hasil_wp.v.loc[best]):.{dp}f}")
        if hasil_saw and hasil_wp:
            same = hasil_saw.peringkat.idxmin() == hasil_wp.peringkat.idxmin()
            col3.metric("Konsistensi Metode", "Sepakat ✅" if same else "Berbeda ⚠️")

        # Teks kesimpulan yang bisa diedit
        teks_default = _kesimpulan_otomatis(problem, hasil_saw, hasil_wp, dp)
        teks_kesimpulan = st.text_area(
            "Teks Kesimpulan (dapat diedit)",
            value=state.get("teks_kesimpulan", teks_default),
            height=400,
            key="textarea_kesimpulan",
        )
        state["teks_kesimpulan"] = teks_kesimpulan

    st.divider()

    # ---- EKSPOR ----
    st.markdown("## ⬇️ Unduh Hasil")

    if hasil_saw is None and hasil_wp is None:
        st.info("ℹ️ Jalankan perhitungan terlebih dahulu untuk mengaktifkan ekspor.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**📊 Excel dengan Rumus Hidup**")
        try:
            excel_bytes = ekspor_excel(problem, hasil_saw, hasil_wp)
            st.download_button(
                "⬇️ Unduh Excel (.xlsx)",
                data=excel_bytes,
                file_name=f"DSS_{problem.nama_kasus.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_excel",
                type="primary",
            )
        except Exception as e:
            st.error(f"❌ Error ekspor Excel: {e}")

    with col2:
        st.markdown("**📄 CSV Ranking**")
        csv_str = ekspor_csv_ranking(problem, hasil_saw, hasil_wp)
        st.download_button(
            "⬇️ Unduh CSV",
            data=csv_str,
            file_name=f"ranking_{problem.nama_kasus.replace(' ', '_')}.csv",
            mime="text/csv",
            key="dl_csv",
        )

    with col3:
        st.markdown("**📝 Laporan Markdown**")
        md_str = ekspor_markdown(problem, hasil_saw, hasil_wp)
        st.download_button(
            "⬇️ Unduh Laporan (.md)",
            data=md_str,
            file_name=f"laporan_{problem.nama_kasus.replace(' ', '_')}.md",
            mime="text/markdown",
            key="dl_md",
        )
