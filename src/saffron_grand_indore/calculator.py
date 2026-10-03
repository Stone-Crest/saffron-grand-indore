import re
from .knowledge import ROOMS_BY_TYPE, EXTRA_BED_CHARGE

NIGHTS_PATTERN = re.compile(r"(\d+)\s*night", re.IGNORECASE)
WORD_TO_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
EXTRA_BED_PATTERN = re.compile(r"(\d+|one|two|three|four|five)\s*extra\s*bed", re.IGNORECASE)
BARE_EXTRA_BED_PATTERN = re.compile(r"\bextra\s*bed\b", re.IGNORECASE)


def parse_extra_beds(text):
    match = EXTRA_BED_PATTERN.search(text)
    if match:
        val = match.group(1).lower()
        return int(val) if val.isdigit() else WORD_TO_NUM[val]
    if BARE_EXTRA_BED_PATTERN.search(text):
        return 1
    return 0


def extract_mentioned_room(text):
    for room_name in ROOMS_BY_TYPE:
        if re.search(rf"\b{re.escape(room_name)}\b", text, re.IGNORECASE):
            return room_name
    return None


def compute_stay_cost(text, history_text=""):
    room_name = extract_mentioned_room(text) or extract_mentioned_room(history_text)
    if not room_name:
        return None

    nights_match = NIGHTS_PATTERN.search(text) or NIGHTS_PATTERN.search(history_text)
    if not nights_match:
        return None
    nights = int(nights_match.group(1))

    extra_beds = parse_extra_beds(text) or parse_extra_beds(history_text)

    room = ROOMS_BY_TYPE[room_name]
    room_total = room["price_inr_per_night"] * nights
    extra_bed_total = EXTRA_BED_CHARGE * extra_beds * nights
    grand_total = room_total + extra_bed_total

    lines = [f"{room_name}: ₹{room['price_inr_per_night']}/night x {nights} night(s) = ₹{room_total}"]
    if extra_beds:
        lines.append(f"Extra beds: {extra_beds} x ₹{EXTRA_BED_CHARGE}/night x {nights} night(s) = ₹{extra_bed_total}")
    lines.append(f"Total estimated cost: ₹{grand_total}")

    return "Computed check:\n" + "\n".join(lines)