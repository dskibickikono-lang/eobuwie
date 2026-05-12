# Performance Tracker: Modivo/eobuwie (HR KONO)

Plik konfiguracyjny dla Claude okre�laj�cy kontekst biznesowy, techniczny i zasady kodowania dla projektu.

## Komendy operacyjne
- **Instalacja zale�no�ci**: `pip install streamlit pandas openpyxl numpy`
- **Uruchomienie aplikacji**: `streamlit run eobuwie_app.py`

## Logika Biznesowa & KPI
Aplikacja monitoruje wydajno�ci operacyjne pracownik�w na projektach PICK i PACK w centrum logistycznym EOBUWIE.

### Normy (Target 100%):
- **PICK**: 460 szt./zmiana (8h)
- **PACK**: 464 szt./zmiana (8h)

### Progi Heatmapy (Wdro�enie):
- **Ciemny Zielony (Sukces)**: >= 94% normy (PICK >= 432.4, PACK >= 436.16)
- **Jasny Zielony (Stabilnie)**: 80% - 93% normy
- **��ty (W procesie)**: 50% - 79% normy
- **Czerwony (Krytyczny/Rotacja)**: < 50% normy

Sta�e zdefiniowane globalnie: `PICK_TARGET = 460`, `PACK_TARGET = 464`.

## Architektura Danych

### Backend & Dependencies
- Python, Streamlit, pandas, numpy, openpyxl, datetime (stdlib)

### State Management
- Jeden klucz: `st.session_state.performance_data` — DataFrame z kolumnami `['Worker_ID', 'Department', 'Date', 'Units_per_Shift']`.
- Inicjalizowany przy starcie przez `generate_mock_data()` (60 pracownik�w, 21 dni wstecz, seed=42).
- Rozszerzany przez `pd.concat` przy wpisie r�cznym i bulk upload.
- Resetowany do pustego DataFrame przyciskiem "Clear All Data".

### Kluczowy identyfikator
Kolumna `login` lub `Worker_ID` (wykrywana case-insensitive przy imporcie).

### Pipeline przetwarzania danych
1. **`clean_and_aggregate_data(df)`** — oczyszczenie i agregacja:
   - `pd.to_numeric(..., errors='coerce')` na `Units_per_Shift` (obs�uguje statusy tekstowe: "TRAINING", "NB", puste).
   - Usuwa wiersze z `NaN` w `Units_per_Shift` lub `Date`.
   - Oblicza numer tygodnia ISO: `df['Date'].dt.isocalendar().week` → kolumna `Week` jako `"wXX"`.
   - Grupuje po `['Worker_ID', 'Department', 'Week']`, oblicza `mean()` jako `Units_per_Shift`.

2. **`process_department_data(df, dept, target)`** — pivot i metryki:
   - Filtruje po `Department`, oblicza `%_of_Target = Units_per_Shift / target`.
   - `pivot(index='Worker_ID', columns='Week', values='%_of_Target')` → wide format.
   - `Trend (W-o-W)` = ostatni tydzie� minus przedostatni (0.0 je�li < 2 tygodnie).
   - `Avg Efficiency` = �rednia po wszystkich kolumnach tygodniowych.
   - Sort ascending po ostatnim tygodniu (najgorsze na g�rze).

3. **`render_dataframe(data, weeks)`** — renderowanie:
   - `style.map(get_color_status, subset=weeks + ['Avg Efficiency'])` — kolorowanie kom�rek.
   - Formatowanie procentowe `"{:.1%}"` dla kolumn tygodniowych i `Avg Efficiency`.
   - `Trend (W-o-W)` renderowany przez `format_trend()`: 🟢 je�li >= +5%, 🔴 je�li <= -5%, ⚪ w przeciwnym razie.
   - `st.dataframe(..., height=600, hide_index=True, use_container_width=True)`.

### Parser Bulk Upload (Wide Format → Long Format)
- Wczytuje CSV lub Excel (`pd.read_csv` / `pd.read_excel`).
- Auto-detekcja kolumny ID: szuka nazwy `['login', 'worker_id', 'worker id']` (case-insensitive strip).
- Auto-detekcja kolumn dat: iteruje nag��wki, pr�buje `pd.to_datetime(str(col))` — sukces = kolumna datowa.
- Auto-detekcja kolumny Department: szuka nazwy `'department'` (case-insensitive); je�li brak, u�ywa warto�ci z selectboxa sidebara.
- `pd.melt(id_vars=[id_col, (dept_col)], value_vars=date_cols, var_name='Date', value_name='Units_per_Shift')`.
- Standaryzuje nazwy kolumn do `['Worker_ID', 'Department', 'Date', 'Units_per_Shift']`.
- Wynik do��czany do `st.session_state.performance_data` przez `pd.concat`.

### G�wne sekcje UI
- **Sidebar**: formularz r�cznego wpisu (clear_on_submit), formularz bulk upload, przycisk reset, legenda KPI.
- **Top metrics bar** (4 kolumny): Total Active Workers, Latest Week, PICK Critical (<50%), PACK Critical (<50%).
- **Taby**: "PICK Department (Target: 460)" i "PACK Department (Target: 464)" z heatmapami.

## Wytyczne Stylistyczne (Vibe Coding)
- **UI**: Modern B2B Dashboard, Dark Mode (`#0f172a`), Glassmorphism (backdrop-filter, rgba borders), Tailwind-like styling.
- **UX**: Najgorsze wyniki (Czerwone) zawsze na g�rze tabeli (sort ascending po ostatnim tygodniu).
- **Kod**:
    - Unikaj zb�dnych komentarzy.
    - Zawsze zwracaj kompletny, dzia�aj�cy kod (ready-to-run).
    - Zachowuj integralno�� `st.session_state` przy ka�dej modyfikacji.
    - Przy imporcie danych z zewn�trz (CSV/Excel) zawsze stosuj `errors='coerce'` dla warto�ci numerycznych.

## Struktura Projektu
- `eobuwie_app.py`: G��wny plik aplikacji.
- `CLAUDE.md`: Niniejszy plik kontekstu.
- `run.sh`: skrypt uruchomieniowy.
- `README.md`: instrukcje.
- `dataset.xlsx`: przyk�adowe dane wej�ciowe.
