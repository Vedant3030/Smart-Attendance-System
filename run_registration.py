import tkinter as tk
from attendance_config import DB_CONFIG, FACE_RECOGNITION_CONFIG, CAMERA_CONFIG
from database_manager import DatabaseManager
from face_recognition_engine import FaceRecognitionEngine
from camera_manager import CameraManager
from registration_app import RegistrationApp

if __name__ == "__main__":
    # Initialize managers
    db = DatabaseManager(DB_CONFIG)
    face_engine = FaceRecognitionEngine(FACE_RECOGNITION_CONFIG)
    camera_mgr = CameraManager(CAMERA_CONFIG)
    
    # Create and run application
    root = tk.Tk()
    app = RegistrationApp(root, db, face_engine, camera_mgr)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
    
    # Cleanup
    db.close()
