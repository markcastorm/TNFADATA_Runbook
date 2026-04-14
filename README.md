# TNFADATA Runbook

Automated SIMBA pipeline for Taiwan National Financial Assets Data (Households Sector).

Scrapes **Table 6 - Assets Structure for Households Sector** from Taiwan's
[DGBAS National Statistics](https://eng.stat.gov.tw/np.asp?ctNode=1553) website,
extracts Real Estate and Household Equipment data, and generates SIMBA-standard
DATA, META, and ZIP output files.

## Quick Start

```bash
pip install undetected-chromedriver selenium openpyxl xlwt requests
python main.py
```

## Pipeline

```
Step 1: SCRAPER   - Navigate DGBAS site (bypass Cloudflare), download Table 6 Excel
Step 2: EXTRACTOR - Parse year tabs, extract Amount + Composition for each item
Step 3: GENERATOR - Create DATA .xls, META .xls, ZIP -> output/<timestamp>/ + output/latest/
```

## Configuration

Edit `config.py` to change behavior:

| Setting | Default | Description |
|---------|---------|-------------|
| `TARGET_YEAR` | `None` | `None` = latest year, `'ALL'` = all years, `2023` = specific year |
| `HEADLESS_MODE` | `True` | `False` to see the browser during scraping |
| `CLOUDFLARE_WAIT` | `60` | Seconds to wait for Cloudflare Turnstile resolution |

## Output Series

| Code | Description | Unit |
|------|-------------|------|
| `TNFADATA.REALESTATE.AMOUNT.A` | Real Estate, Amount | 100M NTD |
| `TNFADATA.REALESTATE.COMPOSITION.A` | Real Estate, Composition | % |
| `TNFADATA.HOUSEHOLDEQUIPMENT.AMOUNT.A` | Household Equipment, Amount | 100M NTD |
| `TNFADATA.HOUSEHOLDEQUIPMENT.COMPOSITION.A` | Household Equipment, Composition | % |

## Output Files

```
output/
  <timestamp>/
    TNFADATA_ANNUAL_DATA_<timestamp>.xls    # Year rows x 4 series columns
    TNFADATA_ANNUAL_META_<timestamp>.xls    # 4 rows, one per series
    TNFADATA_ANNUAL_<timestamp>.zip         # Both files bundled
  latest/
    TNFADATA_ANNUAL_DATA_latest.xls
    TNFADATA_ANNUAL_META_latest.xls
    TNFADATA_ANNUAL_latest.zip
```

## Architecture

| File | Role |
|------|------|
| `main.py` | Entry point |
| `orchestrator.py` | Wires pipeline: download -> extract -> generate |
| `config.py` | All constants, paths, series definitions, metadata |
| `scraper.py` | Selenium + undetected-chromedriver scraper with Cloudflare bypass |
| `extractor.py` | Dynamic Excel parser (no hardcoded row/column positions) |
| `file_generator.py` | DATA/META/ZIP generator using xlwt |

## Dependencies

| Package | Purpose |
|---------|---------|
| `undetected-chromedriver` | Bypass Cloudflare Turnstile (primary driver) |
| `selenium` | Browser automation, fallback driver |
| `selenium-stealth` | Stealth patches (fallback only) |
| `openpyxl` | Read source .xlsx files |
| `xlwt` | Write output .xls files |
| `requests` | HTTP download with browser cookies |

## Environment

- **Windows**: Chrome detected via registry, runs with visible or headless browser
- **Linux/Docker**: Chrome detected via CLI, must use `HEADLESS_MODE = True`
- Requires Google Chrome installed

## Navigation Flow

```
1. https://eng.stat.gov.tw/np.asp?ctNode=1553  (Main page)
   |-- Cloudflare Turnstile challenge (auto-bypassed by undetected-chromedriver)
   |
2. Click "National Wealth Statistics" category
   |
3. Click "Statistical Tables" link
   |
4. Find Table 6 "Assets Structure for Households Sector" -> click .xlsx link
   |
5. Download table6e112.xlsx via requests (with cookies) or browser fallback
```
