# file_generator.py
# Generate DATA (.xls), META (.xls), and ZIP output files for TNFADATA.

import os
import shutil
import zipfile
import logging
import xlwt

import config

logger = logging.getLogger(__name__)


class FileGenerator:
    """
    Generates the SIMBA-standard output files:
      - DATA file: 2 header rows (codes + descriptions) + year data rows
      - META file: one row per series with standard metadata columns
      - ZIP file: contains both DATA and META
    All files are saved to the timestamped output folder and also
    copied to the 'latest' folder.
    """

    def __init__(self):
        self.logger = logger

    # ─────────────────────────────────────────────────────────────────────
    # DATA file
    # ─────────────────────────────────────────────────────────────────────

    def create_data_file(self, parsed_data, output_path):
        """
        Create the DATA Excel file.

        Layout:
            Row 0: [empty] | TNFADATA.REALESTATE.AMOUNT.A | ... (series codes)
            Row 1: [empty] | <description>                | ... (descriptions)
            Row 2: 2019    | 464541                       | ...
            Row 3: 2020    | 473905                       | ...
            ...
        """
        self.logger.info('Creating DATA file...')

        data = parsed_data['data']
        years = parsed_data['years']

        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('DATA')

        num_series = len(config.SERIES_DEFINITIONS)

        # ── Row 0: series codes ──────────────────────────────────────────
        sheet.write(0, 0, '')
        for col_idx in range(num_series):
            sheet.write(0, col_idx + 1, config.SERIES_CODES[col_idx])

        # ── Row 1: series descriptions ───────────────────────────────────
        sheet.write(1, 0, '')
        for col_idx in range(num_series):
            sheet.write(1, col_idx + 1, config.SERIES_DESCRIPTIONS[col_idx])

        # ── Data rows (year per row) ─────────────────────────────────────
        for row_offset, year in enumerate(years):
            row_idx = row_offset + 2
            sheet.write(row_idx, 0, str(year))

            year_data = data.get(year, {})

            for col_idx, (item_key, measure, code, _) in enumerate(config.SERIES_DEFINITIONS):
                item_data = year_data.get(item_key, {})
                value = item_data.get(measure)
                if value is not None:
                    sheet.write(row_idx, col_idx + 1, value)

        workbook.save(output_path)

        self.logger.info(
            f'DATA file saved: {output_path}  |  '
            f'{len(years)} years x {num_series} series'
        )
        return output_path

    # ─────────────────────────────────────────────────────────────────────
    # META file
    # ─────────────────────────────────────────────────────────────────────

    def create_meta_file(self, output_path):
        """
        Create the META Excel file.
        One row per series, columns defined by config.METADATA_COLUMNS.
        """
        self.logger.info('Creating META file...')

        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('META')

        # ── Header row ───────────────────────────────────────────────────
        for col_idx, col_name in enumerate(config.METADATA_COLUMNS):
            sheet.write(0, col_idx, col_name)

        # ── Data rows ────────────────────────────────────────────────────
        for series_idx, (item_key, measure, code, description) in enumerate(config.SERIES_DEFINITIONS):
            row_idx = series_idx + 1
            mnemonic = config.SERIES_CODE_MNEMONICS[series_idx]
            meta = config.SERIES_METADATA[code]

            row_data = {
                'CODE':                 code,
                'CODE_MNEMONIC':        mnemonic,
                'DESCRIPTION':          description,
                'FREQUENCY':            meta['FREQUENCY'],
                'MULTIPLIER':           meta['MULTIPLIER'],
                'AGGREGATION_TYPE':     meta['AGGREGATION_TYPE'],
                'UNIT_TYPE':            meta['UNIT_TYPE'],
                'DATA_TYPE':            meta['DATA_TYPE'],
                'DATA_UNIT':            meta['DATA_UNIT'],
                'SEASONALLY_ADJUSTED':  meta['SEASONALLY_ADJUSTED'],
                'ANNUALIZED':           meta['ANNUALIZED'],
                'STATE':                meta['STATE'],
                'PROVIDER_MEASURE_URL': meta['PROVIDER_MEASURE_URL'],
                'PROVIDER':             meta['PROVIDER'],
                'SOURCE':               meta['SOURCE'],
                'SOURCE_DESCRIPTION':   meta['SOURCE_DESCRIPTION'],
                'COUNTRY':              meta['COUNTRY'],
                'DATASET':              meta['DATASET'],
            }

            for col_idx, col_name in enumerate(config.METADATA_COLUMNS):
                value = row_data.get(col_name, '')
                sheet.write(row_idx, col_idx, value)

        workbook.save(output_path)

        self.logger.info(
            f'META file saved: {output_path}  |  '
            f'{len(config.SERIES_DEFINITIONS)} series'
        )
        return output_path

    # ─────────────────────────────────────────────────────────────────────
    # ZIP file
    # ─────────────────────────────────────────────────────────────────────

    def create_zip_file(self, data_file, meta_file, zip_path):
        """Bundle DATA and META files into a single ZIP."""
        self.logger.info(f'Creating ZIP: {zip_path}')

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(data_file, os.path.basename(data_file))
            zf.write(meta_file, os.path.basename(meta_file))

        self.logger.info('ZIP created')
        return zip_path

    # ─────────────────────────────────────────────────────────────────────
    # Generate all outputs
    # ─────────────────────────────────────────────────────────────────────

    def generate_files(self, parsed_data, output_dir):
        """
        Generate DATA, META, and ZIP files in *output_dir* and copy
        them to the 'latest' folder.
        """
        os.makedirs(output_dir, exist_ok=True)

        timestamp = config.RUN_TIMESTAMP

        data_filename = config.DATA_FILE_PATTERN.format(timestamp=timestamp)
        meta_filename = config.META_FILE_PATTERN.format(timestamp=timestamp)
        zip_filename  = config.ZIP_FILE_PATTERN.format(timestamp=timestamp)

        data_path = os.path.join(output_dir, data_filename)
        meta_path = os.path.join(output_dir, meta_filename)
        zip_path  = os.path.join(output_dir, zip_filename)

        # Create files
        self.create_data_file(parsed_data, data_path)
        self.create_meta_file(meta_path)
        self.create_zip_file(data_path, meta_path, zip_path)

        # Copy to 'latest' folder
        latest_dir = config.LATEST_OUTPUT_DIR
        os.makedirs(latest_dir, exist_ok=True)

        latest_data = os.path.join(latest_dir, 'TNFADATA_ANNUAL_DATA_latest.xls')
        latest_meta = os.path.join(latest_dir, 'TNFADATA_ANNUAL_META_latest.xls')
        latest_zip  = os.path.join(latest_dir, 'TNFADATA_ANNUAL_latest.zip')

        shutil.copy2(data_path, latest_data)
        shutil.copy2(meta_path, latest_meta)
        shutil.copy2(zip_path, latest_zip)

        self.logger.info(f'Files copied to latest: {latest_dir}')

        return {
            'data_file':   data_path,
            'meta_file':   meta_path,
            'zip_file':    zip_path,
            'latest_data': latest_data,
            'latest_meta': latest_meta,
            'latest_zip':  latest_zip,
        }
