from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pymongo import MongoClient
from bson import ObjectId
from typing import List

app = FastAPI()

# MongoDB client setup
client = MongoClient("mongodb+srv://myUser:omernazeer@cluster0.7gioi.mongodb.net/my_database?retryWrites=true&w=majority")
db = client.my_database

students_collection = db.students
courses_collection = db.courses

# Convert ObjectId to and from string
def str_to_objectid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise ValueError("Invalid ObjectId format")

# Student model
class Student(BaseModel):
    id: str = Field(default_factory=str, alias="_id")
    name: str
    enrolled_courses: List[str] = []

    class Config:
        json_encoders = {ObjectId: str}

# Course model
class Course(BaseModel):
    id: str = Field(default_factory=str, alias="_id")
    name: str
    enrolled_students: List[str] = []

    class Config:
        json_encoders = {ObjectId: str}

# Create a student
@app.post("/students/", response_model=Student)
async def create_student(student: Student):
    try:
        student_dict = student.dict(exclude_unset=True)
        if "_id" in student_dict:
            student_dict["_id"] = str_to_objectid(student_dict["_id"])
        result = students_collection.insert_one(student_dict)
        student_dict["_id"] = str(result.inserted_id)  # Ensure _id is a string
        return student_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating student: {e}")

# Create a course
@app.post("/courses/", response_model=Course)
async def create_course(course: Course):
    try:
        course_dict = course.dict(exclude_unset=True)
        if "_id" in course_dict:
            course_dict["_id"] = str_to_objectid(course_dict["_id"])
        result = courses_collection.insert_one(course_dict)
        course_dict["_id"] = str(result.inserted_id)  # Ensure _id is a string
        return course_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating course: {e}")

# Enroll a student in a course
@app.post("/enroll/")
async def enroll_student(student_id: str, course_id: str):
    try:
        student = students_collection.find_one({"_id": str_to_objectid(student_id)})
        course = courses_collection.find_one({"_id": str_to_objectid(course_id)})

        if not student or not course:
            raise HTTPException(status_code=404, detail="Student or Course not found")

        # Update student with course reference
        students_collection.update_one(
            {"_id": str_to_objectid(student_id)},
            {"$addToSet": {"enrolled_courses": str_to_objectid(course_id)}}
        )

        # Update course with student reference
        courses_collection.update_one(
            {"_id": str_to_objectid(course_id)},
            {"$addToSet": {"enrolled_students": str_to_objectid(student_id)}}
        )

        return {"message": "Student enrolled in course"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enrolling student: {e}")

# Get all courses a student is enrolled in
@app.get("/students/{student_id}/courses/", response_model=List[Course])
async def get_student_courses(student_id: str):
    try:
        student = students_collection.find_one({"_id": str_to_objectid(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        course_ids = student.get("enrolled_courses", [])
        courses = list(courses_collection.find({"_id": {"$in": [str_to_objectid(id) for id in course_ids]}}))
        
        # Convert ObjectId to string for response consistency
        for course in courses:
            course["_id"] = str(course["_id"])
            course["enrolled_students"] = [str(student_id) for student_id in course.get("enrolled_students", [])]
        
        return courses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving student courses: {e}")

# Get all students enrolled in a specific course
@app.get("/courses/{course_id}/students/", response_model=List[Student])
async def get_course_students(course_id: str):
    try:
        course = courses_collection.find_one({"_id": str_to_objectid(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        student_ids = course.get("enrolled_students", [])
        students = list(students_collection.find({"_id": {"$in": [str_to_objectid(id) for id in student_ids]}}))
        
        # Convert ObjectId to string for response consistency
        for student in students:
            student["_id"] = str(student["_id"])
            student["enrolled_courses"] = [str(course_id) for course_id in student.get("enrolled_courses", [])]
        
        return students
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving course students: {e}")
