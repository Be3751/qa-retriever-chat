import os
import csv
import sys
from datetime import datetime
import concurrent.futures

from modules.record import create_record_from_row
from modules.prompt import cleanse_record

def batch_cleanse_records(records):
    """
    Cleanse each record in a given list of records in parallel using threads.
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_index = {executor.submit(cleanse_record, record): index for index, record in enumerate(records)}
        results: list[dict] = [None] * len(records)
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            results[index] = future.result()
    return results

# CLI usage: python indexing/cleansing.py -f <file_path> -o <output_dir> -s <start_line>
def main():
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
        fieldnames = [
            '番号', '開始日時', 'タグ', '緊急度', 'ステータス', 'ウォッチリスト', 'サービス', 'サービス2', 'サービス3', 
            'サービスオファリング', 'サービスオファリング表示名', '簡単な説明', '問い合わせユーザー', '優先度', 
            'アサイン先グループ', 'アサイン先', '更新日時', '更新者', '作業開始日時', '作業終了日時', 'クローズ日時', 
            '部門別カテゴリ1', '説明', 'コメントと作業メモ', '保留理由'
        ]
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        if start_line == 1:
            writer.writeheader()

        with open(file_path, mode='r', encoding='shift-jis', errors='ignore') as file:
            csv_reader = csv.DictReader(file)
            records = []
            try:
                for line_number, row in enumerate(csv_reader, start=1):
                    if line_number < start_line:
                        continue
                    record = create_record_from_row(row)
                    records.append(record)
                    if len(records) == BATCH_SIZE_FOR_RECORDS:
                        elapsed_time = datetime.now() - start_time
                        print(f"Processing records {line_number - BATCH_SIZE_FOR_RECORDS + 1} to {line_number}... (Elapsed time: {elapsed_time})")
                        results = batch_cleanse_records(records)
                        for result in results:
                            writer.writerow(result)
                        print(f"Processed lines up to: {line_number}")
                        records = []
                # Process any remaining records
                if records:
                    elapsed_time = datetime.now() - start_time
                    print(f"Processing records {line_number - BATCH_SIZE_FOR_RECORDS + 1} to {line_number}... (Elapsed time: {elapsed_time})")
                    results = batch_cleanse_records(records)
                    for result in results:
                        writer.writerow(result)
            except Exception as e:
                print(f"Exception occurred between lines {line_number - BATCH_SIZE_FOR_RECORDS + 1} and {line_number}: {e}")
                next_start_line = (line_number // BATCH_SIZE_FOR_RECORDS) * BATCH_SIZE_FOR_RECORDS + 1
                print(f"Processing interrupted. Next start line: {next_start_line}")
                sys.exit(1)

if __name__ == '__main__':
    main()
