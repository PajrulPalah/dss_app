"""Konfigurasi pytest untuk DSS Calculator Engine tests."""
import sys
import os

# Tambahkan direktori dss_app ke path agar import engine bekerja
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
