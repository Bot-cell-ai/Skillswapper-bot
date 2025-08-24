# matcher.py
"""
Matching rules:
1) If both new_user.skill and new_user.want are non-empty:
     Find an existing row where
        existing['Skill'].lower() == new_user['Want'].lower()
     AND existing['Want'].lower() == new_user['Skill'].lower()
   (mutual swap)

2) Cross match:
     If one user has Skill filled & Want blank
     AND the other has Skill blank & Want filled
     AND the filled values match exactly (case-insensitive).
"""

def _clean(s):
    return (s or "").strip().lower()

def find_one_match(new_row: dict, all_rows: list) -> dict | None:
    """
    new_row: dict with keys "User ID","Name","Skill","Want","Timestamp"
    all_rows: list of dict rows (sheet.get_all_records())
    Returns a matched row dict or None.
    """
    new_uid = str(new_row.get("User ID", ""))
    new_skill = _clean(new_row.get("Skill", ""))
    new_want = _clean(new_row.get("Want", ""))

    # iterate newest rows first
    for row in reversed(all_rows):
        try:
            other_uid = str(row.get("User ID", ""))
        except Exception:
            continue
        if other_uid == new_uid:
            continue  # skip self

        other_skill = _clean(row.get("Skill", ""))
        other_want = _clean(row.get("Want", ""))

        # Rule 1: both filled -> mutual exact swap
        if new_skill and new_want and other_skill and other_want:
            if new_skill == other_want and new_want == other_skill:
                return row

        # Rule 2: cross match (one has skill, one has want)
        if new_skill and not new_want and not other_skill and other_want:
            if new_skill == other_want:
                return row

        if not new_skill and new_want and other_skill and not other_want:
            if new_want == other_skill:
                return row

        # No match otherwise

    return None
