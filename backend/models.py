
from pydantic import BaseModel, Field


class Student(BaseModel):
    id: str
    name: str
    exam_ids: list[str]


class Exam(BaseModel):
    id: str
    name: str
    duration_minutes: int = Field(gt=0)
    required_invigilators_per_room: int = Field(ge=0)
    eligible_slot_ids: list[str]


class Room(BaseModel):
    id: str
    name: str
    building: str
    capacity: int = Field(gt=0)
    available_slot_ids: list[str]


class Invigilator(BaseModel):
    id: str
    name: str
    available_slot_ids: list[str]
    max_assignments: int = Field(ge=0)


class Slot(BaseModel):
    id: str
    date: str
    start_time: str
    end_time: str


class Constraints(BaseModel):
    hard: dict[str, bool] = Field(default_factory=dict)
    soft: dict[str, bool] = Field(default_factory=dict)


class Dataset(BaseModel):
    students: list[Student]
    exams: list[Exam]
    rooms: list[Room]
    invigilators: list[Invigilator]
    slots: list[Slot]
    constraints: Constraints
