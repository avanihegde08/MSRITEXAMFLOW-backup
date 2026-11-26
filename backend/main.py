from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json

from models import Dataset
from solver import generate_timetable

app = FastAPI(title="MSRITFlow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "sample_data.json"
)


def get_dataset():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return Dataset.model_validate(data).model_dump()

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Dataset file not found"
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.get("/")
def home():
    return {"message": "Welcome to MSRITFlow API"}

@app.get("/api/dataset")
def dataset():
    return get_dataset()
    
@app.put("/api/dataset")
def update_dataset(dataset: Dataset):
    try:
        data = dataset.model_dump()

        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

        return {
            "status": "success",
            "message": "Dataset saved successfully"
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.get("/api/students")
def students():
    return get_dataset()["students"]


@app.get("/api/exams")
def exams():
    return get_dataset()["exams"]


@app.get("/api/rooms")
def rooms():
    return get_dataset()["rooms"]


@app.get("/api/invigilators")
def invigilators():
    return get_dataset()["invigilators"]


@app.get("/api/slots")
def slots():
    return get_dataset()["slots"]


@app.post("/api/generate-timetable")
def generate_exam_timetable():

    data = get_dataset()

    result = generate_timetable(data)

    if result["status"] != "success":
        raise HTTPException(
            status_code=422,
            detail=result["message"]
        )

    return result