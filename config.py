"""
Konfigurasi konstanta global untuk DSS Calculator Engine.
Semua nilai default dan konstanta dipusatkan di sini.
"""

# --- Nilai pengganti default untuk WP saat data <= 0 ---
DEFAULT_REPLACEMENT_VALUE: float = 0.01

# --- Jumlah desimal tampilan default ---
DEFAULT_DECIMAL_PLACES: int = 4

# --- Jumlah iterasi Monte Carlo default ---
DEFAULT_MONTE_CARLO_ITERATIONS: int = 1000

# --- Langkah sweep sensitivitas one-at-a-time ---
DEFAULT_SENSITIVITY_STEP: float = 0.05

# --- Jumlah kriteria minimum dan maksimum ---
MIN_CRITERIA: int = 2
MAX_CRITERIA: int = 15

# --- Jumlah alternatif minimum ---
MIN_ALTERNATIVES: int = 2

# --- Tipe kriteria valid ---
BENEFIT: str = "Benefit"
COST: str = "Cost"
VALID_TYPES: list[str] = [BENEFIT, COST]

# --- Warna tema ---
COLOR_PRIMARY: str = "#0F4C5C"
COLOR_ACCENT: str = "#D9EAEC"
COLOR_INPUT: str = "#EAF4FB"
COLOR_FORMULA: str = "#FFFFFF"

# --- Nama preset ---
PRESET_EMPTY: str = "Kosong / Buat Sendiri"
PRESET_SUPERSTORE: str = "Superstore WP (Data Referensi)"
PRESET_LAPTOP: str = "Laptop Mahasiswa"
PRESET_BEASISWA: str = "Beasiswa"
