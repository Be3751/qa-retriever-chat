## Usage

### Command Line Arguments
- `-f` (First argument): File path of the source CSV file. (Required)
- `-o` (Second argument): Directory path for the output CSV file. (Required)
- `-s` (Third argument): Line number to start processing from in the CSV. If not specified, processing starts from the first line. (Optional)
  - Since processing is done in batches of 100 lines, valid start positions are 101, 201, 301, ...

### Notes
- If the process is interrupted due to an unexpected error, the next start position will be output in the format `Processing interrupted. Next start line: 201`.

### Examples
```bash
# Execute data cleansing
$ python indexing/cleansing.py -f indexing/input_csv/incident_all_20240421.csv -o indexing/output_csv

# Specify another CSV file (already cleansed) and execute data cleansing
$ python indexing/cleansing.py -f indexing/input_csv/incident_all_20250216.csv -o indexing/output_csv

# Specify a starting line (line 201) and execute data cleansing
$ python indexing/cleansing.py -f indexing/input_csv/incident_all_20240421.csv -o indexing/output_csv -s 201
```
