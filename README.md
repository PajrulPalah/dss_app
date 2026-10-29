# DSS Calculator Engine

> **Alat Simulasi Multi-Attribute Decision Making (MADM)** — SAW dan WP  
> Untuk Mahasiswa Magister Manajemen dan Pengambil Keputusan

---

## 📋 Deskripsi

DSS Calculator Engine adalah aplikasi web Streamlit yang transparan dan edukatif untuk perhitungan MADM. Setiap langkah perhitungan ditampilkan lengkap dengan rumus LaTeX dan angka antara — tidak hanya hasil akhir.

**Metode yang didukung:**
- **SAW** (Simple Additive Weighting): Normalisasi + penjumlahan terbobot
- **WP** (Weighted Product): Perkalian nilai pangkat bobot

**Fitur utama:**
- Input generik: alternatif, kriteria, tipe (Benefit/Cost), bobot bebas
- Kolom turunan (mis. Profit Ratio = Profit / Sales × 100)
- 3 preset contoh: Superstore, Laptop Mahasiswa, Beasiswa
- Analisis sensitivitas: skenario bobot, sweep one-at-a-time, Monte Carlo
- Ekspor Excel dengan rumus hidup, CSV, dan laporan Markdown
- Antarmuka penuh Bahasa Indonesia

---

## 🚀 Instalasi dan Menjalankan

### Prasyarat
- Python 3.11+

### Langkah Instalasi

```bash
# 1. Masuk ke direktori aplikasi
cd D:\KUMPULAN_PROJECT_AI\DSS_ENGINE\dss_app

# 2. Install dependensi
pip install -r requirements.txt

# 3. Jalankan aplikasi
streamlit run app.py
```

Aplikasi akan terbuka otomatis di browser pada `http://localhost:8501`.

### Menjalankan Tes

```bash
cd D:\KUMPULAN_PROJECT_AI\DSS_ENGINE\dss_app
python -m pytest tests/ -v
```

---

## 📁 Struktur Proyek

```
dss_app/
├── app.py                    # Entry point Streamlit (8 tab)
├── config.py                 # Konstanta global
├── requirements.txt          # Dependensi Python
├── engine/                   # Logic perhitungan (tanpa streamlit)
│   ├── __init__.py
│   ├── models.py             # Dataclass: Criterion, Problem, SAWResult, WPResult
│   ├── saw.py                # Engine SAW
│   ├── wp.py                 # Engine WP
│   ├── sensitivity.py        # Analisis sensitivitas + Monte Carlo
│   ├── validators.py         # Validasi input berbahasa Indonesia
│   └── exporters.py          # Ekspor Excel (rumus hidup), CSV, Markdown
├── ui/                       # Komponen UI per tab
│   ├── tab_problem.py        # Tab 1: Definisi Masalah
│   ├── tab_data.py           # Tab 2: Data & Matriks Keputusan
│   ├── tab_saw.py            # Tab 3: Hasil SAW
│   ├── tab_wp.py             # Tab 4: Hasil WP
│   ├── tab_comparison.py     # Tab 5: Perbandingan SAW vs WP
│   ├── tab_sensitivity.py    # Tab 6: Analisis Sensitivitas
│   ├── tab_conclusion.py     # Tab 7: Kesimpulan & Ekspor
│   └── tab_guide.py          # Tab 8: Panduan & Rumus
├── presets/                  # Data contoh (JSON)
│   ├── superstore.json       # Superstore Tableau WP
│   ├── laptop.json           # Pemilihan Laptop Mahasiswa
│   └── beasiswa.json         # Seleksi Penerima Beasiswa
└── tests/                    # Pytest unit tests
    ├── test_saw.py            # 10+ test SAW
    ├── test_wp.py             # 15+ test WP
    └── test_sensitivity.py   # 8+ test sensitivitas
```

---

## ✅ Nilai Validasi

| Kasus | Nilai | Ekspektasi |
|-------|-------|-----------|
| Superstore WP V West | 0.5984 | ✅ |
| Superstore WP V Central | 0.0006 | ✅ |
| Laptop SAW V A4 | 0.8367 | ✅ |
| Laptop WP total S | 5.2521 | ✅ |
| Beasiswa SAW V Dimas | 0.8351 | ✅ |
| Sensitivitas Laptop: A3 peringkat 1 saat bobot Harga=0.60 | ✅ | ✅ |

---

## 🔧 Cara Menambah Metode Baru (TOPSIS, AHP, dll.)

Ikuti antarmuka engine yang seragam:

```python
# engine/topsis.py
from engine.models import Problem
from dataclasses import dataclass
import pandas as pd
import numpy as np

@dataclass
class TOPSISResult:
    problem: Problem
    v: pd.Series      # Wajib: skor preferensi
    peringkat: pd.Series  # Wajib: peringkat
    peringatan: list[str]

def hitung_topsis(problem: Problem, **settings) -> TOPSISResult:
    """
    Hitung TOPSIS (Technique for Order Preference by Similarity to Ideal Solution).
    
    Langkah: Normalisasi vektor → Bobot → Solusi ideal A+/A- → 
             Jarak D+/D- → Preferensi C = D-/(D++D-) → Peringkat.
    """
    # Implementasi di sini...
    pass
```

Tambahkan tab di `app.py` dan render di `ui/tab_topsis.py`.

---

## 📊 Screenshot

*[Screenshot akan ditambahkan setelah aplikasi dijalankan]*

---

## 🎓 Target Pengguna

- Mahasiswa Magister Manajemen
- Pengambil keputusan non-programmer
- Peneliti MADM/SPK (Sistem Pendukung Keputusan)

---

## ⚠️ Batasan yang Diketahui

1. **Kolom turunan**: Hanya mendukung operator `+ - * /` dan nama kolom (tidak mendukung fungsi seperti `abs()`, `sqrt()`).
2. **WP dan nilai negatif**: Penggantian nilai ≤ 0 (mis. 0.01) sangat mempengaruhi hasil. Pilih strategi dengan hati-hati.
3. **Monte Carlo**: Menggunakan seed tetap (42) untuk reproducibility. Ubah seed di `engine/sensitivity.py` jika perlu variasi.
4. **Ekspor Excel**: Rumus hidup menggunakan referensi relatif; jika dipindah ke sheet lain, rumus perlu disesuaikan manual.
5. **Kinerja**: Monte Carlo dengan >5000 iterasi mungkin lambat tanpa cache. Gunakan `st.cache_data` jika diperlukan.
