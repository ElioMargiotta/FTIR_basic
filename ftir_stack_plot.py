#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FTIR stacked plot from a folder of CSVs (path read from .env).
- Reads all *.csv (recursive), auto-detects delimiter (',' or ';').
- Uses first two columns: wavenumber [cm^-1], transmittance.
- Stacks curves with constant vertical offset.
- Peak annotation:
    * If TARGET_GUESSES in .env -> annotate nearest detected minima to those guesses.
    * Else -> annotate top N minima by prominence (PEAKS_PER_CURVE).
- Saves figure and a CSV summary of annotated peaks.
"""

import os
import re
import glob
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from dotenv import load_dotenv

# ---------- Config via .env ----------
load_dotenv()  # loads .env from current working directory

INPUT_DIR = os.getenv("INPUT_DIR", "").strip()
if not INPUT_DIR:
    raise RuntimeError("INPUT_DIR is not set in .env")

OFFSET_STEP = float(os.getenv("OFFSET_STEP", "0.175"))
PEAK_PROMINENCE = float(os.getenv("PEAK_PROMINENCE", "0.001"))
PEAKS_PER_CURVE = int(os.getenv("PEAKS_PER_CURVE", "5"))

_guess_env = os.getenv("TARGET_GUESSES", "").strip()
TARGET_GUESSES = None
if _guess_env:
    TARGET_GUESSES = []
    for tok in re.split(r"[,\s;]+", _guess_env):
        if tok:
            try:
                TARGET_GUESSES.append(float(tok))
            except ValueError:
                pass
    if not TARGET_GUESSES:
        TARGET_GUESSES = None  # fallback to auto

OUT_DIR = os.path.join("results", "plots")
os.makedirs(OUT_DIR, exist_ok=True)

# ---------- Utilities ----------
def _read_csv_any(path: str) -> pd.DataFrame:
    """
    Try CSV with default delimiter; fallback to ';'.
    Use first two columns and coerce to numeric.
    """
    def _clean(df):
        # keep first two columns
        df = df.iloc[:, :2].copy()
        df.columns = ["wavenumber", "transmittance"]
        # strip and coerce numeric
        for c in df.columns:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(",", ".", regex=False), errors="coerce"
            )
        df = df.dropna().reset_index(drop=True)
        return df

    try:
        df = pd.read_csv(path)
        if df.shape[1] < 2:
            raise ValueError("Too few columns")
        return _clean(df)
    except Exception:
        df = pd.read_csv(path, sep=";")
        return _clean(df)

def _find_minima(wn: np.ndarray, tr: np.ndarray, prominence: float):
    """
    Detect absorption minima as peaks of (1 - tr).
    Returns indices of minima.
    """
    inverted = 1.0 - tr
    peaks, _ = find_peaks(inverted, prominence=prominence)
    return peaks

def _nearest_index(x: np.ndarray, value: float) -> int:
    return int(np.argmin(np.abs(x - value)))

# ---------- Gather files ----------
csv_files = sorted(glob.glob(os.path.join(INPUT_DIR, "**", "*.csv"), recursive=True),
                   key=lambda p: os.path.basename(p).lower())

if not csv_files:
    raise FileNotFoundError(f"No CSV files found under: {INPUT_DIR}")

# ---------- Load all data ----------
curves = []
for path in csv_files:
    df = _read_csv_any(path)
    # sort by wavenumber descending if needed (common for FTIR plots)
    # not strictly required, but helps consistent text placement
    df = df.sort_values("wavenumber", ascending=False).reset_index(drop=True)
    curves.append((os.path.basename(path), df))

# ---------- Plot ----------
plt.figure(figsize=(10, 6))
n = len(curves)
peak_rows = []  # for summary csv

for i, (name, df) in enumerate(curves, start=1):
    wn = df["wavenumber"].to_numpy()
    tr = df["transmittance"].to_numpy()

    # vertical stacking: first curve highest
    offset = (n - i) * OFFSET_STEP
    plt.plot(wn, tr + offset, label=f"{name} (offset +{offset:.3f})")

    # peak detection on original (non-shifted) curve
    peak_idx = _find_minima(wn, tr, prominence=PEAK_PROMINENCE)

    if TARGET_GUESSES:
        # annotate nearest detected minima to each guess
        for guess in TARGET_GUESSES:
            if peak_idx.size == 0:
                continue
            nearest = peak_idx[_nearest_index(wn[peak_idx], guess)]
            p_wn = wn[nearest]
            p_tr = tr[nearest]
            plt.plot(p_wn, p_tr + offset, marker="+", linestyle="none")
            plt.text(p_wn, p_tr + offset + 0.01*max(1.0, OFFSET_STEP/0.175),
                     f"{p_wn:.0f}", fontsize=8)
            peak_rows.append({"file": name, "mode": "guess", "guess_cm-1": guess,
                              "peak_cm-1": float(p_wn), "transmittance": float(p_tr)})
    else:
        # annotate top-N minima by prominence (approx via sorting depth)
        if peak_idx.size > 0 and PEAKS_PER_CURVE > 0:
            # rank by depth (1 - tr) at the peak
            depths = (1.0 - tr[peak_idx])
            order = np.argsort(depths)[::-1][:PEAKS_PER_CURVE]
            for idx in peak_idx[order]:
                p_wn = wn[idx]
                p_tr = tr[idx]
                plt.plot(p_wn, p_tr + offset, marker="+", linestyle="none")
                plt.text(p_wn, p_tr + offset + 0.01*max(1.0, OFFSET_STEP/0.175),
                         f"{p_wn:.0f}", fontsize=8)
                peak_rows.append({"file": name, "mode": "auto",
                                  "guess_cm-1": None,
                                  "peak_cm-1": float(p_wn),
                                  "transmittance": float(p_tr)})

# FTIR: usual to invert X axis (high -> low wavenumber)
plt.gca().invert_xaxis()
plt.xlabel("Wavenumber (cm⁻¹)")
plt.ylabel(f"Transmittance (stacked, Δ={OFFSET_STEP})")
plt.title("FTIR Spectra (stacked)")
plt.grid(True, alpha=0.4)
plt.legend(loc="best", fontsize=8)
plt.tight_layout()
plt.show()

png_path = os.path.join(OUT_DIR, "ftir_stacked.png")
plt.savefig(png_path, dpi=200)
print(f"Saved plot: {png_path}")

# ---------- Peak summary ----------
if peak_rows:
    df_peaks = pd.DataFrame(peak_rows)
    out_csv = os.path.join(OUT_DIR, "ftir_peaks_summary.csv")
    df_peaks.to_csv(out_csv, index=False)
    print(f"Saved peak summary: {out_csv}")
