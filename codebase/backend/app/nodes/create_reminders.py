"""Graph node: generate medication reminders from a processed prescription."""
import re


def _parse_times_per_day(med: dict) -> int:
    if isinstance(med.get("times_per_day"), int) and med["times_per_day"] > 0:
        return med["times_per_day"]

    schedule = (med.get("schedule") or "").lower()
    if not schedule:
        return 0

    match = re.search(r"(\d+)\s*(lan|lần)", schedule)
    if match:
        return int(match.group(1))

    if "sáng" in schedule and "trưa" in schedule and "tối" in schedule:
        return 3
    if "sáng" in schedule and "tối" in schedule and "trưa" not in schedule:
        return 2
    if "trưa" in schedule and "tối" in schedule and "sáng" not in schedule:
        return 2
    if "sáng" in schedule and "trưa" in schedule and "tối" not in schedule:
        return 2
    if "sau ăn" in schedule and "trước ăn" not in schedule:
        if "sáng" in schedule and "trưa" in schedule and "tối" in schedule:
            return 3
        if "sáng" in schedule and "tối" in schedule:
            return 2
    if "trước ăn" in schedule or "sau ăn" in schedule:
        if "sáng" in schedule and "tối" in schedule and "trưa" not in schedule:
            return 2
        if "sáng" in schedule and "trưa" in schedule and "tối" in schedule:
            return 3

    if "1" in schedule or "một" in schedule:
        return 1
    if "2" in schedule or "hai" in schedule:
        return 2
    if "3" in schedule or "ba" in schedule:
        return 3
    if "4" in schedule or "bốn" in schedule or "bon" in schedule:
        return 4

    return 0


def _schedule_to_times(schedule: str, count: int) -> list[str]:
    schedule = (schedule or "").lower()
    if count == 1:
        return ["07:30"]
    if count == 2:
        if "sáng" in schedule and "tối" in schedule and "trưa" not in schedule:
            return ["08:00", "20:00"]
        return ["08:00", "20:00"]
    if count == 3:
        if "sáng" in schedule and "trưa" in schedule and "tối" in schedule:
            return ["07:00", "12:30", "19:00"]
        return ["07:00", "12:30", "19:00"]
    if count == 4:
        return ["07:00", "12:00", "16:30", "21:00"]
    return ["07:30"]


def _display_label_base(med: dict) -> str:
    name = med.get("raw_name") or med.get("name") or "Thuốc"
    dose = (med.get("dose") or "").strip()
    strength = (med.get("strength") or "").strip()

    if dose and strength:
        return f"{name} {strength} {dose}"
    if dose:
        return f"{name} {dose}"
    if strength:
        return f"{name} {strength}"
    return name


def _label_for_time(label_base: str, schedule_str: str, time: str) -> str:
    schedule = (schedule_str or "").lower()
    if "trước ăn sáng" in schedule or "truoc an sang" in schedule:
        return f"{label_base} trước ăn sáng"
    if "sau ăn sáng" in schedule or "sau an sang" in schedule:
        return f"{label_base} sau ăn sáng"
    if "trước ăn trưa" in schedule or "truoc an trua" in schedule:
        return f"{label_base} trước ăn trưa"
    if "sau ăn trưa" in schedule or "sau an trua" in schedule:
        return f"{label_base} sau ăn trưa"
    if "trước ăn tối" in schedule or "truoc an toi" in schedule:
        return f"{label_base} trước ăn tối"
    if "sau ăn tối" in schedule or "sau an toi" in schedule:
        return f"{label_base} sau ăn tối"
    if "trước khi ngủ" in schedule or "truoc khi ngu" in schedule:
        return f"{label_base} trước khi ngủ"
    if "sáng" in schedule and time in {"07:00", "07:30", "08:00"}:
        return f"{label_base} vào buổi sáng"
    if "trưa" in schedule and time in {"12:00", "12:30"}:
        return f"{label_base} vào buổi trưa"
    if "chiều" in schedule and time == "16:30":
        return f"{label_base} vào buổi chiều"
    if "tối" in schedule and time in {"19:00", "20:00", "21:00"}:
        return f"{label_base} buổi tối"
    if time == "07:30" or time == "08:00":
        return f"{label_base} sáng"
    if time in {"12:00", "12:30"}:
        return f"{label_base} trưa"
    if time == "16:30":
        return f"{label_base} chiều"
    if time in {"19:00", "20:00", "21:00"}:
        return f"{label_base} tối"
    return f"{label_base} vào {time}"


def _group_nearby_reminder_times(reminders: list[dict[str, str]], threshold: int = 30) -> list[dict[str, str]]:
    def to_minutes(time: str) -> int:
        hours, minutes = (time or "00:00").split(":")
        return int(hours) * 60 + int(minutes)

    sorted_reminders = sorted(reminders, key=lambda item: to_minutes(item.get("time", "00:00")))
    grouped: list[dict[str, str]] = []

    for item in sorted_reminders:
        item_minutes = to_minutes(item.get("time", "00:00"))
        if grouped:
            last = grouped[-1]
            last_minutes = to_minutes(last["time"])
            if item_minutes - last_minutes <= threshold:
                item["time"] = last["time"]
        grouped.append(item)

    return grouped


async def create_reminders(state: dict) -> dict:
    """Generate reminder items from a processed prescription state."""
    prescription = state.get("prescription") or {}
    medications = prescription.get("medications", [])

    reminders: list[dict[str, str]] = []
    for med in medications:
        label_base = _display_label_base(med)
        schedule_str = med.get("schedule") or med.get("notes") or ""
        count = _parse_times_per_day(med)
        if count <= 0:
            count = _parse_times_per_day({"schedule": schedule_str})
        if count <= 0:
            count = 1

        times = _schedule_to_times(schedule_str, count)
        times = times[:count]

        for time in times:
            reminders.append(
                {
                    "medicationId": med.get("id") or med.get("medicationId") or "",
                    "label": _label_for_time(label_base, schedule_str, time),
                    "time": time,
                }
            )

    grouped = _group_nearby_reminder_times(reminders)
    return {**state, "reminders": grouped}
