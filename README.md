# CSV HP SKU Processor

A Python script that processes large CSV files (~60,000 rows) to clean HP SKU values by removing trailing 'S' or 's' characters from JSON data.

## Features

- **JSON Parsing**: Parses JSON arrays in CSV cells and modifies specific fields
- **HP SKU Cleaning**: Removes trailing 'S' or 's' from HP SKU values (case-insensitive)
- **Error Handling**: Robust error handling for malformed JSON and missing fields
- **Backup Creation**: Automatically creates timestamped backups before processing
- **Detailed Reporting**: Provides comprehensive statistics and error reports
- **Progress Tracking**: Shows progress indicators for large files
- **Configurable**: All settings managed through `config.json`

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only standard library modules)

## Installation

1. Clone or download this repository
2. No additional packages required - uses Python standard library only

## Configuration

Edit the `config.json` file to customize processing:

```json
{
  "general_settings": {
    "create_backup": true,
    "target_column": "R",
    "target_column_index": 17,
    "max_rows_to_process": 100000
  },
  "file_paths": {
    "input_file": "",
    "output_file": ""
  },
  "processing_rules": {
    "hp_sku_field_name": "HP SKU",
    "remove_trailing_s": true,
    "case_insensitive": true
  },
  "logging": {
    "enabled": true,
    "log_file": "sku_processor.log",
    "verbose": true
  }
}
```

### Configuration Options

#### General Settings
- `create_backup`: Whether to create a backup before processing (recommended: `true`)
- `target_column`: Column letter containing JSON data (e.g., "R")
- `target_column_index`: Zero-based index of the target column (R = 17)
- `max_rows_to_process`: Maximum number of rows to process (safety limit)

#### File Paths
- `input_file`: Path to input CSV (leave empty to be prompted)
- `output_file`: Path to output CSV (leave empty for auto-generation)

#### Processing Rules
- `hp_sku_field_name`: The JSON field name to search for (default: "HP SKU")
- `remove_trailing_s`: Whether to remove trailing 'S'/'s' (default: `true`)
- `case_insensitive`: Case-insensitive matching for trailing 'S' (default: `true`)

#### Logging
- `enabled`: Enable logging (default: `true`)
- `log_file`: Log file name (default: "sku_processor.log")
- `verbose`: Detailed logging output (default: `true`)

## Usage

### Basic Usage

1. Run the script:
```bash
python3 csv_sku_processor.py
```

2. When prompted, enter the path to your CSV file
3. Confirm the processing
4. Review the summary report

### Pre-configured Usage

Set file paths in `config.json`:
```json
"file_paths": {
  "input_file": "/path/to/your/input.csv",
  "output_file": "/path/to/your/output.csv"
}
```

Then run:
```bash
python csv_sku_processor.py
```

### Make Script Executable (Linux/Mac)

```bash
chmod +x csv_sku_processor.py
./csv_sku_processor.py
```

## Input Data Format

The script expects CSV files with JSON data in the specified column (default: column R).

### Expected JSON Structure

```json
[
  {"id":244592,"name":"HP SKU","value":"1KTP0062S"},
  {"id":244593,"name":"Front Panel","value":"https://cloud.masuri.com/..."},
  {"id":244594,"name":"Second Image","value":"https://cloud.masuri.com/..."},
  {"id":244595,"name":"Product Type","value":"Training Kit"}
]
```

### Processing Example

**Before:**
```json
{"name":"HP SKU","value":"1KTP0062S"}
```

**After:**
```json
{"name":"HP SKU","value":"1KTP0062"}
```

## Output

### Processed CSV File
- **Contains ONLY modified rows** (rows where HP SKU values were changed)
- Header row is always included
- Modified HP SKU values (trailing 'S' removed)
- Rows with unchanged SKUs, empty columns, or missing HP SKU fields are excluded
- Same structure as input for included rows

**Example:** If you have 60,000 rows and only 1,247 have SKUs ending in 'S', the output will contain 1,248 rows (1 header + 1,247 modified rows).

### Processing Summary
```
==============================================================
PROCESSING SUMMARY
==============================================================
Total rows in file:        60000
Rows processed:            59999
Rows modified:             1247
Rows in output file:       1248
Rows excluded:             58752
SKUs unchanged:            58752
Errors encountered:        0
Malformed JSON rows:       0
Rows missing HP SKU:       0
==============================================================
```

### Log File
Detailed log saved to `sku_processor.log` (configurable) containing:
- Processing timestamps
- Detailed modifications
- Error messages
- Warning notifications

### Backup File
Automatic backup created with timestamp:
- Format: `original_filename_backup_YYYYMMDD_HHMMSS.csv`
- Example: `products_backup_20251201_143022.csv`

## Error Handling

The script handles various error conditions:

### Malformed JSON
- Logs the row number and error details
- Preserves original data (no modification)
- Continues processing remaining rows

### Missing HP SKU Field
- Logs rows where HP SKU field is not found
- Preserves original data
- Reports in summary

### Column Not Found
- Logs rows with insufficient columns
- Skips those rows
- Continues processing

### File Errors
- Checks for file existence
- Validates backup creation
- Reports clear error messages

## Examples

### Example 1: Standard Processing
```bash
$ python csv_sku_processor.py
==============================================================
CSV HP SKU Processor
==============================================================

Enter the path to the input CSV file: /data/products.csv
Output will be saved to: /data/products_processed.csv

Input file:  /data/products.csv
Output file: /data/products_processed.csv

Proceed with processing? (y/n): y

Processing...
Processed 5000 rows...
Processed 10000 rows...
...
Processing complete!
```

### Example 2: Pre-configured Processing
Edit `config.json`:
```json
"file_paths": {
  "input_file": "/data/products.csv",
  "output_file": "/data/products_cleaned.csv"
}
```

Run:
```bash
$ python csv_sku_processor.py
```

## Troubleshooting

### Issue: "Configuration file not found"
**Solution**: Ensure `config.json` exists in the same directory as the script

### Issue: "Input file does not exist"
**Solution**: Verify the file path is correct and accessible

### Issue: "Permission denied"
**Solution**: Check file permissions and ensure write access for output directory

### Issue: High number of malformed JSON errors
**Solution**:
- Verify column R contains JSON data
- Check if `target_column_index` is correct (R = 17)
- Review sample malformed rows in the log file

### Issue: No modifications made
**Solution**:
- Verify SKU values end with 'S' or 's'
- Check `hp_sku_field_name` matches your JSON field name
- Ensure `remove_trailing_s` is set to `true`

## Technical Details

### Performance
- Processes ~60,000 rows efficiently
- Memory-efficient (reads and writes incrementally)
- Progress indicators every 5,000 rows

### Data Integrity
- Creates backups before processing
- Preserves all non-modified data
- Maintains original CSV structure and formatting

### Limitations
- Maximum rows configurable (default: 100,000)
- Requires valid UTF-8 encoding
- Column R must contain valid JSON or empty cells

## License

This script is provided as-is for internal use.

## Support

For issues or questions, please review:
- This README
- The `config.json` field definitions
- Log file for detailed error information

## Version History

- **v1.0** (2025-12-01): Initial release
  - JSON parsing and HP SKU modification
  - Configurable processing rules
  - Comprehensive error handling and reporting
