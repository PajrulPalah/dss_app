"""
Komponen UI untuk Tab 8: Panduan dan Rumus.
"""
from __future__ import annotations

import streamlit as st


def render_tab_guide() -> None:
    """Render Tab 8: Panduan dan Rumus."""

    st.markdown("## 📚 Panduan DSS Calculator Engine")
    st.markdown(
        "Aplikasi ini adalah alat simulasi **Multi-Attribute Decision Making (MADM)** "
        "yang transparan — setiap langkah perhitungan ditampilkan lengkap dengan rumus dan angka antara."
    )

    # ---- SAW ----
    with st.expander("📐 Metode SAW (Simple Additive Weighting)", expanded=True):
        st.markdown(
            """
**Langkah-langkah SAW:**

1. **Normalisasi Matriks Keputusan**
   - Benefit: nilai lebih besar = lebih baik
   - Cost: nilai lebih kecil = lebih baik
            """
        )
        col1, col2 = st.columns(2)
        with col1:
            st.latex(r"r_{ij} = \frac{x_{ij}}{\max_j(x_{ij})} \quad \text{(Benefit)}")
        with col2:
            st.latex(r"r_{ij} = \frac{\min_j(x_{ij})}{x_{ij}} \quad \text{(Cost)}")

        st.markdown("2. **Hitung Skor Preferensi V**")
        st.latex(r"V_i = \sum_{j=1}^{n} w_j \cdot r_{ij}")

        st.markdown("3. **Peringkat** — urutkan V menurun; skor tertinggi = terbaik")
        st.markdown(
            """
**Sifat Penting SAW:**
- Nilai V antara 0 dan 1 (untuk data positif)
- Menggunakan penjumlahan terbobot → satu nilai rendah bisa dikompensasi nilai tinggi kriteria lain
- Normalisasi linier mengasumsikan hubungan proporsional
            """
        )

    # ---- WP ----
    with st.expander("📐 Metode WP (Weighted Product)", expanded=True):
        st.markdown(
            """
**Langkah-langkah WP:**

1. **Tentukan Pangkat** (bergantung tipe kriteria)
            """
        )
        col1, col2 = st.columns(2)
        with col1:
            st.latex(r"\text{pangkat}_j = +w_j \quad \text{(Benefit)}")
        with col2:
            st.latex(r"\text{pangkat}_j = -w_j \quad \text{(Cost)}")

        st.markdown("2. **Hitung Vektor S** (di log-space untuk stabilitas numerik)")
        st.latex(r"S_i = \prod_{j=1}^{n} x_{ij}^{\text{pangkat}_j} = \exp\!\left(\sum_{j=1}^{n} \text{pangkat}_j \cdot \ln x_{ij}\right)")

        st.markdown("3. **Hitung Vektor V** (proporsi — total V = 1)")
        st.latex(r"V_i = \frac{S_i}{\sum_{k} S_k}")

        st.markdown(
            """
**Catatan Penting WP:**
- WP **memerlukan nilai positif** (`x_ij > 0`)
- Nilai ≤ 0 harus diganti/digeser (lihat pengaturan lanjutan)
- WP menghukum nilai rendah lebih keras karena menggunakan perkalian
- Sangat sensitif terhadap nilai pengganti yang dipilih untuk data negatif/nol
            """
        )

    # ---- NORMALISASI BOBOT ----
    with st.expander("⚖️ Normalisasi Bobot", expanded=False):
        st.markdown("Pengguna memasukkan bobot bebas (mis. 20/30/50 atau 0,2/0,3/0,5). Selalu dinormalisasi:")
        st.latex(r"w_j = \frac{\text{bobot\_input}_j}{\sum_{k} \text{bobot\_input}_k}, \quad \sum_{j} w_j = 1")
        st.info(
            "💡 Bobot adalah **asumsi dan keputusan** pengambil keputusan, **bukan** berasal dari data. "
            "Gunakan Tab 6 (Sensitivitas) untuk memeriksa seberapa sensitif hasil terhadap perubahan bobot."
        )

    # ---- CARA PENGGUNAAN ----
    with st.expander("🗺️ Cara Menggunakan Aplikasi", expanded=False):
        st.markdown(
            """
1. **Tab 1 - Definisi Masalah:** Isi nama kasus, kriteria (Kode/Nama/Tipe/Bobot), dan daftar alternatif.
2. **Tab 2 - Data:** Masukkan matriks keputusan. Bisa upload dari Excel/CSV atau definisikan kolom turunan.
3. **Tab 3 - Hasil SAW:** Lihat seluruh langkah SAW beserta contoh hitung interaktif.
4. **Tab 4 - Hasil WP:** Lihat langkah WP, sel yang disesuaikan, dan penjelasan edukatif.
5. **Tab 5 - Perbandingan:** Bandingkan hasil SAW vs WP secara visual dan naratif.
6. **Tab 6 - Sensitivitas:** Uji kestabilan keputusan terhadap perubahan bobot.
7. **Tab 7 - Kesimpulan:** Lihat ringkasan dan unduh hasil (Excel, CSV, Markdown).
            """
        )

    # ---- CARA MENAMBAH METODE BARU ----
    with st.expander("🔧 Cara Menambah Metode Baru (mis. TOPSIS, AHP)", expanded=False):
        st.markdown(
            """
Engine dirancang terbuka untuk ekstensi. Ikuti konvensi berikut:

```python
# File: engine/topsis.py
from engine.models import Problem

def hitung_topsis(problem: Problem, **settings) -> SomeResult:
    \"\"\"
    Hitung TOPSIS untuk masalah MADM.
    Returns hasil dengan atribut v (Series) dan peringkat (Series).
    \"\"\"
    # 1. Normalisasi vektor
    # 2. Bobot ternormalisasi
    # 3. Tentukan solusi ideal positif (A+) dan negatif (A-)
    # 4. Hitung jarak D+ dan D-
    # 5. Hitung preferensi C = D- / (D+ + D-)
    # 6. Peringkat
    ...
```

Kemudian tambahkan tab baru di `app.py` dan render di `ui/tab_topsis.py`.
            """
        )

    # ---- REFERENSI ----
    with st.expander("📖 Referensi", expanded=False):
        st.markdown(
            """
- Fishburn, P. C. (1967). *Additive Utilities with Incomplete Product Sets: Application to Priorities and Assignments.*
- Triantaphyllou, E. (2000). *Multi-Criteria Decision Making Methods: A Comparative Study.* Springer.
- Kusumadewi, S., et al. (2006). *Fuzzy Multi-Attribute Decision Making (Fuzzy MADM).* Graha Ilmu.
            """
        )
