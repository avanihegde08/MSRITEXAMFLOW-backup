
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from collections import defaultdict


def parse_time(date, time):
    return datetime.strptime(
        f"{date} {time}", "%Y-%m-%d %H:%M"
    )


def generate_timetable(dataset):

    students = dataset["students"]
    exams = dataset["exams"]
    rooms = dataset["rooms"]
    invigilators = dataset["invigilators"]
    slots = dataset["slots"]

    constraints = dataset.get("constraints", {})
    hard = constraints.get("hard", {})
    soft = constraints.get("soft", {})

    def enabled(settings, name):
        return settings.get(name, True)

    # --------------------------------------------------
    # 1. Validate input data
    # --------------------------------------------------

    slot_map = {s["id"]: s for s in slots}
    exam_map = {e["id"]: e for e in exams}
    room_map = {r["id"]: r for r in rooms}
    inv_map = {i["id"]: i for i in invigilators}
    student_map = {s["id"]: s for s in students}

    if len(slot_map) != len(slots):
        return {"status": "infeasible", "message": "Duplicate slot IDs"}

    if len(exam_map) != len(exams):
        return {"status": "infeasible", "message": "Duplicate exam IDs"}

    if len(room_map) != len(rooms):
        return {"status": "infeasible", "message": "Duplicate room IDs"}

    if len(inv_map) != len(invigilators):
        return {"status": "infeasible", "message": "Duplicate invigilator IDs"}

    if len(student_map) != len(students):
        return {"status": "infeasible", "message": "Duplicate student IDs"}

    try:
        slot_intervals = {}

        for slot in slots:
            start = parse_time(slot["date"], slot["start_time"])
            end = parse_time(slot["date"], slot["end_time"])

            if end <= start:
                raise ValueError(f"Invalid slot: {slot['id']}")

            slot_intervals[slot["id"]] = (start, end)

        for exam in exams:
            if exam["duration_minutes"] <= 0:
                raise ValueError(f"Invalid duration: {exam['id']}")

            if exam["required_invigilators_per_room"] < 0:
                raise ValueError(f"Invalid invigilator requirement: {exam['id']}")

        for room in rooms:
            if room["capacity"] <= 0:
                raise ValueError(f"Invalid room capacity: {room['id']}")

        for inv in invigilators:
            if inv["max_assignments"] < 0:
                raise ValueError(f"Invalid assignment limit: {inv['id']}")

        for student in students:
            for eid in student["exam_ids"]:
                if eid not in exam_map:
                    raise ValueError(
                        f"Unknown exam {eid} for student {student['id']}"
                    )

        for exam in exams:
            for sid in exam["eligible_slot_ids"]:
                if sid not in slot_map:
                    raise ValueError(
                        f"Unknown slot {sid} for exam {exam['id']}"
                    )

        for room in rooms:
            for sid in room["available_slot_ids"]:
                if sid not in slot_map:
                    raise ValueError(
                        f"Unknown slot {sid} for room {room['id']}"
                    )

        for inv in invigilators:
            for sid in inv["available_slot_ids"]:
                if sid not in slot_map:
                    raise ValueError(
                        f"Unknown slot {sid} for invigilator {inv['id']}"
                    )

    except (KeyError, TypeError, ValueError) as error:
        return {
            "status": "infeasible",
            "message": str(error)
        }

    # --------------------------------------------------
    # 2. Validate slot duration and eligible slots
    # --------------------------------------------------

    respect_duration = enabled(hard, "respect_exam_duration")
    respect_eligible = enabled(hard, "respect_exam_eligible_slots")
    respect_room_availability = enabled(hard, "respect_room_availability")
    respect_inv_availability = enabled(hard, "respect_invigilator_availability")

    candidates = {}

    for exam in exams:
        eid = exam["id"]

        if respect_eligible:
            candidates[eid] = exam["eligible_slot_ids"]
        else:
            candidates[eid] = list(slot_map.keys())

        if not candidates[eid]:
            return {
                "status": "infeasible",
                "message": f"No eligible slots for {eid}"
            }

        if respect_duration:
            candidates[eid] = [
                sid for sid in candidates[eid]
                if (
                    slot_intervals[sid][1] -
                    slot_intervals[sid][0]
                ).total_seconds() >= exam["duration_minutes"] * 60
            ]

        if not candidates[eid]:
            return {
                "status": "infeasible",
                "message": f"No sufficiently long slots for {eid}"
            }

    # --------------------------------------------------
    # 3. Calculate actual examination intervals
    # --------------------------------------------------

    exam_students = {
        exam["id"]: [
            student for student in students
            if exam["id"] in student["exam_ids"]
        ]
        for exam in exams
    }

    def exam_interval(eid, sid):
        start = slot_intervals[sid][0]
        end = start + timedelta(
            minutes=exam_map[eid]["duration_minutes"]
        )
        return start, end

    def overlaps(eid_a, sid_a, eid_b, sid_b):
        start_a, end_a = exam_interval(eid_a, sid_a)
        start_b, end_b = exam_interval(eid_b, sid_b)

        return start_a < end_b and start_b < end_a

    # --------------------------------------------------
    # 4. Create optimization model
    # --------------------------------------------------

    model = cp_model.CpModel()

    exam_slot = {}
    room_used = {}
    student_room = {}
    inv_assignment = {}

    # Each exam gets exactly one slot.

    for exam in exams:
        eid = exam["id"]

        for sid in candidates[eid]:
            exam_slot[eid, sid] = model.NewBoolVar(
                f"exam_{eid}_slot_{sid}"
            )

        model.Add(
            sum(exam_slot[eid, sid] for sid in candidates[eid]) == 1
        )

    # --------------------------------------------------
    # 5. Room assignment
    # --------------------------------------------------

    for exam in exams:
        eid = exam["id"]

        for room in rooms:
            rid = room["id"]

            for sid in candidates[eid]:

                if (
                    respect_room_availability
                    and sid not in room["available_slot_ids"]
                ):
                    continue

                key = (eid, rid, sid)

                room_used[key] = model.NewBoolVar(
                    f"room_{eid}_{rid}_{sid}"
                )

                model.Add(
                    room_used[key] <= exam_slot[eid, sid]
                )

    # --------------------------------------------------
    # 6. Student-to-room allocation
    # --------------------------------------------------

    for exam in exams:
        eid = exam["id"]

        for student in exam_students[eid]:
            stid = student["id"]

            for sid in candidates[eid]:

                assigned_rooms = []

                for room in rooms:
                    rid = room["id"]
                    key = (eid, rid, sid)

                    if key not in room_used:
                        continue

                    allocation_key = (stid, eid, rid, sid)

                    student_room[allocation_key] = model.NewBoolVar(
                        f"student_{stid}_{eid}_{rid}_{sid}"
                    )

                    model.Add(
                        student_room[allocation_key] <= room_used[key]
                    )

                    assigned_rooms.append(
                        student_room[allocation_key]
                    )

                # Every registered student gets exactly one room.

                model.Add(
                    sum(assigned_rooms) == exam_slot[eid, sid]
                )

    # --------------------------------------------------
    # 7. Room capacity and room usage
    # --------------------------------------------------

    allocated_count = {}

    respect_capacity = enabled(hard, "respect_room_capacity")

    for exam in exams:
        eid = exam["id"]

        for room in rooms:
            rid = room["id"]

            for sid in candidates[eid]:
                key = (eid, rid, sid)

                if key not in room_used:
                    continue

                allocated = sum(
                    student_room[
                        (student["id"], eid, rid, sid)
                    ]
                    for student in exam_students[eid]
                    if (student["id"], eid, rid, sid) in student_room
                )

                allocated_count[key] = allocated

                # Do not activate an empty room.

                model.Add(
                    room_used[key] <= allocated
                )

                if respect_capacity:
                    model.Add(
                        allocated <= room["capacity"] * room_used[key]
                    )

    # --------------------------------------------------
    # 8. Room double-booking
    # --------------------------------------------------

    if enabled(hard, "prevent_room_double_booking"):

        for room in rooms:
            rid = room["id"]

            keys = [
                key for key in room_used
                if key[1] == rid
            ]

            for i in range(len(keys)):
                for j in range(i + 1, len(keys)):

                    a = keys[i]
                    b = keys[j]

                    if overlaps(a[0], a[2], b[0], b[2]):
                        model.Add(
                            room_used[a] + room_used[b] <= 1
                        )

    # --------------------------------------------------
    # 9. Student examination clashes
    # --------------------------------------------------

    if enabled(hard, "prevent_student_exam_clashes"):

        for student in students:
            registered = [
                eid for eid in student["exam_ids"]
                if eid in exam_map
            ]

            for i in range(len(registered)):
                for j in range(i + 1, len(registered)):

                    ea = registered[i]
                    eb = registered[j]

                    for sa in candidates[ea]:
                        for sb in candidates[eb]:

                            if overlaps(ea, sa, eb, sb):
                                model.Add(
                                    exam_slot[ea, sa]
                                    + exam_slot[eb, sb] <= 1
                                )

    # --------------------------------------------------
    # 10. Invigilator assignment
    # --------------------------------------------------

    for exam in exams:
        eid = exam["id"]
        required = exam["required_invigilators_per_room"]

        for room in rooms:
            rid = room["id"]

            for sid in candidates[eid]:
                key = (eid, rid, sid)

                if key not in room_used:
                    continue

                eligible = [
                    inv for inv in invigilators
                    if (
                        not respect_inv_availability
                        or sid in inv["available_slot_ids"]
                    )
                ]

                assigned = []

                for inv in eligible:
                    iid = inv["id"]

                    ikey = (eid, rid, sid, iid)

                    inv_assignment[ikey] = model.NewBoolVar(
                        f"inv_{eid}_{rid}_{sid}_{iid}"
                    )

                    model.Add(
                        inv_assignment[ikey] <= room_used[key]
                    )

                    assigned.append(inv_assignment[ikey])

                model.Add(
                    sum(assigned) == required * room_used[key]
                )

    # --------------------------------------------------
    # 11. Invigilator clashes and workload
    # --------------------------------------------------

    inv_loads = {}

    for inv in invigilators:
        iid = inv["id"]

        assignments = [
            variable
            for key, variable in inv_assignment.items()
            if key[3] == iid
        ]

        inv_loads[iid] = sum(assignments)

        model.Add(
            inv_loads[iid] <= inv["max_assignments"]
        )

    if enabled(hard, "prevent_invigilator_double_booking"):

        for inv in invigilators:
            iid = inv["id"]

            keys = [
                key for key in inv_assignment
                if key[3] == iid
            ]

            for i in range(len(keys)):
                for j in range(i + 1, len(keys)):

                    a = keys[i]
                    b = keys[j]

                    if overlaps(a[0], a[2], b[0], b[2]):
                        model.Add(
                            inv_assignment[a] + inv_assignment[b] <= 1
                        )

    # --------------------------------------------------
    # 12. Soft optimization objectives
    # --------------------------------------------------

    objective = []

    # Minimize the number of rooms used.

    if soft.get("minimize_number_of_rooms_used", False):
        objective.append(
            10000 * sum(room_used.values())
        )

    # Minimize unused room capacity.

    if (
        soft.get("minimize_unused_room_capacity", False)
        and respect_capacity
    ):
        unused = []

        for key, used in room_used.items():
            eid, rid, sid = key

            unused.append(
                room_map[rid]["capacity"] * used
                - allocated_count[key]
            )

        objective.append(10 * sum(unused))

    # Balance invigilator workloads.

    if (
        soft.get("balance_invigilator_workload", False)
        and invigilators
    ):
        maximum = model.NewIntVar(0, 100000, "max_inv_load")
        minimum = model.NewIntVar(0, 100000, "min_inv_load")

        for load in inv_loads.values():
            model.Add(load <= maximum)
            model.Add(load >= minimum)

        objective.append(100 * (maximum - minimum))

    # Minimize gaps between a student's examinations.

    if soft.get("minimize_student_gaps", False):

        for student in students:
            registered = [
                eid for eid in student["exam_ids"]
                if eid in exam_map
            ]

            for i in range(len(registered)):
                for j in range(i + 1, len(registered)):

                    ea = registered[i]
                    eb = registered[j]

                    for sa in candidates[ea]:
                        for sb in candidates[eb]:

                            start_a, end_a = exam_interval(ea, sa)
                            start_b, end_b = exam_interval(eb, sb)

                            if end_a <= start_b:
                                gap = int(
                                    (start_b - end_a).total_seconds() / 60
                                )
                            elif end_b <= start_a:
                                gap = int(
                                    (start_a - end_b).total_seconds() / 60
                                )
                            else:
                                continue

                            if gap == 0:
                                continue

                            both = model.NewBoolVar(
                                f"gap_{student['id']}_{ea}_{sa}_{eb}_{sb}"
                            )

                            model.Add(both <= exam_slot[ea, sa])
                            model.Add(both <= exam_slot[eb, sb])

                            model.Add(
                                both >= exam_slot[ea, sa]
                                + exam_slot[eb, sb] - 1
                            )

                            objective.append(gap * both)

    if objective:
        model.Minimize(sum(objective))

    # --------------------------------------------------
    # 13. Run solver
    # --------------------------------------------------

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {
            "status": "infeasible",
            "message": "No feasible timetable found.",
            "solver_status": solver.StatusName(status)
        }

    # --------------------------------------------------
    # 14. Build timetable
    # --------------------------------------------------

    timetable = []

    for exam in exams:
        eid = exam["id"]

        for sid in candidates[eid]:

            if solver.Value(exam_slot[eid, sid]) != 1:
                continue

            for room in rooms:
                rid = room["id"]
                key = (eid, rid, sid)

                if key not in room_used:
                    continue

                if solver.Value(room_used[key]) != 1:
                    continue

                allocated_students = [
                    student["id"]
                    for student in exam_students[eid]
                    if solver.Value(
                        student_room[
                            (student["id"], eid, rid, sid)
                        ]
                    ) == 1
                ]

                allocated_invigilators = [
                    inv["id"]
                    for inv in invigilators
                    if (
                        eid, rid, sid, inv["id"]
                    ) in inv_assignment
                    and solver.Value(
                        inv_assignment[
                            (eid, rid, sid, inv["id"])
                        ]
                    ) == 1
                ]

                start, end = exam_interval(eid, sid)

                timetable.append({
    "exam_id": eid,
    "exam_name": exam["name"],
    "slot_id": sid,
    "date": start.strftime("%Y-%m-%d"),
    "start_time": start.strftime("%H:%M"),
    "end_time": end.strftime("%H:%M"),
    "room_id": rid,
    "room_name": room["name"],
    "room_capacity": room["capacity"],
    "student_ids": allocated_students,
    "student_count": len(allocated_students),
    "room_utilization_percent": round(
        len(allocated_students) / room["capacity"] * 100, 1
    ),
    "invigilator_ids": allocated_invigilators
})
    return {
        "status": "success",
        "timetable": timetable,
        "solver_status": solver.StatusName(status),

        "summary": {
            "exams_scheduled": len({
                row["exam_id"] for row in timetable
            }),
            "room_allocations": len(timetable),
            "rooms_used": len({
                row["room_id"] for row in timetable
            }),
            "student_room_allocations": sum(
                row["student_count"] for row in timetable
            )
        },

        "objective_value": solver.ObjectiveValue()
    }