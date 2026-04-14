# CLAUDE.md - TNFADATA Runbook

## Project Overview

SIMBA automation runbook that scrapes Taiwan's DGBAS National Statistics website for
"Assets Structure for Households Sector" (Table 6) data, extracts Real Estate and
Household Equipment figures, and generates SIMBA-standard output files (DATA, META, ZIP).

**Source**: https://eng.stat.gov.tw/np.asp?ctNode=1553
**Dataset**: TNFADATA (Taiwan National Financial Assets Data)
**Country**: TWN (Taiwan)

## Architecture

Standard SIMBA pipeline: `config -> scraper -> extractor -> file_generator -> orchestrator -> main`

```
main.py              Entry point — calls orchestrator.main()
orchestrator.py      Wires pipeline: download() -> parse_excel() -> generate_files()
config.py            ALL constants, paths, series definitions, metadata, nav search terms
scraper.py           Selenium scraper with Cloudflare bypass
extractor.py         Dynamic Excel parser (openpyxl)
file_generator.py    Generates DATA/META/ZIP output files (xlwt)
```

## File Details

### config.py
- `TARGET_YEAR`: `None` = latest year only, `'ALL'` = all year tabs, `2023` = specific year
- `HEADLESS_MODE`: `True` for Docker/prod, `False` for visible browser debugging
- `SERIES_DEFINITIONS`: 4 series as tuples `(item_key, measure, code, description)`
  - `TNFADATA.REALESTATE.AMOUNT.A`
  - `TNFADATA.REALESTATE.COMPOSITION.A`
  - `TNFADATA.HOUSEHOLDEQUIPMENT.AMOUNT.A`
  - `TNFADATA.HOUSEHOLDEQUIPMENT.COMPOSITION.A`
- `SERIES_METADATA`: per-series dict with MULTIPLIER (8.0 for Amount, 0.0 for Composition),
  UNIT_TYPE (FLOW/LEVEL), DATA_TYPE (CURRENCY/PERCENT), etc.
- `EXTRACT_ITEMS`: `{'REALESTATE': 'Real Estate', 'HOUSEHOLDEQUIPMENT': 'Household Equipment'}`
- `NAV_CATEGORY_TITLE`, `NAV_STATISTICAL_TABLES`, `NAV_TABLE_TITLE`: navigation search terms
- `CLOUDFLARE_WAIT`: 60s timeout for Turnstile challenge resolution

### scraper.py
- Uses `undetected-chromedriver` (primary) to bypass Cloudflare Turnstile — falls back to
  `selenium` + `selenium_stealth` if not installed
- `get_chrome_version()`: detects Chrome via winreg (Windows) or CLI (Linux)
- `_build_driver()`: creates patched Chrome with download prefs
- `_handle_cloudflare()`: waits for Turnstile, clicks checkbox via ActionChains if needed
- Navigation: 3 pages — Main Page -> National Wealth Statistics -> Statistical Tables -> Table 6 xlsx link
- `_find_and_click_link()`: finds links by `title` attribute or visible text (partial match)
- `_find_excel_download_url()`: finds `<a class="xlsx">` near "Table 6" + "Assets Structure" text
- Download: tries `requests` with browser cookies first (`verify=False` for DGBAS SSL cert),
  falls back to browser navigation download
- `_wait_for_downloaded_file()`: polls for .xlsx, waits for .crdownload/.tmp to clear

### extractor.py
- `TNFADataParser` class — fully dynamic, no hardcoded positions
- `_get_year_sheets()`: finds sheet tabs that are valid years (2019, 2020, etc.)
- `_find_amount_composition_cols()`: scans header rows for "Amount"/"Composition" text,
  returns first pair found (cols C=3, D=4 under first asset group). Fallback to 3,4.
- `_find_item_row()`: partial text match in column B for item names
- `_extract_sheet_data()`: extracts REALESTATE and HOUSEHOLDEQUIPMENT data from one tab
- `parse_excel()`: processes sheets per TARGET_YEAR setting, returns
  `{data: {year: {item: {AMOUNT, COMPOSITION}}}, years, min_year, max_year}`

### file_generator.py
- `FileGenerator` class — generates SIMBA-standard .xls files using `xlwt`
- DATA file: Row 0 = series codes, Row 1 = descriptions, Rows 2+ = year data
- META file: One row per series with all METADATA_COLUMNS from config
- ZIP file: bundles DATA + META
- `generate_files()`: creates timestamped output + copies to `output/latest/`

### orchestrator.py
- `main()`: configures logging, silences noisy loggers, runs 3-step pipeline
- Returns 0 on success, 1 on failure

## Source Data Structure

The downloaded `table6e112.xlsx` has:
- Year tabs as sheet names: 2023, 2022, 2021, 2020, 2019
- Row 2-3: merged headers for 3 asset groups, each with Amount + Composition sub-columns
- First asset group: "Assets (Land evaluated at current land valuee)" -> cols C (Amount), D (Composition)
- Items in column B: "Real Estate" (row ~5), "Household Equipment" (row ~8)
- Values are numeric (Amount in 100 Million NT$, Composition in %)

## Output Structure

```
output/
  20260414_091011/                    # timestamped run folder
    TNFADATA_ANNUAL_DATA_20260414_091011.xls
    TNFADATA_ANNUAL_META_20260414_091011.xls
    TNFADATA_ANNUAL_20260414_091011.zip
  latest/                             # always holds most recent
    TNFADATA_ANNUAL_DATA_latest.xls
    TNFADATA_ANNUAL_META_latest.xls
    TNFADATA_ANNUAL_latest.zip
downloads/
  20260414_091011/
    table6e112.xlsx                   # raw downloaded source
```

## Dependencies

```
undetected-chromedriver   # Primary — Cloudflare Turnstile bypass
selenium                  # Fallback driver + WebDriverWait utilities
selenium-stealth          # Fallback stealth (used only if uc unavailable)
openpyxl                  # Read .xlsx source data
xlwt                      # Write .xls output files
requests                  # Direct HTTP download (with browser cookies)
```

## Key Decisions & Gotchas

- **Cloudflare Turnstile**: This site ALWAYS shows a Turnstile challenge. `undetected-chromedriver`
  bypasses it automatically by patching ChromeDriver. Regular selenium+stealth does NOT work.
- **SSL cert issue**: The DGBAS download server (`ws.dgbas.gov.tw`) has a misconfigured SSL cert.
  `requests` uses `verify=False`. Browser download works as fallback.
- **No Unicode arrows in logs**: Windows cp1252 console cannot encode `->` arrows. Use `->` instead.
- **Dynamic parsing**: The extractor finds columns/rows by text scanning — no hardcoded positions.
  If DGBAS changes the spreadsheet layout, the dynamic search should adapt.
- **TARGET_YEAR semantics**: `None` = latest only (default for prod), `'ALL'` = all tabs,
  int = specific year. This was a deliberate design choice.
- **Cross-platform**: Chrome version detection uses winreg (Windows) with Linux CLI fallback.
  All paths use `os.path.join()`. Works in Docker with `HEADLESS_MODE=True`.

## Verified Data (2023 tab)

| Series | Value |
|--------|-------|
| Real Estate Amount | 518,149 |
| Real Estate Composition | 30.21 |
| Household Equipment Amount | 57,019 |
| Household Equipment Composition | 3.32 |

## Common Tasks

- **Run pipeline**: `python main.py`
- **Change target year**: Edit `TARGET_YEAR` in config.py
- **Debug with visible browser**: Set `HEADLESS_MODE = False` in config.py
- **Add new extract items**: Add to `EXTRACT_ITEMS`, `SERIES_DEFINITIONS`, and `SERIES_METADATA` in config.py
