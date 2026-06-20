# camera_manager.py
"""
Manages multiple camera sources with auto-detection, using threaded capture to prevent lag.
"""

import cv2
import threading
import time
import os
import sys

# Silence OpenCV logging warnings globally
os.environ["OPENCV_VIDEOIO_LOGGING_LEVEL"] = "0"
os.environ["OPENCV_LOG_LEVEL"] = "OFF"

class ThreadedCamera:
    """Wrapper around cv2.VideoCapture that grabs frames in a background thread to prevent latency/lag."""
    def __init__(self, cap):
        self.cap = cap
        self.ret = False
        self.frame = None
        self.is_running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        
    def _read_loop(self):
        while self.is_running:
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    self.ret = ret
                    self.frame = frame
                else:
                    time.sleep(0.01)
            else:
                time.sleep(0.01)
            time.sleep(0.005) # Prevent CPU throttling
            
    def read(self):
        return self.ret, self.frame
        
    def release(self):
        self.is_running = False
        time.sleep(0.05) # Allow read loop to finish
        self.cap.release()

class CameraManager:
    def __init__(self, config):
        self.config = config
        self.available_cameras = []
        self.detect_cameras()
        
    def detect_cameras(self):
        """Detect all available cameras using the optimal backend"""
        self.available_cameras = []
        
        # Test first 5 camera indices
        for i in range(5):
            if sys.platform == 'win32':
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(i)
                
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    
                    camera_info = {
                        'index': i,
                        'name': f"Camera {i}",
                        'resolution': f"{width}x{height}"
                    }
                    self.available_cameras.append(camera_info)
                cap.release()
        
        print(f"✓ Detected {len(self.available_cameras)} camera(s)")
        return self.available_cameras
    
    def open_camera(self, camera_index):
        """Open a camera with optimal settings and wrap it in ThreadedCamera to eliminate latency"""
        if sys.platform == 'win32':
            cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(camera_index)
            
        if not cap.isOpened():
            return None
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config['frame_width'])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config['frame_height'])
        cap.set(cv2.CAP_PROP_FPS, self.config['fps'])
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
        
        return ThreadedCamera(cap)
    
    def get_camera_list(self):
        """Get list of camera names for UI dropdown"""
        return [f"{cam['name']} ({cam['resolution']})" 
                for cam in self.available_cameras]
