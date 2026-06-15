from datetime import date, datetime
from typing import Optional


FORMATS = ["%Y-%m-%d", "%d %B %Y", "%d-%b-%Y", "%B %d, %Y", "%d/%m/%Y"]


def parse_date(value: str) -> Optional[date]:
    for fmt in FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def days_between(start: str, end: str) -> Optional[int]:
    d1 = parse_date(start)
    d2 = parse_date(end)
    if d1 and d2:
        return (d2 - d1).days
    return None
