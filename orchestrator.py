# orchestrator.py
# Wires the full TNFADATA pipeline: download → extract → generate.

import sys
import logging

import config
from scraper import download
from extractor import TNFADataParser
from file_generator import FileGenerator

logger = logging.getLogger(__name__)


def main():
    """Run the full pipeline. Returns 0 on success, 1 on failure."""
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # Silence noisy third-party loggers
    for noisy in ('selenium', 'selenium.webdriver', 'urllib3',
                   'urllib3.connectionpool', 'openpyxl'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    try:
        logger.info('=== TNFADATA pipeline started ===')
        logger.info(f'Timestamp: {config.RUN_TIMESTAMP}')
        logger.info(f'Source:    {config.BASE_URL}')
        logger.info(f'Target:    {config.TARGET_YEAR or "latest year"}')

        # ── Step 1: Download ─────────────────────────────────────────────
        logger.info('Step 1: Downloading Table 6 from DGBAS...')
        file_path = download()
        logger.info(f'Downloaded: {file_path}')

        # ── Step 2: Extract ──────────────────────────────────────────────
        logger.info('Step 2: Extracting data from spreadsheet...')
        parser = TNFADataParser()
        parsed_data = parser.parse_excel(file_path)

        if not parsed_data or not parsed_data.get('data'):
            logger.error('No data extracted — aborting')
            return 1

        logger.info(
            f'Extracted: {len(parsed_data["years"])} years '
            f'({parsed_data["min_year"]}–{parsed_data["max_year"]})'
        )

        # ── Step 3: Generate output files ────────────────────────────────
        logger.info('Step 3: Generating output files...')
        generator = FileGenerator()
        output_files = generator.generate_files(
            parsed_data, config.OUTPUT_RUN_DIR
        )

        # ── Summary ──────────────────────────────────────────────────────
        logger.info('=== TNFADATA pipeline completed successfully ===')
        logger.info(f'Output dir:  {config.OUTPUT_RUN_DIR}')
        logger.info(f'Latest dir:  {config.LATEST_OUTPUT_DIR}')
        logger.info(f'DATA: {output_files["data_file"]}')
        logger.info(f'META: {output_files["meta_file"]}')
        logger.info(f'ZIP:  {output_files["zip_file"]}')

        return 0

    except Exception as e:
        logger.exception(f'Pipeline failed: {e}')
        return 1
