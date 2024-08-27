from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List

# FastAPI app and MongoDB Atlas connection using pymongo
app = FastAPI()

# MongoDB Atlas connection using pymongo
uri = "mongodb+srv://optimizations44:gjnQah1SK7eYvhXp@cluster0.y90og.mongodb.net/my_database?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client.my_database

students_collection = db.students
courses_collection = db.courses

# Custom ObjectId type for MongoDB
class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if isinstance(value, ObjectId):
            return str(value)
        try:
            return str(ObjectId(value))
        except Exception:
            raise ValueError("Invalid ObjectId")

# Pydantic models
class Student(BaseModel):
    id: PyObjectId = Field(default_factory=str, alias="_id")
    name: str
    enrolled_courses: List[PyObjectId] = []

    class Config:
        json_encoders = {ObjectId: str}

class Course(BaseModel):
    id: PyObjectId = Field(default_factory=str, alias="_id")
    name: str
    enrolled_students: List[PyObjectId] = []

    class Config:
        json_encoders = {ObjectId: str}

# Create a student
@app.post("/students/", response_model=Student)
async def create_student(student: Student):
    try:
        student_dict = student.dict(exclude_unset=True)
        result = await students_collection.insert_one(student_dict)
        student_dict["_id"] = str(result.inserted_id)  # Ensure _id is a string
        return student_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating student: {e}")

# Create a course
@app.post("/courses/", response_model=Course)
async def create_course(course: Course):
    try:
        course_dict = course.dict(exclude_unset=True)
        result = await courses_collection.insert_one(course_dict)
        course_dict["_id"] = str(result.inserted_id)  # Ensure _id is a string
        return course_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating course: {e}")

# Enroll a student in a course
@app.post("/enroll/")
async def enroll_student(student_id: str, course_id: str):
    try:
        student = await students_collection.find_one({"_id": ObjectId(student_id)})
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})

        if not student or not course:
            raise HTTPException(status_code=404, detail="Student or Course not found")

        # Update student with course reference
        await students_collection.update_one(
            {"_id": ObjectId(student_id)},
            {"$addToSet": {"enrolled_courses": ObjectId(course_id)}}
        )

        # Update course with student reference
        await courses_collection.update_one(
            {"_id": ObjectId(course_id)},
            {"$addToSet": {"enrolled_students": ObjectId(student_id)}}
        )

        return {"message": "Student enrolled in course"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enrolling student: {e}")

# Get all courses a student is enrolled in
@app.get("/students/{student_id}/courses/", response_model=List[Course])
async def get_student_courses(student_id: str):
    try:
        student = await students_collection.find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        course_ids = student.get("enrolled_courses", [])
        courses = await courses_collection.find({"_id": {"$in": [ObjectId(id) for id in course_ids]}}).to_list(length=None)
        return courses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving student courses: {e}")

# Get all students enrolled in a specific course
@app.get("/courses/{course_id}/students/", response_model=List[Student])
async def get_course_students(course_id: str):
    try:
        course = await courses_collection.find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        student_ids = course.get("enrolled_students", [])
        students = await students_collection.find({"_id": {"$in": [ObjectId(id) for id in student_ids]}}).to_list(length=None)
        return students
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving course students: {e}")
