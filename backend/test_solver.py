
import json
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta
from models import Dataset
from solver import generate_timetable


DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "sample_data.json"
)


def to_datetime(date, time):
    return datetime.strptime(
        f"{date} {time}", "%Y-%m-%d %H:%M"
    )


def overlaps(a, b):
    return (
        a[0] < b[1]
        and b[0] < a[1]
    )


def test_generate_timetable():

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        raw_data = json.load(file)

    dataset = Dataset.model_validate(raw_data).model_dump()

    result = generate_timetable(dataset)

    print("\nSolver result:")
    print(json.dumps(result, indent=4))

    # The corrected sample dataset should be feasible.
    assert result["status"] == "success", result.get("message")

    timetable = result["timetable"]

    students = dataset["students"]
    exams = {e["id"]: e for e in dataset["exams"]}
    rooms = {r["id"]: r for r in dataset["rooms"]}
    invigilators = {
        i["id"]: i for i in dataset["invigilators"]
    }
    slots = {s["id"]: s for s in dataset["slots"]}

    # Store actual examination intervals.
    exam_intervals = {}

    for exam in dataset["exams"]:
        eid = exam["id"]

        matching = [
            row for row in timetable
            if row["exam_id"] == eid
        ]

        assert matching, f"No room allocated for exam {eid}"

        slot_ids = {row["slot_id"] for row in matching}
        assert len(slot_ids) == 1, (
            f"Exam {eid} assigned to multiple slots"
        )

        sid = next(iter(slot_ids))
        assert sid in exam["eligible_slot_ids"], (
            f"Exam {eid} assigned to an ineligible slot"
        )

        slot = slots[sid]
        start = to_datetime(slot["date"], slot["start_time"])
        end = start + timedelta(
    minutes=exam["duration_minutes"]
)

        exam_intervals[eid] = (start, end)

        assert end <= to_datetime(
            slot["date"], slot["end_time"]
        ), f"Exam {eid} exceeds its slot duration"

    # Every registered student must receive exactly one room.
    for exam in dataset["exams"]:
        eid = exam["id"]

        registered = [
            student["id"]
            for student in students
            if eid in student["exam_ids"]
        ]

        allocated = [
            sid
            for row in timetable
            if row["exam_id"] == eid
            for sid in row["student_ids"]
        ]

        assert Counter(allocated) == Counter(registered), (
            f"Student allocation error in {eid}"
        )

    # Check room capacity and availability.
    for row in timetable:
        room = rooms[row["room_id"]]

        assert row["student_count"] <= room["capacity"], (
            f"Room capacity exceeded: {room['room_id']}"
        )

        assert row["slot_id"] in room["available_slot_ids"], (
            f"Room unavailable: {room['room_id']}"
        )

        assert row["student_count"] == len(row["student_ids"])

    # Check required invigilators and availability.
    inv_load = Counter()

    for row in timetable:
        exam = exams[row["exam_id"]]

        assert len(row["invigilator_ids"]) == (
            exam["required_invigilators_per_room"]
        ), f"Wrong invigilator count for {row['exam_id']}"

        assert len(set(row["invigilator_ids"])) == (
            len(row["invigilator_ids"])
        ), "Duplicate invigilator assignment"

        for iid in row["invigilator_ids"]:
            assert iid in invigilators, f"Unknown invigilator {iid}"

            inv = invigilators[iid]

            assert row["slot_id"] in inv["available_slot_ids"], (
                f"Invigilator unavailable: {iid}"
            )

            inv_load[iid] += 1

    for iid, count in inv_load.items():
        assert count <= invigilators[iid]["max_assignments"], (
            f"Invigilator workload exceeded: {iid}"
        )

    # Check room double-booking.
    for i in range(len(timetable)):
        for j in range(i + 1, len(timetable)):

            a = timetable[i]
            b = timetable[j]

            if a["room_id"] == b["room_id"]:
                assert not overlaps(
                    exam_intervals[a["exam_id"]],
                    exam_intervals[b["exam_id"]]
                ), f"Room clash: {a['room_id']}"

    # Check invigilator double-booking.
    for i in range(len(timetable)):
        for j in range(i + 1, len(timetable)):

            a = timetable[i]
            b = timetable[j]

            common = (
                set(a["invigilator_ids"])
                & set(b["invigilator_ids"])
            )

            if common:
                assert not overlaps(
                    exam_intervals[a["exam_id"]],
                    exam_intervals[b["exam_id"]]
                ), f"Invigilator clash: {common}"

    # Check student examination clashes.
    for student in students:
        registered = [
            eid for eid in student["exam_ids"]
            if eid in exams
        ]

        for i in range(len(registered)):
            for j in range(i + 1, len(registered)):

                a = exam_intervals[registered[i]]
                b = exam_intervals[registered[j]]

                assert not overlaps(a, b), (
                    f"Student clash: {student['id']}"
                )

    print("\nALL BACKEND SCHEDULING TESTS PASSED!")


if __name__ == "__main__":
    test_generate_timetable()
