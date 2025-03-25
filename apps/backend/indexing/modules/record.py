from datetime import datetime
import csv

class Record:
    def __init__(self, number, start_date, tag, urgency, status, watchlist, service, service2, service3, service_offering, service_offering_display_name, short_description, user, priority, assigned_group, assigned_to, update_date, updater, work_start_date, work_end_date, close_date, department_category1, description, comments_and_work_notes, hold_reason):
        self.number = number
        self.start_date = self.parse_date(start_date)
        self.tag = tag
        self.urgency = urgency
        self.status = status
        self.watchlist = watchlist
        self.service = service
        self.service2 = service2
        self.service3 = service3
        self.service_offering = service_offering
        self.service_offering_display_name = service_offering_display_name
        self.short_description = short_description
        self.user = user
        self.priority = priority
        self.assigned_group = assigned_group
        self.assigned_to = assigned_to
        self.update_date = self.parse_date(update_date)
        self.updater = updater
        self.work_start_date = self.parse_date(work_start_date)
        self.work_end_date = self.parse_date(work_end_date)
        self.close_date = self.parse_date(close_date)
        self.department_category1 = department_category1
        self.description = description
        self.comments_and_work_notes = comments_and_work_notes
        self.hold_reason = hold_reason

    def parse_date(self, date_str):
        if date_str:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return None

def create_record_from_row(row):
    return Record(
        row['番号'],
        row['開始日時'],
        row['タグ'],
        row['緊急度'],
        row['ステータス'],
        row['ウォッチリスト'],
        row['サービス'],
        row['サービス2'],
        row['サービス3'],
        row['サービスオファリング'],
        row['サービスオファリング表示名'],
        row['簡単な説明'],
        row['問い合わせユーザー'],
        row['優先度'],
        row['アサイン先グループ'],
        row['アサイン先'],
        row['更新日時'],
        row['更新者'],
        row['作業開始日時'],
        row['作業終了日時'],
        row['クローズ日時'],
        row['部門別カテゴリ1'],
        row['説明'],
        row['コメントと作業メモ'],
        row['保留理由']
    )

def parse_csv(file_path):
    with open(file_path, mode='r', encoding='shift-jis', errors='ignore') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            record = create_record_from_row(row)
            yield record