# FTIR Stacked Plot — Batch CSV → Figure + Peaks

This utility scans a folder of **FTIR spectra** stored as CSVs, stacks the curves with a constant offset, annotates absorption **minima** (via peak detection on `1 - T`), and saves a figure plus a CSV summary of the detected features.

- Script to run: **`ftir_stack_plot.py`**
- Inputs: all `*.csv` found **recursively** under a directory set in `.env` (`INPUT_DIR`)
- Outputs: auto-numbered figures `results/plots/ftir_stacked_###.png` and a matching peaks table `results/plots/ftir_stacked_###.csv`

---

## 1) Quick start (macOS, **zsh**)

```zsh
# clone or cd into your project folder
git clone https://github.com/ElioMargiotta/FTIR_basic.git
python3 -m venv .venv
source .venv/bin/activate         # activate the virtual environment
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```



---

## 2) Configure `.env`

The script reads settings from a `.env` file in the current working directory. An example file is provided: **`.env.example`**.

1. **Copy** the template and **edit** it:
   ```zsh
   cp .env.example .env
   ```
2. Open `.env` and set `INPUT_DIR` to your data folder (absolute or relative path).  
   If the path contains spaces, you may quote it.

   ```dotenv
   # Required
   INPUT_DIR=/absolute/path/to/your/csv_folder

   # Plot stacking
   OFFSET_STEP=0.175

   # Peak detection
   PEAK_PROMINENCE=0.001
   PEAKS_PER_CURVE=5
   # Optionally target specific bands (cm^-1), annotate nearest detected minima
   TARGET_GUESSES=830,900,1090,2180,2350

   # Output file naming (auto-increment, no overwrite)
   FIG_BASENAME=ftir_stacked
   FIG_DIGITS=3
   ```

> The output directory defaults to `results/plots` (auto-created).

---

## 3) Run

```zsh
# from the repo root (after activating the venv)
python3 ftir_stack_plot.py
```

- The script enumerates all CSV files under `INPUT_DIR`, plots stacked spectra, and saves outputs to `results/plots`.
- Filenames are **auto-incremented**: `ftir_stacked_001.png`, `ftir_stacked_002.png`, … and similarly for the peaks CSV.

---

## 4) CSV format expectations

- The script reads the **first two columns** as:  
  `wavenumber (cm^-1)`, `transmittance (fraction)`.
- It **auto-detects delimiters** (`,` or `;`) and handles decimal commas.
- Curves are sorted by **descending** wavenumber (typical FTIR convention); the X-axis is inverted in the figure.

---

## 5) Peak/minima detection — how it works

We want **absorption minima** in transmittance `T(ν)`. Instead of coding a custom minima finder, we reuse SciPy’s robust **peak** routines by inspecting the **inverted** signal:
\[ s(\nu) = 1 - T(\nu) \]
Now minima in `T` ↔ maxima in \( s \). We then call **`scipy.signal.find_peaks`** on \( s \) and keep peaks that satisfy a **prominence** condition. Prominence \(\mathcal{P}\) is a measure of how much a peak stands out relative to its surrounding baseline; informally it is the **vertical distance** from the peak to the highest “valley” (lowest contour) that connects it to a taller peak or the ends of the signal.

- If you provide `TARGET_GUESSES` (comma-separated wavenumbers in **cm⁻¹**), the script **annotates the nearest detected minima** to those guesses.
- Otherwise, it annotates the **top-N** minima ranked by prominence (controlled by `PEAKS_PER_CURVE`).

### What is “prominence”?
- **SciPy** defines prominence as *“how much a peak stands out from the surrounding baseline… the vertical distance between the peak and its lowest contour line.”* See [`scipy.signal.peak_prominences`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.peak_prominences.html).  
- In practice, a small noisy wiggle won’t be labeled if its prominence is below `PEAK_PROMINENCE`. Increase the value to be **stricter** (fewer peaks), decrease it to be **more permissive** (more peaks).

**References**
- `scipy.signal.find_peaks` documentation: <https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html>  
- Prominence definition in SciPy: <https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.peak_prominences.html>  
- General explanation (MATLAB): <https://www.mathworks.com/help/signal/ug/prominence.html>

---

## 6) Troubleshooting

- **No files found**: ensure `INPUT_DIR` points to the correct folder (use an **absolute** path to be safe).
- **Too many/too few annotations**: tune `PEAK_PROMINENCE` and/or `PEAKS_PER_CURVE`, or supply `TARGET_GUESSES`.
- **Mixed CSV formats**: the reader auto-detects `,` vs `;` and decimal comma, but the **first two columns must be numeric**.

---

## 7) What file does what?

- **`ftir_stack_plot.py`** — main entry point: loads CSVs, detects minima, plots and saves outputs.
- **`.env` / `.env.example`** — configuration (paths & detection parameters). The script uses `python-dotenv` to load values.

---

## 8) License & contributions

Feel free to adapt to your lab workflow.