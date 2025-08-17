# sheet_manager.py
import os
import json
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

SHEET_NAME = os.getenv("SHEET_NAME", "SkillSwapper")

# Build creds from secret JSON
sa = json.loads(os.environ["GSHEETS_SERVICE_ACCOUNT_JSON"])
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(sa, scopes=scopes)
gc = gspread.authorize(creds)
sheet = gc.open(SHEET_NAME).sheet1


def save_user_row(user_id: int, name: str, skill: str, want: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [str(user_id), name or "", skill or "", want or "", ts]
    sheet.append_row(row)


def get_all_records():
    return sheet.get_all_records()


from matcher import find_one_match  # ADD THIS AT TOP

def delete_matched_pair(new_row: dict):
    """
    Delete both users (the new_row and the matched row) based on Skill/Want matching rules.
    """
    all_rows = sheet.get_all_records()
    match = find_one_match(new_row, all_rows)
    if not match:
        return False

    def _clean(s):
        return (s or "").strip().lower()

    new_skill = _clean(new_row.get("Skill"))
    new_want = _clean(new_row.get("Want"))
    match_skill = _clean(match.get("Skill"))
    match_want = _clean(match.get("Want"))

    # Collect rows to delete (find them in the sheet by comparing skill/want)
    records = sheet.get_all_records()
    rows_to_delete = []
    for i, record in enumerate(records, start=2):  # row 1 is header
        skill = _clean(record.get("Skill"))
        want = _clean(record.get("Want"))
        if (skill == new_skill and want == new_want) or \
           (skill == match_skill and want == match_want):
            rows_to_delete.append(i)

    for row in sorted(rows_to_delete, reverse=True):
        sheet.delete_rows(row)

    return True