import os
import sys
import threading
import subprocess
import tkinter as tk
from tkinter import messagebox
import argparse
from database_manager import DatabaseManager
from attendance_config import DB_CONFIG, FACE_RECOGNITION_CONFIG, CAMERA_CONFIG
from face_recognition_engine import FaceRecognitionEngine
from camera_manager import CameraManager
from registration_app import RegistrationApp
from attendance_kiosk import AttendanceKiosk
from classroom_attendance import ClassroomAttendanceApp


class DashboardApp:
    def __init__(self, api_executable: str | None = None):
        self.db = DatabaseManager(DB_CONFIG)
        self.face_engine = FaceRecognitionEngine(FACE_RECOGNITION_CONFIG)
        self.camera_mgr = CameraManager(CAMERA_CONFIG)
        self.api_process = None
        self.api_executable = api_executable

        self.root = tk.Tk()
        self.root.title("Attendance System Dashboard")
        self.root.geometry("600x360")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        tk.Label(self.root, text="Attendance System - Dashboard", font=("Arial", 16, "bold")).pack(pady=10)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        reg_btn = tk.Button(btn_frame, text="Open Registration App", width=25, command=self.open_registration)
        reg_btn.grid(row=0, column=0, padx=8, pady=8)

        kiosk_btn = tk.Button(btn_frame, text="Open Attendance Kiosk", width=25, command=self.open_kiosk)
        kiosk_btn.grid(row=0, column=1, padx=8, pady=8)

        api_btn = tk.Button(btn_frame, text="Start API Server", width=25, command=self.toggle_api)
        api_btn.grid(row=1, column=0, padx=8, pady=8)
        self.api_btn = api_btn

        class_btn = tk.Button(btn_frame, text="Open Classroom Session App", width=25, command=self.open_classroom_app)
        class_btn.grid(row=1, column=1, padx=8, pady=8)

        status_frame = tk.Frame(self.root)
        status_frame.pack(fill='x', pady=12, padx=12)

        self.api_status = tk.StringVar(value="API: stopped")
        tk.Label(status_frame, textvariable=self.api_status).pack(anchor='w')

        self.db_status = tk.StringVar(value="DB: connected")
        tk.Label(status_frame, textvariable=self.db_status).pack(anchor='w')

        cameras = self.camera_mgr.get_camera_list()
        tk.Label(status_frame, text=f"Cameras detected: {len(cameras)}").pack(anchor='w')

        footer = tk.Label(self.root, text="Use the buttons to open apps or start the API.")
        footer.pack(side='bottom', pady=8)

    def open_registration(self):
        top = tk.Toplevel(self.root)
        top.title("Registration")
        app = RegistrationApp(top, self.db, self.face_engine, self.camera_mgr)

    def open_kiosk(self):
        top = tk.Toplevel(self.root)
        top.title("Attendance Kiosk")
        app = AttendanceKiosk(top, self.db, self.face_engine, self.camera_mgr)

    def open_classroom_app(self):
        top = tk.Toplevel(self.root)
        top.title("Classroom Session Attendance")
        app = ClassroomAttendanceApp(top, self.db, self.face_engine, self.camera_mgr)

    def toggle_api(self):
        if self.api_process is None:
            self.start_api()
        else:
            self.stop_api()

    def start_api(self):
        # Start uvicorn as subprocess using the current Python interpreter
        try:
            # Determine executable: explicit override > venv python > sys.executable
            if self.api_executable:
                executable = self.api_executable
            else:
                venv_python = os.path.join(os.getcwd(), 'venv', 'bin', 'python')
                if os.path.isfile(venv_python) and os.access(venv_python, os.X_OK):
                    executable = venv_python
                else:
                    executable = sys.executable

            cmd = [executable, "-m", "uvicorn", "run_api:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]
            # Capture output so we can show useful errors if the process immediately fails
            self.api_process = subprocess.Popen(cmd, cwd=os.getcwd(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.api_status.set(f"API: running (pid={self.api_process.pid})")
            self.api_btn.config(text="Stop API Server")

            # Start a watcher thread to detect immediate failures and surface stderr
            def _watch_process(p):
                try:
                    # give process a moment to fail during startup
                    p.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    return
                # process exited quickly; fetch output
                out, err = p.communicate(timeout=1)
                msg = err.strip() or out.strip() or f"Process exited with code {p.returncode}"
                try:
                    messagebox.showerror("API Error", f"API process failed to start:\n{msg}")
                except Exception:
                    print("API Error:\n", msg)
                finally:
                    self.api_process = None
                    self.api_status.set("API: stopped")
                    self.api_btn.config(text="Start API Server")

            t = threading.Thread(target=_watch_process, args=(self.api_process,), daemon=True)
            t.start()
        except Exception as e:
            messagebox.showerror("API Error", f"Failed to start API server: {e}")
            self.api_process = None

    def stop_api(self):
        if self.api_process:
            try:
                self.api_process.terminate()
                self.api_process.wait(timeout=5)
            except Exception:
                try:
                    self.api_process.kill()
                except Exception:
                    pass
            self.api_process = None
        self.api_status.set("API: stopped")
        self.api_btn.config(text="Start API Server")

    def on_close(self):
        if messagebox.askokcancel("Quit", "Close dashboard and all running services?"):
            try:
                if self.api_process:
                    self.stop_api()
            except Exception:
                pass
            try:
                self.db.close()
            except Exception:
                pass
            self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(prog="run_dashboard.py")
    parser.add_argument("--api-python", help="Path to python executable to use for the API (overrides venv)")
    args = parser.parse_args()

    app = DashboardApp(api_executable=args.api_python)
    app.run()


if __name__ == '__main__':
    main()
