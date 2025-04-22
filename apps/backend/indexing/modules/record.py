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

    def to_dict(self, keys: list[str]):
        return {key: getattr(self, key) for key in keys}
        
def create_record_from_row(row: dict, keys: list[str]):
    return Record(*(row[key] for key in keys))
