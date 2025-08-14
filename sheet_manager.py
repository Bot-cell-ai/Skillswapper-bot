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


def delete_user_by_id(user_id: str):
    """Delete first row with matching User ID (header is row 1)."""
    records = sheet.get_all_records()
    for i, record in enumerate(records, start=2):
        if str(record.get("User ID")) == str(user_id):
            sheet.delete_rows(i)
            break
