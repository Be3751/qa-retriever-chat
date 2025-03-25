import sys
import csv
from datetime import datetime
import concurrent.futures

from modules.record import create_record_from_row, Record
from modules.search import initialize_index, create_document_from_record, upload_documents, check_index_exists, check_document_exists, generate_document_key

def batch_upload_documents(records: list[Record]) -> None:
    """
    Uploads a list of records to the search index using a ThreadPoolExecutor"""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_index = {executor.submit(create_document_from_record, record): index for index, record in enumerate(records)}
        results: list[dict] = [None] * len(records)
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            record = records[index]
            if not check_document_exists(record):
                results[index] = future.result()
            else:
                print(f"Skipping upload for existing document with id: {generate_document_key(record)}")
    results = [result for result in results if result is not None]
    if results:
        try:
            upload_documents(results)
        except Exception as e:
            raise Exception(f"Error uploading documents: {e}")
    else:
        print("No new records to upload")

def main():
    """
    CLI options:
    -c, --create-index: create a new search index if it does not exist
    -u, --upload-to-existing-index: upload documents to an existing search index
    -d, --delete-index: delete existing documents in the search index
    -f, --file: path to the file to process
    -s, --start-line: line number to start processing from, if not specified, starts from the first line
    Example usage: 
      python indexing.py -c -f data.csv
      python indexing.py -u -f data.csv
      python indexing.py -u -f data.csv -s 101
    """
    start_time = datetime.now()

    exec_type = sys.argv[1].strip()
    if exec_type == "-c":
        print("Creating a new search index.")
        initialize_index()
    elif exec_type == "-u":
        print("Uploading documents to an existing search index.")
        if not check_index_exists():
            print("Error: Index does not exist. Please create a new index first.")
            sys.exit(1)
    elif exec_type == "-d":
        print("Not implemented yet.")
        sys.exit(0)
    else:
        print("Invalid option. Please specify one of the following options: -c, -u, -d")
        sys.exit(1)
    
    file_path = sys.argv[3].strip()
    start_line = int(sys.argv[5].strip()) if len(sys.argv) > 5 else 1
    BATCH_SIZE_FOR_RECORDS = 100

    # Validate start_line
    if (start_line - 1) % BATCH_SIZE_FOR_RECORDS != 0:
        print(f"Error: start_line must be a multiple of {BATCH_SIZE_FOR_RECORDS} plus 1 (e.g., 1, 101, 201, ...).")
        sys.exit(1)
    
    print(f"Processing file: {file_path}")
    print("=====================================")
    print(f"Starting from line: {start_line}")
    print(f"Processing started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    with open(file_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        records: list[Record] = []
        try:
            for line_number, row in enumerate(csv_reader, start=1):
                if line_number < start_line:
                    continue
                record = create_record_from_row(row)
                # Skip records labeled with "SKIPPED" for some reason in data cleaning
                if record.description == "SKIPPED" or record.comments_and_work_notes == "SKIPPED":
                    continue
                records.append(record)
                if len(records) == BATCH_SIZE_FOR_RECORDS:
                    elapsed_time = datetime.now() - start_time
                    print(f"Processing records {line_number - BATCH_SIZE_FOR_RECORDS + 1} to {line_number}... (Elapsed time: {elapsed_time})")
                    batch_upload_documents(records)
                    print(f"Processed lines up to: {line_number}")
                    records = []
            # Process any remaining records
            if records:
                elapsed_time = datetime.now() - start_time
                print(f"Processing records {line_number - len(records) + 1} to {line_number}... (Elapsed time: {elapsed_time})")
                batch_upload_documents(records)
                print(f"Processed lines up to: {line_number}")
        except Exception as e:
            print(f"Exception occurred at line {line_number}: {e}")
            next_start_line = (line_number // BATCH_SIZE_FOR_RECORDS) * BATCH_SIZE_FOR_RECORDS + 1
            print(f"Processing interrupted. Next start line: {next_start_line}")
            sys.exit(1)

if __name__ == "__main__":
    main()