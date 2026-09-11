from datetime import date, time

from app.schedule.availability import TimeInterval, generate_candidate_slots, max_concurrent_overlaps, subtract_intervals


def test_subtract_intervals_respects_a_partial_block() -> None:
    window = TimeInterval(time(8, 0), time(12, 0))
    blocked = [TimeInterval(time(10, 0), time(10, 30))]

    assert subtract_intervals(window, blocked) == [
        TimeInterval(time(8, 0), time(10, 0)),
        TimeInterval(time(10, 30), time(12, 0)),
    ]


def test_generate_slots_does_not_cross_the_end_of_a_window() -> None:
    slots = generate_candidate_slots(
        [TimeInterval(time(8, 0), time(10, 0))],
        duration_minutes=45,
        granularity_minutes=15,
        target_date=date(2026, 9, 10),
    )

    assert slots == [time(8, 0), time(8, 15), time(8, 30), time(8, 45), time(9, 0), time(9, 15)]


def test_capacity_counts_the_maximum_overlap_not_total_intervals() -> None:
    candidate = TimeInterval(time(8, 0), time(9, 0))
    existing = [
        TimeInterval(time(8, 0), time(8, 20)),
        TimeInterval(time(8, 40), time(9, 0)),
    ]

    assert max_concurrent_overlaps(candidate, existing) == 1
    assert max_concurrent_overlaps(candidate, existing) < 2


def test_capacity_two_rejects_a_third_simultaneous_service() -> None:
    candidate = TimeInterval(time(8, 0), time(8, 30))
    existing = [
        TimeInterval(time(8, 0), time(8, 30)),
        TimeInterval(time(8, 0), time(8, 30)),
    ]

    assert max_concurrent_overlaps(candidate, existing) == 2
    assert not max_concurrent_overlaps(candidate, existing) < 2
