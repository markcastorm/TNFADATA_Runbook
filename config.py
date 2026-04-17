# config.py
# TNFADATA — Taiwan National Financial Assets Data (Households Sector)
# All constants, paths, column mappings, and settings

import os
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR  = os.path.join(BASE_DIR, 'downloads')
OUTPUT_DIR    = os.path.join(BASE_DIR, 'output')

# ── Timestamped folders ──────────────────────────────────────────────────────
RUN_TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')

DOWNLOAD_RUN_DIR = os.path.join(DOWNLOAD_DIR, RUN_TIMESTAMP)
OUTPUT_RUN_DIR   = os.path.join(OUTPUT_DIR, RUN_TIMESTAMP)

# Latest folder — always holds the most recent output
LATEST_OUTPUT_DIR = os.path.join(OUTPUT_DIR, 'latest')

# ── Source ────────────────────────────────────────────────────────────────────
BASE_URL = 'https://eng.stat.gov.tw/np.asp?ctNode=1553'

PROVIDER_NAME = 'National Statistics Republic of China (Taiwan)'
DATASET_NAME  = 'TNFADATA'
COUNTRY_CODE  = 'TWN'

# ── Browser ───────────────────────────────────────────────────────────────────
HEADLESS_MODE       = True
WAIT_TIMEOUT        = 60
PAGE_LOAD_DELAY     = 5
DOWNLOAD_WAIT_TIME  = 120
CLOUDFLARE_WAIT     = 60

# ── Download settings ────────────────────────────────────────────────────────
MAX_DOWNLOAD_RETRIES = 3
RETRY_DELAY          = 3.0

# ── Target year ──────────────────────────────────────────────────────────────
# None  → extract only the LATEST year tab from the downloaded Excel
# 'ALL' → extract ALL available year tabs
# 2023  → extract only the specified year tab
TARGET_YEAR = 'ALL'

# ── Output filenames ─────────────────────────────────────────────────────────
DATA_FILE_PATTERN = 'TNFADATA_ANNUAL_DATA_{timestamp}.xls'
META_FILE_PATTERN = 'TNFADATA_ANNUAL_META_{timestamp}.xls'
ZIP_FILE_PATTERN  = 'TNFADATA_ANNUAL_{timestamp}.zip'

# =============================================================================
# NAVIGATION — Dynamic search terms for page traversal
# =============================================================================

# Page 1 → find this category on the main page
NAV_CATEGORY_TITLE = 'National Wealth Statistics'

# Page 2 → find this link on the category page
NAV_STATISTICAL_TABLES = 'Statistical Tables'

# Page 3 → find the table containing this text, then click its EXCEL link
NAV_TABLE_TITLE = 'Table 6 Assets Structure for Households Sector'

# =============================================================================
# EXTRACTION — Dynamic search terms for parsing the downloaded Excel
# =============================================================================

# Items to extract from each year tab (partial match against column B)
EXTRACT_ITEMS = {
    'REALESTATE':         'Real Estate',
    'HOUSEHOLDEQUIPMENT': 'Household Equipment',
}

# We extract from the FIRST asset group: "Assets (Land evaluated at current land valuee)"
# Columns C (Amount) and D (Composition) relative to the header structure.
# The extractor finds these dynamically by scanning headers.

# =============================================================================
# SERIES DEFINITIONS (absolute — exact order matters)
# =============================================================================

SERIES_DEFINITIONS = [
    # (series_key, measure, code_suffix, description)
    (
        'REALESTATE', 'AMOUNT',
        'TNFADATA.REALESTATE.AMOUNT.A',
        'Assets Structure for Households Sector, Net Non-financial Assets, Real Estate, Amount',
    ),
    (
        'REALESTATE', 'COMPOSITION',
        'TNFADATA.REALESTATE.COMPOSITION.A',
        'Assets Structure for Households Sector, Net Non-financial Assets, Real Estate, Composition',
    ),
    (
        'HOUSEHOLDEQUIPMENT', 'AMOUNT',
        'TNFADATA.HOUSEHOLDEQUIPMENT.AMOUNT.A',
        'Assets Structure for Households Sector, Net Non-financial Assets, Household Equipment, Amount',
    ),
    (
        'HOUSEHOLDEQUIPMENT', 'COMPOSITION',
        'TNFADATA.HOUSEHOLDEQUIPMENT.COMPOSITION.A',
        'Assets Structure for Households Sector, Net Non-financial Assets, Household Equipment, Composition',
    ),
]

# Derived lists (absolute order)
SERIES_CODES = [s[2] for s in SERIES_DEFINITIONS]

SERIES_CODE_MNEMONICS = [s[2].rsplit('.', 1)[0] for s in SERIES_DEFINITIONS]

SERIES_DESCRIPTIONS = [s[3] for s in SERIES_DEFINITIONS]

# =============================================================================
# META FILE CONFIGURATION
# =============================================================================

METADATA_COLUMNS = [
    'CODE',
    'CODE_MNEMONIC',
    'DESCRIPTION',
    'FREQUENCY',
    'MULTIPLIER',
    'AGGREGATION_TYPE',
    'UNIT_TYPE',
    'DATA_TYPE',
    'DATA_UNIT',
    'SEASONALLY_ADJUSTED',
    'ANNUALIZED',
    'STATE',
    'PROVIDER_MEASURE_URL',
    'PROVIDER',
    'SOURCE',
    'SOURCE_DESCRIPTION',
    'COUNTRY',
    'DATASET',
]

# Per-series metadata (keyed by series code)
SERIES_METADATA = {
    'TNFADATA.REALESTATE.AMOUNT.A': {
        'FREQUENCY':            'A',
        'MULTIPLIER':           8.0,
        'AGGREGATION_TYPE':     'UNDEFINED',
        'UNIT_TYPE':            'FLOW',
        'DATA_TYPE':            'CURRENCY',
        'DATA_UNIT':            'TWD',
        'SEASONALLY_ADJUSTED':  'NSA',
        'ANNUALIZED':           False,
        'STATE':                'ACTIVE',
        'PROVIDER_MEASURE_URL': 'https://eng.stat.gov.tw/np.asp?ctNode=1553',
        'PROVIDER':             'AfricaAI',
        'SOURCE':               'TWNSTAT',
        'SOURCE_DESCRIPTION':   PROVIDER_NAME,
        'COUNTRY':              COUNTRY_CODE,
        'DATASET':              DATASET_NAME,
    },
    'TNFADATA.REALESTATE.COMPOSITION.A': {
        'FREQUENCY':            'A',
        'MULTIPLIER':           0.0,
        'AGGREGATION_TYPE':     'UNDEFINED',
        'UNIT_TYPE':            'LEVEL',
        'DATA_TYPE':            'PERCENT',
        'DATA_UNIT':            'PERCENT',
        'SEASONALLY_ADJUSTED':  'NSA',
        'ANNUALIZED':           False,
        'STATE':                'ACTIVE',
        'PROVIDER_MEASURE_URL': 'https://eng.stat.gov.tw/np.asp?ctNode=1553',
        'PROVIDER':             'AfricaAI',
        'SOURCE':               'TWNSTAT',
        'SOURCE_DESCRIPTION':   PROVIDER_NAME,
        'COUNTRY':              COUNTRY_CODE,
        'DATASET':              DATASET_NAME,
    },
    'TNFADATA.HOUSEHOLDEQUIPMENT.AMOUNT.A': {
        'FREQUENCY':            'A',
        'MULTIPLIER':           8.0,
        'AGGREGATION_TYPE':     'UNDEFINED',
        'UNIT_TYPE':            'FLOW',
        'DATA_TYPE':            'CURRENCY',
        'DATA_UNIT':            'TWD',
        'SEASONALLY_ADJUSTED':  'NSA',
        'ANNUALIZED':           False,
        'STATE':                'ACTIVE',
        'PROVIDER_MEASURE_URL': 'https://eng.stat.gov.tw/np.asp?ctNode=1553',
        'PROVIDER':             'AfricaAI',
        'SOURCE':               'TWNSTAT',
        'SOURCE_DESCRIPTION':   PROVIDER_NAME,
        'COUNTRY':              COUNTRY_CODE,
        'DATASET':              DATASET_NAME,
    },
    'TNFADATA.HOUSEHOLDEQUIPMENT.COMPOSITION.A': {
        'FREQUENCY':            'A',
        'MULTIPLIER':           0.0,
        'AGGREGATION_TYPE':     'UNDEFINED',
        'UNIT_TYPE':            'LEVEL',
        'DATA_TYPE':            'PERCENT',
        'DATA_UNIT':            'PERCENT',
        'SEASONALLY_ADJUSTED':  'NSA',
        'ANNUALIZED':           False,
        'STATE':                'ACTIVE',
        'PROVIDER_MEASURE_URL': 'https://eng.stat.gov.tw/np.asp?ctNode=1553',
        'PROVIDER':             'AfricaAI',
        'SOURCE':               'TWNSTAT',
        'SOURCE_DESCRIPTION':   PROVIDER_NAME,
        'COUNTRY':              COUNTRY_CODE,
        'DATASET':              DATASET_NAME,
    },
}
