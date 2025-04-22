import os
import csv
import sys
from datetime import datetime
import concurrent.futures

from modules.record import create_record_from_row, Record
from modules.prompt import cleanse_record

def get_csv_headers(file_path, encoding='utf-8'):
    """
    Reads a CSV file and returns the list of column names (headers).
    
    :param file_path: Path to the CSV file.
    :param encoding: Encoding of the CSV file (default is 'utf-8').
    :return: List of column names.
    """
    try:
        with open(file_path, mode='r', encoding=encoding) as file:
            csv_reader = csv.reader(file)
            headers = next(csv_reader)  # Read the first row as headers
            return headers
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []

def batch_cleanse_records(records):
    """
    Cleanse each record in a given list of records in parallel using threads.
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_index = {executor.submit(cleanse_record, record): index for index, record in enumerate(records)}
        results: list[Record] = [None] * len(records)
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            results[index] = future.result()
    return results

def batch_write_records(records: list[Record], writer: csv.DictWriter):
    """
    Write a batch of records to the CSV file using the provided writer.
    """
    results = batch_cleanse_records(records)
    for result in results:
        writer.writerow(result.__dict__)

def main():
    """
    CLI Usage:
    python cleansing.py -f <file_path> -o <output_dir> -s <start_line>
    -f: Path to the input CSV file.
    -o: Path to the directory to save the output CSV file.
    -s: Line number to start processing from (default is 1).
    """
    start_time = datetime.now()

    file_path = sys.argv[2].strip()
    output_dir = sys.argv[4].strip() if len(sys.argv) > 4 else os.path.dirname(file_path)
    start_line = int(sys.argv[6].strip()) if len(sys.argv) > 6 else 1
    BATCH_SIZE_FOR_RECORDS = 100

    # Validate start_line
    if (start_line - 1) % BATCH_SIZE_FOR_RECORDS != 0:
        print(f"Error: start_line must be a multiple of {BATCH_SIZE_FOR_RECORDS} plus 1 (e.g., 1, 101, 201, ...).")
        sys.exit(1)
    output_file_path = os.path.join(output_dir, 'updated_' + os.path.basename(file_path))
    print(f"Processing file: {file_path}")
    print(f"Output file: {output_file_path}")
    print(f"Starting from line: {start_line}")
    print("=====================================")

    print(f"Processing started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    mode = 'a' if start_line > 1 else 'w'
    with open(output_file_path, mode=mode, newline='', encoding='utf-8') as output_file:
        writer = csv.DictWriter(output_file, fieldnames=get_csv_headers(file_path, encoding='shift-jis'))
        if start_line == 1:
            writer.writeheader()

        with open(file_path, mode='r', encoding='shift-jis', errors='ignore') as file:
            csv_reader = csv.DictReader(file)
            records = []
            try:
                for line_number, row in enumerate(csv_reader, start=1):
                    if line_number < start_line:
                        continue
                    record = create_record_from_row(row, csv_reader.fieldnames)
                    records.append(record)
                    if len(records) == BATCH_SIZE_FOR_RECORDS:
                        elapsed_time = datetime.now() - start_time
                        print(f"Processing records {line_number - BATCH_SIZE_FOR_RECORDS + 1} to {line_number}... (Elapsed time: {elapsed_time})")
                        batch_write_records(records, writer)
                        print(f"Processed lines up to: {line_number}")
                        records = []
                # Process any remaining records
                if records:
                    elapsed_time = datetime.now() - start_time
                    print(f"Processing records {line_number - BATCH_SIZE_FOR_RECORDS + 1} to {line_number}... (Elapsed time: {elapsed_time})")
                    batch_write_records(records, writer)
            except Exception as e:
                print(f"Exception occurred between lines {line_number - BATCH_SIZE_FOR_RECORDS + 1} and {line_number}: {e}")
                next_start_line = (line_number // BATCH_SIZE_FOR_RECORDS) * BATCH_SIZE_FOR_RECORDS + 1
                print(f"Processing interrupted. Next start line: {next_start_line}")
                sys.exit(1)

if __name__ == '__main__':
    main()
