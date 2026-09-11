from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass(frozen=True)
class TimeInterval:
    start: time
    end: time


def subtract_intervals(window: TimeInterval, blocked: list[TimeInterval]) -> list[TimeInterval]:
    remaining = [window]
    for block in sorted(blocked, key=lambda item: item.start):
        next_remaining: list[TimeInterval] = []
        for segment in remaining:
            if block.end <= segment.start or block.start >= segment.end:
                next_remaining.append(segment)
                continue
            if segment.start < block.start:
                next_remaining.append(TimeInterval(segment.start, block.start))
            if block.end < segment.end:
                next_remaining.append(TimeInterval(block.end, segment.end))
        remaining = next_remaining
    return [item for item in remaining if item.start < item.end]


def generate_candidate_slots(
    windows: list[TimeInterval],
    duration_minutes: int,
    granularity_minutes: int,
    now: datetime | None = None,
    target_date: date | None = None,
) -> list[time]:
    if duration_minutes <= 0 or granularity_minutes <= 0:
        return []
    slots: list[time] = []
    for window in windows:
        cursor = datetime.combine(target_date or date.today(), window.start)
        end = datetime.combine(target_date or date.today(), window.end)
        while cursor + timedelta(minutes=duration_minutes) <= end:
            if now is None or cursor >= now:
                slots.append(cursor.time().replace(second=0, microsecond=0))
            cursor += timedelta(minutes=granularity_minutes)
    return slots


def max_concurrent_overlaps(candidate: TimeInterval, existing: list[TimeInterval]) -> int:
    events: list[tuple[time, int]] = []
    for interval in existing:
        if interval.start < candidate.end and interval.end > candidate.start:
            start = max(interval.start, candidate.start)
            end = min(interval.end, candidate.end)
            events.extend(((start, 1), (end, -1)))
    active = 0
    maximum = 0
    for _, delta in sorted(events, key=lambda event: (event[0], 0 if event[1] == -1 else 1)):
        active += delta
        maximum = max(maximum, active)
    return maximum
