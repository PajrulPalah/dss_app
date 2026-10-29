import sys, os
sys.path.insert(0, '.')
import numpy as np
import pandas as pd
from engine.models import Criterion, Problem
from engine.saw import hitung_saw
from engine.wp import hitung_wp

# ============ TEST SUPERSTORE WP ============
print('=== SUPERSTORE WP ===')
alternatif = ['West', 'East', 'Central', 'South']
sales = {'West': 107483.0, 'East': 41705.0, 'Central': 14007.0, 'South': 17309.0}
profit = {'West': 19663.0, 'East': 4985.0, 'Central': -3634.0, 'South': 2219.0}
qty = {'West': 1898.0, 'East': 543.0, 'Central': 350.0, 'South': 262.0}
pelanggan = {'West': 170.0, 'East': 41.0, 'Central': 37.0, 'South': 24.0}
profit_ratio = {a: profit[a]/sales[a]*100 for a in alternatif}
sales_per_cust = {a: sales[a]/pelanggan[a] for a in alternatif}

kriteria = [
    Criterion('C1','Sales','Benefit',20),
    Criterion('C2','Profit','Benefit',30),
    Criterion('C3','Profit Ratio','Benefit',25),
    Criterion('C4','Sales/Cust','Benefit',10),
    Criterion('C5','Quantity','Benefit',5),
    Criterion('C6','Pelanggan','Benefit',10),
]
matriks = pd.DataFrame({'C1':sales,'C2':profit,'C3':profit_ratio,'C4':sales_per_cust,'C5':qty,'C6':pelanggan},index=alternatif)
p = Problem('Superstore',alternatif,kriteria,matriks)
h = hitung_wp(p, strategi_zero='ganti', nilai_pengganti=0.01)
print('S West=%.4f (exp: 1892.2965)' % h.s['West'])
print('S East=%.4f (exp: 797.0127)' % h.s['East'])
print('S Central=%.4f (exp: 1.8668)' % h.s['Central'])
print('S South=%.4f (exp: 471.2107)' % h.s['South'])
print('Total S=%.4f (exp: 3162.3867)' % h.s.sum())
print('V West=%.4f (exp: 0.5984)' % h.v['West'])
print('V East=%.4f (exp: 0.2520)' % h.v['East'])
print('V Central=%.4f (exp: 0.0006)' % h.v['Central'])
print('V South=%.4f (exp: 0.1490)' % h.v['South'])
print('Peringkat: %s' % dict(h.peringkat))
print()

# ============ TEST LAPTOP SAW ============
print('=== LAPTOP SAW ===')
kriteria_l = [
    Criterion('C1','Harga','Cost',0.35),
    Criterion('C2','RAM','Benefit',0.30),
    Criterion('C3','Baterai','Benefit',0.20),
    Criterion('C4','Berat','Cost',0.15),
]
alt_l = ['A1','A2','A3','A4']
mat_l = pd.DataFrame({
    'C1': {'A1':9,'A2':12,'A3':8,'A4':15},
    'C2': {'A1':8,'A2':16,'A3':8,'A4':16},
    'C3': {'A1':8,'A2':10,'A3':6,'A4':12},
    'C4': {'A1':1.6,'A2':1.8,'A3':1.4,'A4':1.3},
},index=alt_l)
p_l = Problem('Laptop',alt_l,kriteria_l,mat_l)
h_saw = hitung_saw(p_l)
print('V A1=%.4f (exp: 0.7163)' % h_saw.v['A1'])
print('V A2=%.4f (exp: 0.8083)' % h_saw.v['A2'])
print('V A3=%.4f (exp: 0.7393)' % h_saw.v['A3'])
print('V A4=%.4f (exp: 0.8367)' % h_saw.v['A4'])
print('Peringkat: %s' % dict(h_saw.peringkat))
print()

# ============ TEST LAPTOP WP ============
print('=== LAPTOP WP ===')
h_wp = hitung_wp(p_l)
print('S A1=%.4f (exp: 1.2216)' % h_wp.s['A1'])
print('S A2=%.4f (exp: 1.3971)' % h_wp.s['A2'])
print('S A3=%.4f (exp: 1.2262)' % h_wp.s['A3'])
print('S A4=%.4f (exp: 1.4072)' % h_wp.s['A4'])
print('Total S=%.4f (exp: 5.2521)' % h_wp.s.sum())
print('V A1=%.4f (exp: 0.2326)' % h_wp.v['A1'])
print('V A2=%.4f (exp: 0.2660)' % h_wp.v['A2'])
print('V A3=%.4f (exp: 0.2335)' % h_wp.v['A3'])
print('V A4=%.4f (exp: 0.2679)' % h_wp.v['A4'])
print()

# ============ TEST BEASISWA SAW ============
print('=== BEASISWA SAW ===')
alt_b = ['Andi','Bunga','Citra','Dimas','Eka']
kriteria_b = [
    Criterion('C1','IPK','Benefit',0.35),
    Criterion('C2','Penghasilan','Cost',0.30),
    Criterion('C3','Tanggungan','Benefit',0.15),
    Criterion('C4','Prestasi','Benefit',0.20),
]
mat_b = pd.DataFrame({
    'C1': {'Andi':3.85,'Bunga':3.45,'Citra':3.80,'Dimas':3.40,'Eka':3.90},
    'C2': {'Andi':6.0,'Bunga':2.5,'Citra':4.0,'Dimas':1.8,'Eka':7.5},
    'C3': {'Andi':2,'Bunga':4,'Citra':3,'Dimas':5,'Eka':1},
    'C4': {'Andi':4,'Bunga':3,'Citra':5,'Dimas':2,'Eka':4},
},index=alt_b)
p_b = Problem('Beasiswa',alt_b,kriteria_b,mat_b)
h_b = hitung_saw(p_b)
print('V Andi=%.4f (exp: 0.6555)' % h_b.v['Andi'])
print('V Bunga=%.4f (exp: 0.7656)' % h_b.v['Bunga'])
print('V Citra=%.4f (exp: 0.7660)' % h_b.v['Citra'])
print('V Dimas=%.4f (exp: 0.8351)' % h_b.v['Dimas'])
print('V Eka=%.4f (exp: 0.6120)' % h_b.v['Eka'])
print('Peringkat: %s' % dict(h_b.peringkat))
print()

# ============ TEST SENSITIVITAS LAPTOP ============
print('=== SENSITIVITAS LAPTOP (Prioritas Harga 0.60) ===')
from engine.sensitivity import SkenarioBobot, analisis_skenario
sk = SkenarioBobot('Prioritas Harga', [0.60, 0.18, 0.12, 0.09])
hasil_sk = analisis_skenario(p_l, [sk], hitung_saw_flag=True, hitung_wp_flag=False)
h_sk = hasil_sk[0]
print('Peringkat SAW: %s' % dict(h_sk.peringkat_saw))
v_a3 = float(h_sk.v_saw['A3'])
print('V A3=%.4f (exp: 0.8396)' % v_a3)
print('A3 peringkat 1? %s (exp: True)' % (h_sk.peringkat_saw['A3'] == 1))
print('SEMUA VALIDASI SELESAI')
