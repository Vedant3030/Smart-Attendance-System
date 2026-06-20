# attendance_kiosk.py
"""
Professional Attendance Kiosk with Enhanced UI and Real-time Recognition
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import threading
import time
from datetime import datetime
from collections import deque

class AttendanceKiosk:
    def __init__(self, root, db_manager, face_engine, camera_manager):
        self.root = root
        self.db = db_manager
        self.face_engine = face_engine
        self.camera_manager = camera_manager
        
        self.root.title("Attendance Kiosk - Face Recognition System")
        self.root.geometry("1400x800")
        self.root.configure(bg='#f0f0f0')
        
        # Variables
        self.current_frame = None
        self.is_camera_running = False
        self.video_thread = None
        self.subjects = {}
        self.selected_subject = tk.StringVar()
        self.selected_camera = tk.StringVar()
        self.last_seen = {}  # Cooldown tracking
        self.cooldown_period = 300  # 5 minutes
        self.recent_logs = deque(maxlen=10)  # Recent attendance logs
        
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        """Create the user interface"""
        # Title Bar
        title_frame = tk.Frame(self.root, bg='#1976D2', height=70)
        title_frame.pack(fill='x', side='top')
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, 
            text="🎓 Attendance Kiosk System", 
            font=("Arial", 24, "bold"),
            bg='#1976D2', 
            fg='white'
        )
        title_label.pack(side='left', padx=30, pady=15)
        
        # Current date/time
        self.datetime_label = tk.Label(
            title_frame,
            text="",
            font=("Arial", 12),
            bg='#1976D2',
            fg='white'
        )
        self.datetime_label.pack(side='right', padx=30)
        self.update_datetime()
        
        # Main Container
        main_container = tk.Frame(self.root, bg='#f0f0f0')
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Left Panel - Video Feed
        left_panel = tk.Frame(main_container, bg='white', relief='raised', bd=2)
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        video_header = tk.Label(
            left_panel, 
            text="Live Camera Feed", 
            font=("Arial", 16, "bold"),
            bg='white', 
            pady=10
        )
        video_header.pack()
        
        self.video_label = tk.Label(left_panel, bg='black')
        
        # Control Panel
        control_frame = tk.Frame(left_panel, bg='white')
        
        # Subject Selection
        subject_frame = tk.Frame(control_frame, bg='white')
        subject_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(
            subject_frame, 
            text="Subject:", 
            font=("Arial", 11, "bold"),
            bg='white'
        ).pack(side='left', padx=5)
        
        self.subject_dropdown = ttk.Combobox(
            subject_frame,
            textvariable=self.selected_subject,
            state='readonly',
            font=("Arial", 10),
            width=30
        )
        self.subject_dropdown.pack(side='left', padx=5, fill='x', expand=True)
        
        # Camera Selection
        camera_frame = tk.Frame(control_frame, bg='white')
        camera_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(
            camera_frame, 
            text="Camera:", 
            font=("Arial", 11, "bold"),
            bg='white'
        ).pack(side='left', padx=5)
        
        self.camera_dropdown = ttk.Combobox(
            camera_frame,
            textvariable=self.selected_camera,
            state='readonly',
            font=("Arial", 10),
            width=30
        )
        self.camera_dropdown.pack(side='left', padx=5, fill='x', expand=True)
        
        # Start/Stop Button
        button_frame = tk.Frame(control_frame, bg='white')
        button_frame.pack(fill='x')
        
        self.start_btn = tk.Button(
            button_frame,
            text="▶ Start Attendance System",
            command=self.toggle_system,
            bg='#4CAF50',
            fg='white',
            font=("Arial", 14, "bold"),
            relief='flat',
            pady=15,
            cursor='hand2'
        )
        self.start_btn.pack(fill='x', padx=5)
        
        # Statistics Frame
        stats_frame = tk.Frame(left_panel, bg='#f0f0f0', relief='solid', bd=1)
        stats_frame.pack(side='bottom', fill='x', padx=15, pady=10)
        
        control_frame.pack(side='bottom', fill='x', padx=15, pady=15)
        
        # Live Video Box (placed in remaining space)
        self.video_label.pack(fill='both', expand=True, padx=15, pady=10)
        
        self.stats_label = tk.Label(
            stats_frame,
            text="System Status: Stopped | Attendance Today: 0",
            font=("Arial", 10),
            bg='#f0f0f0',
            pady=8
        )
        self.stats_label.pack()
        
        # Right Panel - Attendance Log
        right_panel = tk.Frame(main_container, bg='white', relief='raised', bd=2, width=400)
        right_panel.pack(side='right', fill='y')
        right_panel.pack_propagate(False)
        
        log_header = tk.Label(
            right_panel,
            text="📋 Recent Attendance",
            font=("Arial", 16, "bold"),
            bg='white',
            pady=15
        )
        log_header.pack()
        
        # Scrollable log frame
        log_container = tk.Frame(right_panel, bg='white')
        log_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Canvas for scrolling
        canvas = tk.Canvas(log_container, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(log_container, orient='vertical', command=canvas.yview)
        
        self.log_frame = tk.Frame(canvas, bg='white')
        
        canvas.create_window((0, 0), window=self.log_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.log_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # Instructions
        instructions = tk.Label(
            right_panel,
            text="Look at the camera to mark attendance\n"
                 "Green = Success | Blue = Already Marked | Red = Unknown",
            font=("Arial", 9),
            bg='white',
            fg='#666',
            pady=10,
            justify='center'
        )
        instructions.pack(side='bottom')
        
    def update_datetime(self):
        """Update date/time display"""
        now = datetime.now().strftime("%A, %B %d, %Y | %I:%M:%S %p")
        self.datetime_label.config(text=now)
        self.root.after(1000, self.update_datetime)
        
    def load_data(self):
        """Load subjects and cameras"""
        try:
            # Load subjects
            self.subjects = self.db.get_all_subjects()
            if self.subjects:
                self.subject_dropdown['values'] = list(self.subjects.keys())
                self.subject_dropdown.current(0)
            else:
                messagebox.showwarning("Warning", "No subjects found in database")
            
            # Load cameras
            cameras = self.camera_manager.get_camera_list()
            if cameras:
                self.camera_dropdown['values'] = cameras
                self.camera_dropdown.current(0)
            else:
                messagebox.showerror("Error", "No cameras detected")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")
    
    def toggle_system(self):
        """Start or stop the attendance system"""
        if not self.is_camera_running:
            # Validate selections
            if not self.selected_subject.get():
                messagebox.showerror("Error", "Please select a subject")
                return
            
            camera_index = self.camera_dropdown.current()
            if camera_index < 0:
                messagebox.showerror("Error", "Please select a camera")
                return
            
            # Load face encodings
            try:
                encodings, prns = self.db.get_all_face_encodings()
                if not encodings:
                    messagebox.showwarning("Warning", "No registered students found")
                    return
                
                self.face_engine.load_known_faces(encodings, prns)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load face data: {e}")
                return
            
            # Start system
            self.is_camera_running = True
            self.start_btn.config(text="⏸ Stop System", bg='#F44336')
            self.stats_label.config(text="System Status: Running | Processing faces...")
            
            self.video_thread = threading.Thread(
                target=self.video_loop, 
                args=(camera_index,), 
                daemon=True
            )
            self.video_thread.start()
        else:
            # Stop system
            self.is_camera_running = False
            self.start_btn.config(text="▶ Start Attendance System", bg='#4CAF50')
            self.stats_label.config(text="System Status: Stopped")
    
    def video_loop(self, camera_index):
        """Main video processing loop"""
        cap = self.camera_manager.open_camera(camera_index)
        if not cap:
            messagebox.showerror("Error", "Failed to open camera")
            self.is_camera_running = False
            return
        
        frame_count = 0
        process_every_n_frames = 3  # Process every 3rd frame for performance
        
        while self.is_camera_running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            frame_count += 1
            
            # Enhance image quality
            frame = self.face_engine.enhance_image_quality(frame)
            
            # Process faces every N frames
            if frame_count % process_every_n_frames == 0:
                self.process_frame(frame)
            else:
                # Just display the frame
                self.display_frame(frame, [])
        
        cap.release()
    
    def process_frame(self, frame):
        """Process frame for face recognition"""
        # Detect and recognize faces
        face_locations, face_encodings = self.face_engine.detect_and_encode_face(frame)
        
        if not face_encodings:
            self.display_frame(frame, [])
            return
        
        # Recognize faces
        recognitions = self.face_engine.recognize_faces(face_encodings)
        
        # Process each recognition
        results = []
        for i, (prn, confidence) in enumerate(recognitions):
            face_location = face_locations[i]
            
            if prn:
                # Check cooldown
                current_time = time.time()
                already_marked = (prn in self.last_seen and 
                                (current_time - self.last_seen[prn]) < self.cooldown_period)
                
                if not already_marked:
                    # Log attendance
                    subject_id = self.subjects[self.selected_subject.get()]
                    if self.db.log_attendance(prn, subject_id):
                        self.last_seen[prn] = current_time
                        
                        # Get student name
                        student_name = self.db.get_student_name(prn)
                        
                        # Add to recent logs
                        self.add_to_log(student_name or prn, "Success", confidence)
                        
                        results.append((face_location, student_name or prn, 'success', confidence))
                    else:
                        results.append((face_location, prn, 'error', confidence))
                else:
                    # Already marked
                    student_name = self.db.get_student_name(prn)
                    results.append((face_location, f"{student_name or prn} (Already Marked)", 
                                  'already_marked', confidence))
            else:
                # Unknown face
                results.append((face_location, "Unknown", 'unknown', confidence))
        
        # Display frame with annotations
        self.display_frame(frame, results)
    
    def display_frame(self, frame, results):
        """Display frame with face annotations"""
        display_frame = frame.copy()
        
        for result in results:
            face_location, name, status, confidence = result
            top, right, bottom, left = face_location
            
            # Color coding
            if status == 'success':
                color = (0, 255, 0)  # Green
            elif status == 'already_marked':
                color = (255, 165, 0)  # Orange
            elif status == 'unknown':
                color = (0, 0, 255)  # Red
            else:
                color = (128, 128, 128)  # Gray
            
            # Draw rectangle
            cv2.rectangle(display_frame, (left, top), (right, bottom), color, 2)
            
            # Draw label background
            cv2.rectangle(display_frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            
            # Draw text
            text = f"{name} ({confidence:.1f}%)"
            cv2.putText(display_frame, text, (left + 6, bottom - 6),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Convert and display
        frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (800, 600))
        img = Image.fromarray(frame_resized)
        imgtk = ImageTk.PhotoImage(image=img)
        
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
    
    def add_to_log(self, name, status, confidence):
        """Add entry to attendance log"""
        timestamp = datetime.now().strftime("%I:%M:%S %p")
        
        # Create log entry frame
        entry_frame = tk.Frame(self.log_frame, bg='white', relief='solid', bd=1)
        entry_frame.pack(fill='x', pady=5, padx=5)
        
        # Status indicator
        if status == 'Success':
            indicator_color = '#4CAF50'
            status_symbol = '✓'
        else:
            indicator_color = '#F44336'
            status_symbol = '✗'
        
        indicator = tk.Label(
            entry_frame,
            text=status_symbol,
            font=("Arial", 16, "bold"),
            bg=indicator_color,
            fg='white',
            width=2
        )
        indicator.pack(side='left', fill='y')
        
        # Info frame
        info_frame = tk.Frame(entry_frame, bg='white')
        info_frame.pack(side='left', fill='both', expand=True, padx=10, pady=5)
        
        name_label = tk.Label(
            info_frame,
            text=name,
            font=("Arial", 11, "bold"),
            bg='white',
            anchor='w'
        )
        name_label.pack(anchor='w')
        
        details_label = tk.Label(
            info_frame,
            text=f"{timestamp} | Confidence: {confidence:.1f}%",
            font=("Arial", 9),
            bg='white',
            fg='#666',
            anchor='w'
        )
        details_label.pack(anchor='w')
        
        # Keep only last 10 entries
        self.recent_logs.append(entry_frame)
        if len(self.recent_logs) > 10:
            old_entry = self.recent_logs.popleft()
            old_entry.destroy()
    
    def on_close(self):
        """Handle window close"""
        self.is_camera_running = False
        if self.video_thread:
            self.video_thread.join(timeout=1)
        self.root.destroy()


# ===================================================================
# Run Attendance Kiosk
if __name__ == "__main__":
    from attendance_config import DB_CONFIG, FACE_RECOGNITION_CONFIG, CAMERA_CONFIG
    
    # Initialize managers (assuming these are already imported)
    from database_manager import DatabaseManager
    from face_recognition_engine import FaceRecognitionEngine
    from camera_manager import CameraManager
    
    db = DatabaseManager(DB_CONFIG)
    face_engine = FaceRecognitionEngine(FACE_RECOGNITION_CONFIG)
    camera_mgr = CameraManager(CAMERA_CONFIG)
    
    # Create and run application
    root = tk.Tk()
    app = AttendanceKiosk(root, db, face_engine, camera_mgr)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
    
    # Cleanup
    db.close()
