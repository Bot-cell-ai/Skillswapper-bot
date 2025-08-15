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

import logging
logger = logging.getLogger(__name__)

def _find_uid_col_index() -> int:
    """
    Return 1-based column index for header exactly matching "User ID".
    Raises RuntimeError if header not found.
    """
    headers = sheet.row_values(1)
    for idx, h in enumerate(headers, start=1):
        if str(h).strip() == "User ID":
            return idx
    raise RuntimeError(f'Header "User ID" not found. Current headers: {headers}')

def delete_user_by_id(user_id: str) -> bool:
    """
    Delete exactly one row whose 'User ID' equals user_id.
    Returns True if a row was deleted, False if not found.
    """
    uid_col = _find_uid_col_index()
    target = str(user_id).strip()

    col_vals = sheet.col_values(uid_col)  # includes header
    # scan rows starting from row 2 (skip header)
    for sheet_row, cell in enumerate(col_vals[1:], start=2):
        if str(cell).strip() == target:
            logger.info("delete_user_by_id: deleting row %s for User ID %s", sheet_row, target)
            sheet.delete_rows(sheet_row)
            return True

    logger.warning("delete_user_by_id: User ID %s not found (no deletion)", target)
    return False

def delete_matched_users(user_id_1, user_id_2) -> int:
    """
    Delete the two matched users by User ID.
    Returns number of rows deleted (0,1 or 2).
    Safety: will never delete more than 2 rows.
    """
    uid_col = _find_uid_col_index()
    targets = {str(user_id_1).strip(), str(user_id_2).strip()}
    targets.discard("")  # drop any blank

    logger.info("delete_matched_users: looking for IDs %s in column %d", targets, uid_col)

    col_vals = sheet.col_values(uid_col)  # includes header
    rows_to_delete = []
    seen = set()

    for sheet_row, cell in enumerate(col_vals[1:], start=2):
        val = str(cell).strip()
        if val in targets and val not in seen:
            rows_to_delete.append(sheet_row)
            seen.add(val)
            logger.info("delete_matched_users: found %s at row %d", val, sheet_row)
            if len(seen) == len(targets):
                break

    # safety check
    if len(rows_to_delete) > 2:
        raise RuntimeError(f"Safety: would delete >2 rows: {rows_to_delete}")

    if not rows_to_delete:
        logger.warning("delete_matched_users: no rows found for targets %s", targets)
        return 0

    # Delete bottom-up to avoid shifting
    for r in sorted(rows_to_delete, reverse=True):
        logger.info("delete_matched_users: deleting row %d", r)
        sheet.delete_rows(r)

    logger.info("delete_matched_users: deleted %d rows", len(rows_to_delete))
    return len(rows_to_delete)
