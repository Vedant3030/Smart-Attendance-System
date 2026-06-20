from typing import List, Optional
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from datetime import datetime

from attendance_config import DB_CONFIG, FACE_RECOGNITION_CONFIG
from database_manager import DatabaseManager
from face_recognition_engine import FaceRecognitionEngine

app = FastAPI(
    title="Attendance System API",
    description="Backend API for Face Recognition Attendance System",
    version="1.0.0"
)

db = DatabaseManager(DB_CONFIG)
face_engine = FaceRecognitionEngine(FACE_RECOGNITION_CONFIG)


class StudentRegistrationPayload(BaseModel):
    prn: str
    class_id: int
    roll_no: int
    name: str
    email: str
    face_encoding: List[float]


class MultiPhotoEnrollmentPayload(BaseModel):
    """Multi-photo enrollment for improved recognition accuracy."""
    prn: str
    class_id: int
    roll_no: int
    name: str
    email: str
    face_encodings: List[List[float]]  # Multiple photos


class AttendanceLogPayload(BaseModel):
    """Log attendance with optional direction (IN/OUT)."""
    prn: str
    subject_id: int
    camera_id: Optional[str] = None
    direction: Optional[str] = None  # 'IN', 'OUT', or None
    confidence: Optional[float] = None


class CameraConfigPayload(BaseModel):
    """Configure camera direction for IN/OUT tracking."""
    camera_id: str
    direction: str  # 'IN', 'OUT', or 'BOTH'


@app.get("/")
async def root():
    return {
        "message": "Attendance API is running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/classes")
async def list_classes():
    classes = db.get_all_classes()
    return [
        {"id": class_id, "name": class_name}
        for class_name, class_id in classes.items()
    ]


@app.get("/subjects")
async def list_subjects():
    subjects = db.get_all_subjects()
    return [
        {"id": subject_id, "name": subject_name}
        for subject_name, subject_id in subjects.items()
    ]


@app.post("/register")
async def register_student(payload: StudentRegistrationPayload):
    try:
        encoding_array = np.array(payload.face_encoding, dtype=np.float32)

        success, message = db.register_student(
            payload.prn,
            payload.class_id,
            payload.roll_no,
            payload.name,
            payload.email,
            encoding_array,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {"detail": message, "enrolled_at": datetime.now().isoformat()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/enroll-multi-photo")
async def enroll_with_multiple_photos(payload: MultiPhotoEnrollmentPayload):
    """Enroll a student with multiple face photos for improved accuracy."""
    try:
        if not payload.face_encodings:
            raise HTTPException(status_code=400, detail="At least one face encoding required")

        if len(payload.face_encodings) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 photos per enrollment")

        # Average multiple encodings for a more robust embedding
        encodings = [np.array(enc, dtype=np.float32) for enc in payload.face_encodings]
        averaged_encoding = np.mean(encodings, axis=0)

        success, message = db.register_student(
            payload.prn,
            payload.class_id,
            payload.roll_no,
            payload.name,
            payload.email,
            averaged_encoding,
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "detail": message,
            "photos_enrolled": len(payload.face_encodings),
            "enrolled_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/students")
async def get_students():
    if not hasattr(db, "get_all_students"):
        return {"message": "Student listing not implemented yet"}
    return db.get_all_students()


@app.get("/attendance")
async def get_attendance():
    if not hasattr(db, "get_attendance_logs"):
        return {"message": "Attendance logs not implemented yet"}
    return db.get_attendance_logs()


@app.post("/attendance/log")
async def log_attendance(payload: AttendanceLogPayload):
    """Log attendance for a recognized person."""
    try:
        success = db.log_attendance(payload.prn, payload.subject_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to log attendance")

        direction = payload.direction or "UNKNOWN"
        return {
            "detail": "Attendance logged successfully",
            "prn": payload.prn,
            "direction": direction,
            "confidence": payload.confidence,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cameras/config")
async def configure_camera(payload: CameraConfigPayload):
    """Set camera direction (IN/OUT/BOTH) for IN-OUT tracking."""
    try:
        if payload.direction not in ('IN', 'OUT', 'BOTH'):
            raise HTTPException(status_code=400, detail="Invalid direction. Must be IN, OUT, or BOTH")

        face_engine.set_camera_direction(payload.camera_id, payload.direction)
        return {
            "detail": "Camera configured successfully",
            "camera_id": payload.camera_id,
            "direction": payload.direction
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cameras/{camera_id}/direction")
async def get_camera_direction(camera_id: str):
    """Get the configured direction for a camera."""
    direction = face_engine.get_camera_direction(camera_id)
    return {"camera_id": camera_id, "direction": direction}


class StartSessionPayload(BaseModel):
    class_id: int
    subject_id: int


class SessionDetectPayload(BaseModel):
    prns: List[str]


@app.post("/sessions/start")
async def start_session(payload: StartSessionPayload):
    """Start a classroom session"""
    try:
        session_id = db.start_session(payload.class_id, payload.subject_id)
        return {
            "detail": "Session started",
            "session_id": session_id,
            "class_id": payload.class_id,
            "subject_id": payload.subject_id,
            "start_time": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/active")
async def get_active_session():
    """Get active session info"""
    try:
        session = db.get_active_session()
        return session or {"session_id": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/{session_id}/detect")
async def log_session_detections(session_id: int, payload: SessionDetectPayload):
    """Log student face detections during a session"""
    try:
        db.log_session_detections(session_id, payload.prns)
        return {
            "detail": f"Logged {len(payload.prns)} detections",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/{session_id}/end")
async def end_session(session_id: int):
    """End a classroom session and calculate final 80% attendance"""
    try:
        success, message, results = db.end_session(session_id)
        if not success:
            raise HTTPException(status_code=400, detail=message)
        return {
            "detail": message,
            "session_id": session_id,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)