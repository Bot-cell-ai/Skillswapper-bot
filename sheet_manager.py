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


def delete_user_by_id(user_id: str) -> bool:
    """
    Delete exactly one row whose 'User ID' equals user_id.
    Returns True if a row was deleted, False if not found.
    This is robust against row shifts because we search the column first.
    """
    # Locate the 'User ID' column (1-based index)
    headers = sheet.row_values(1)
    try:
        uid_col = headers.index("User ID") + 1  # exact header text
    except ValueError:
        raise RuntimeError(f'Header "User ID" not found. Headers present: {headers}')

    target = str(user_id).strip()
    # Get the whole 'User ID' column (row 1 is the header)
    col_vals = sheet.col_values(uid_col)

    # Scan from row 2 (skip header). row_idx here is the actual sheet row number.
    for row_idx, cell in enumerate(col_vals[1:], start=2):
        if str(cell).strip() == target:
            sheet.delete_rows(row_idx)
            return True

    return False

def delete_matched_users(user_id_1: str | int, user_id_2: str | int) -> int:
    """
    Delete exactly the two matched users (by 'User ID').
    Deletes bottom-up to avoid index shifting.
    Returns the number of rows deleted (0, 1, or 2).
    """
    # Locate the 'User ID' column
    headers = sheet.row_values(1)
    try:
        uid_col = headers.index("User ID") + 1
    except ValueError:
        raise RuntimeError(f'Header "User ID" not found. Headers present: {headers}')

    targets = {str(user_id_1).strip(), str(user_id_2).strip()}
    col_vals = sheet.col_values(uid_col)

    rows_to_delete = []
    seen = set()
    for row_idx, cell in enumerate(col_vals[1:], start=2):  # skip header row
        val = str(cell).strip()
        if val in targets and val not in seen:
            rows_to_delete.append(row_idx)
            seen.add(val)
            if len(seen) == 2:
                break  # we found both, stop scanning

    # Delete from bottom to top to avoid shifting
    for r in sorted(rows_to_delete, reverse=True):
        sheet.delete_rows(r)

    return len(rows_to_delete)
