## 使用方法

### コマンドライン引数
- `-f`（第一引数）: 参照元とするCSVファイルのファイルパス。（必須）
- `-o`（第二引数）: CSVファイルの出力先とするディレクトリパス。（必須）
- `-s`（第三引数）: CSVの途中の行から処理を開始するための行番号。指定されない場合、1行目から開始（任意）。
  - 100行ずつ処理しているため、開始位置は101, 201, 301, ... が許容されている。

### 注意点
- 予期しないエラーで処理が中断された場合、`Processing interrupted. Next start line: 201` の形式で次回の開始位置が出力されます。

### 使用例
```bash
# データクレンジングを実行
$ python indexing/cleansing.py -f indexing/input_csv/incident_all_20240421.csv -o indexing/output_csv

# 別のCSVファイル（データクレンジング済み）を指定して、データクレンジングを実行
$ python indexing/cleansing.py -f indexing/input_csv/incident_all_20250216.csv -o indexing/output_csv

# 途中の行（201行目）を指定して、データクレンジングを実行
$ python indexing/cleansing.py -f indexing/input_csv/incident_all_20240421.csv -o indexing/output_csv -s 201