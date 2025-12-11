#!/usr/bin/env python3
"""
CSV JSON Field Processor
Processes CSV files to find and replace values in JSON custom fields.
Searches for a specific value in a target JSON field and replaces it with
a configured replacement value.

Author: Claude
Date: 2025-12-01
"""

import csv
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
import shutil


class CSVSKUProcessor:
    """Processes CSV files to modify HP SKU values in JSON data."""

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the processor with configuration.

        Args:
            config_path: Path to the configuration JSON file
        """
        self.config = self._load_config(config_path)
        self.stats = {
            'total_rows': 0,
            'rows_processed': 0,
            'rows_modified': 0,
            'errors': 0,
            'malformed_json': [],
            'missing_hp_sku': [],
            'skus_unchanged': 0,
            'skus_modified': []
        }
        self._setup_logging()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Configuration file '{config_path}' not found.")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in configuration file: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """Setup logging configuration."""
        if not self.config['logging']['enabled']:
            return

        log_file = self.config['logging']['log_file']
        log_level = logging.DEBUG if self.config['logging']['verbose'] else logging.INFO

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _create_backup(self, input_file: str) -> str:
        """
        Create a backup of the input file.

        Args:
            input_file: Path to the input CSV file

        Returns:
            Path to the backup file
        """
        if not self.config['general_settings']['create_backup']:
            return None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_suffix = self.config['general_settings']['backup_suffix']
        input_path = Path(input_file)
        backup_file = input_path.parent / f"{input_path.stem}{backup_suffix}_{timestamp}{input_path.suffix}"

        try:
            shutil.copy2(input_file, backup_file)
            self.logger.info(f"Backup created: {backup_file}")
            return str(backup_file)
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise

    def _process_field_value(self, field_value: str) -> Tuple[str, bool]:
        """
        Process field value by replacing search_value with replace_value.

        Args:
            field_value: The field value to process

        Returns:
            Tuple of (processed_value, was_modified)
        """
        if not field_value or not isinstance(field_value, str):
            return field_value, False

        search_value = self.config['processing_rules']['search_value']
        replace_value = self.config['processing_rules']['replace_value']

        # Check if search value exists in the field value
        if search_value and search_value in field_value:
            new_value = field_value.replace(search_value, replace_value)
            return new_value, True

        return field_value, False

    def _process_json_data(self, json_str: str, row_num: int) -> Tuple[str, bool]:
        """
        Process JSON data to find and replace field values.

        Args:
            json_str: JSON string from the CSV cell
            row_num: Row number for error reporting

        Returns:
            Tuple of (modified_json_string, was_modified)
        """
        if not json_str or json_str.strip() == '':
            self.stats['missing_hp_sku'].append({'row': row_num, 'reason': 'Empty column R'})
            self.logger.debug(f"Row {row_num}: Column R is empty - no JSON data")
            return json_str, False

        try:
            # Parse JSON
            data = json.loads(json_str)

            # Handle both array and single object
            if not isinstance(data, list):
                data = [data]

            modified = False
            field_found = False

            # Search for target field
            target_field_name = self.config['processing_rules']['target_field_name']

            for item in data:
                if isinstance(item, dict) and item.get('name') == target_field_name:
                    field_found = True
                    original_value = item.get('value', '')
                    new_value, was_modified = self._process_field_value(original_value)

                    if was_modified:
                        item['value'] = new_value
                        modified = True
                        self.stats['skus_modified'].append({
                            'row': row_num,
                            'original': original_value,
                            'new': new_value
                        })
                        self.logger.debug(f"Row {row_num}: Modified field '{original_value}' -> '{new_value}'")
                    else:
                        self.stats['skus_unchanged'] += 1
                    break

            if not field_found:
                self.stats['missing_hp_sku'].append({'row': row_num, 'reason': 'Target field not found in JSON'})
                self.logger.debug(f"Row {row_num}: Target field '{target_field_name}' not found")

            # Return modified JSON
            return json.dumps(data, ensure_ascii=False), modified

        except json.JSONDecodeError as e:
            self.stats['malformed_json'].append({'row': row_num, 'error': str(e)})
            self.stats['errors'] += 1
            self.logger.warning(f"Row {row_num}: Malformed JSON - {e}")
            return json_str, False
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Row {row_num}: Unexpected error processing JSON - {e}")
            return json_str, False

    def process_csv(self, input_file: str, output_file: str):
        """
        Process the CSV file and modify HP SKU values.

        Args:
            input_file: Path to the input CSV file
            output_file: Path to the output CSV file
        """
        self.logger.info(f"Starting CSV processing: {input_file}")
        self.logger.info(f"Output will be saved to: {output_file}")

        # Create backup if configured
        if self.config['general_settings']['create_backup']:
            self._create_backup(input_file)

        target_col_index = self.config['general_settings']['target_column_index']
        max_rows = self.config['general_settings']['max_rows_to_process']

        try:
            # Read and process CSV
            with open(input_file, 'r', encoding='utf-8', newline='') as infile:
                reader = csv.reader(infile)
                rows = []

                for row_num, row in enumerate(reader, start=1):
                    self.stats['total_rows'] += 1

                    # Skip header row (row 1)
                    if row_num == 1:
                        rows.append(row)
                        continue

                    # Check max rows limit
                    if row_num > max_rows:
                        self.logger.warning(f"Reached maximum row limit ({max_rows}). Stopping processing.")
                        break

                    # Check if target column exists in this row
                    if len(row) > target_col_index:
                        json_data = row[target_col_index]
                        modified_json, was_modified = self._process_json_data(json_data, row_num)

                        # Update the row
                        row[target_col_index] = modified_json

                        if was_modified:
                            self.stats['rows_modified'] += 1
                            # Only add modified rows to output
                            rows.append(row)

                        self.stats['rows_processed'] += 1
                    else:
                        self.logger.debug(f"Row {row_num}: Column {target_col_index} not found (row has {len(row)} columns)")

                    # Progress indicator for large files
                    if row_num % 5000 == 0:
                        self.logger.info(f"Processed {row_num} rows...")

            # Write output CSV
            with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
                writer = csv.writer(outfile)
                writer.writerows(rows)

            self.logger.info(f"Successfully wrote output to: {output_file}")

        except FileNotFoundError:
            self.logger.error(f"Input file not found: {input_file}")
            raise
        except Exception as e:
            self.logger.error(f"Error processing CSV: {e}")
            raise

    def write_detailed_logs(self):
        """Write detailed logs to separate files for successful changes, errors, and missing fields."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Log 1: Successful Changes
        if self.stats['skus_modified']:
            success_log = f"successful_changes_{timestamp}.log"
            with open(success_log, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("SUCCESSFUL FIELD MODIFICATIONS\n")
                f.write("="*60 + "\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total modifications: {len(self.stats['skus_modified'])}\n")
                f.write("="*60 + "\n\n")

                for mod in self.stats['skus_modified']:
                    f.write(f"Row {mod['row']}: '{mod['original']}' -> '{mod['new']}'\n")

                f.write("\n" + "="*60 + "\n")
                f.write(f"End of log - Total entries: {len(self.stats['skus_modified'])}\n")
                f.write("="*60 + "\n")

            self.logger.info(f"Successful changes log written to: {success_log}")

        # Log 2: Errors/Malformed JSON
        if self.stats['malformed_json']:
            error_log = f"errors_malformed_json_{timestamp}.log"
            with open(error_log, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("ERRORS AND MALFORMED JSON\n")
                f.write("="*60 + "\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total errors: {len(self.stats['malformed_json'])}\n")
                f.write("="*60 + "\n\n")

                for error in self.stats['malformed_json']:
                    f.write(f"Row {error['row']}: {error['error']}\n")

                f.write("\n" + "="*60 + "\n")
                f.write(f"End of log - Total entries: {len(self.stats['malformed_json'])}\n")
                f.write("="*60 + "\n")

            self.logger.info(f"Errors/malformed JSON log written to: {error_log}")

        # Log 3: Missing Target Field
        if self.stats['missing_hp_sku']:
            missing_log = f"missing_target_field_{timestamp}.log"
            with open(missing_log, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("ROWS MISSING TARGET FIELD\n")
                f.write("="*60 + "\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total rows missing target field: {len(self.stats['missing_hp_sku'])}\n")
                f.write("="*60 + "\n\n")

                for entry in self.stats['missing_hp_sku']:
                    f.write(f"Row {entry['row']}: {entry['reason']}\n")

                f.write("\n" + "="*60 + "\n")
                f.write(f"End of log - Total entries: {len(self.stats['missing_hp_sku'])}\n")
                f.write("="*60 + "\n")

            self.logger.info(f"Missing target field log written to: {missing_log}")

    def print_summary(self):
        """Print a summary of the processing results."""
        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)
        print(f"Total rows in file:        {self.stats['total_rows']}")
        print(f"Rows processed:            {self.stats['rows_processed']}")
        print(f"Rows modified:             {self.stats['rows_modified']}")
        print(f"Rows in output file:       {self.stats['rows_modified'] + 1}")  # +1 for header
        print(f"Rows excluded:             {self.stats['total_rows'] - self.stats['rows_modified'] - 1}")  # -1 for header
        print(f"Fields unchanged:          {self.stats['skus_unchanged']}")
        print(f"Errors encountered:        {self.stats['errors']}")
        print(f"Malformed JSON rows:       {len(self.stats['malformed_json'])}")
        print(f"Rows missing target field: {len(self.stats['missing_hp_sku'])}")
        print("="*60)

        if self.stats['malformed_json']:
            print("\nRows with malformed JSON:")
            for error in self.stats['malformed_json'][:10]:  # Show first 10
                print(f"  Row {error['row']}: {error['error']}")
            if len(self.stats['malformed_json']) > 10:
                print(f"  ... and {len(self.stats['malformed_json']) - 10} more")

        if self.stats['missing_hp_sku']:
            print(f"\nRows missing target field: {len(self.stats['missing_hp_sku'])}")
            if len(self.stats['missing_hp_sku']) <= 20:
                for entry in self.stats['missing_hp_sku']:
                    print(f"  Row {entry['row']}: {entry['reason']}")
            else:
                print("  First 20 rows:")
                for entry in self.stats['missing_hp_sku'][:20]:
                    print(f"  Row {entry['row']}: {entry['reason']}")

        if self.stats['skus_modified']:
            print(f"\nSample of modified fields (first 10):")
            for mod in self.stats['skus_modified'][:10]:
                print(f"  Row {mod['row']}: '{mod['original']}' -> '{mod['new']}'")

        print("\n" + "="*60)


def get_file_paths(config: Dict) -> Tuple[str, str]:
    """
    Get input and output file paths from config or user input.

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of (input_file, output_file)
    """
    input_file = config['file_paths'].get('input_file', '').strip()
    output_file = config['file_paths'].get('output_file', '').strip()

    # Prompt for input file if not configured
    if not input_file:
        input_file = input("Enter the path to the input CSV file: ").strip()
        if not os.path.exists(input_file):
            print(f"Error: Input file '{input_file}' does not exist.")
            sys.exit(1)

    # Generate output file name if not configured
    if not output_file:
        input_path = Path(input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_processed{input_path.suffix}")
        print(f"Output will be saved to: {output_file}")

    return input_file, output_file


def main():
    """Main entry point for the script."""
    print("="*60)
    print("CSV JSON Field Processor")
    print("="*60)
    print()

    # Initialize processor
    try:
        processor = CSVSKUProcessor("config.json")
    except Exception as e:
        print(f"Failed to initialize processor: {e}")
        sys.exit(1)

    # Get file paths
    input_file, output_file = get_file_paths(processor.config)

    # Confirm before processing
    print(f"\nInput file:  {input_file}")
    print(f"Output file: {output_file}")
    response = input("\nProceed with processing? (y/n): ").strip().lower()

    if response != 'y':
        print("Processing cancelled.")
        sys.exit(0)

    # Process the CSV
    try:
        processor.process_csv(input_file, output_file)
        processor.write_detailed_logs()
        processor.print_summary()
    except Exception as e:
        print(f"\nProcessing failed: {e}")
        sys.exit(1)

    print("\nProcessing complete!")


if __name__ == "__main__":
    main()
