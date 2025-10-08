#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple UI Test - Using ps_camera.py style display
Even frames: Number display, Odd frames: Black screen
"""

import time
import sys
import os
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage
from ps_camera_modules.timer import VSyncFrameTimer
from _lib.wayland_utils import setup_wayland_environment

# Wayland environment setup - wayland_test.py style
wayland_display, xdg_runtime_dir = setup_wayland_environment()

if not wayland_display:
    print("❌ No available Wayland display found")
    sys.exit(1)

socket_path = os.path.join(xdg_runtime_dir, wayland_display)
if not os.path.exists(socket_path):
    print(f"❌ Wayland socket does not exist: {socket_path}")
    sys.exit(1)

# Set DISPLAY environment for Qt (from ps_camera.py memory)
os.environ['DISPLAY'] = ':0'


class SimpleUITest(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.frame_count = 0
        self.number_counter = 0
        self.running = True
        self.last_frame_time = None
        self.frame_interval_ms = 0
        
        # Screen size
        self.width = 640
        self.height = 480
        
        self.setup_ui()
        self.setup_vsync_timer()
        
        print("✓ Simple UI Test initialized")
    
    def setup_ui(self):
        """Setup UI similar to ps_camera.py style"""
        self.setWindowTitle("Simple UI Test")
        self.setFixedSize(660, 580)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Display area (like camera_label in ps_camera.py)
        self.display_label = QLabel("Starting...")
        self.display_label.setFixedSize(640, 480)
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setStyleSheet("border: 1px solid gray; background: black; color: white;")
        layout.addWidget(self.display_label)
        
        # Info panel (like ps_camera.py)
        self.info_widget = QWidget()
        info_layout = QVBoxLayout(self.info_widget)
        info_layout.setContentsMargins(5, 5, 5, 5)
        info_layout.setSpacing(2)
        
        self.info_labels = [QLabel() for _ in range(3)]
        for label in self.info_labels:
            label.setStyleSheet("color: white; font-size: 11px;")
            info_layout.addWidget(label)
        
        self.info_widget.setStyleSheet("background: rgba(40,40,40,200);")
        self.info_widget.setFixedSize(640, 60)
        layout.addWidget(self.info_widget)
        
        # Controls
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close_app)
        controls_layout.addWidget(self.close_button)
        
        layout.addWidget(controls)
    
    def setup_vsync_timer(self):
        """Setup VSync timer using timer.py"""
        try:
            # Hardware refresh rate detection
            self.vsync_timer = VSyncFrameTimer()
            self.hardware_fps = self._detect_hardware_refresh_rate()
            if not self.hardware_fps:
                print("❌ Hardware refresh rate detection failed - fallback to 60fps")
                self.hardware_fps = 60.0
            
            # Frame timing calculation
            self.frame_interval_ms = 1000.0 / self.hardware_fps
            print(f"🎯 Hardware refresh rate: {self.hardware_fps:.2f}Hz")
            print(f"🔄 Frame interval: {self.frame_interval_ms:.2f}ms")
            
            # VSync frame signal callback registration
            self.vsync_timer.add_frame_callback(self.on_frame_signal)
            
            # Start VSync synchronization
            self.vsync_timer.start()
            
            self.start_time = time.time()
            
        except Exception as e:
            print(f"❌ VSync timer setup failed: {e}")
            # Fallback to regular timer
            self.fallback_timer()
    
    def _detect_hardware_refresh_rate(self):
        """Hardware refresh rate detection"""
        try:
            temp_timer = VSyncFrameTimer()
            refresh_rate = temp_timer.get_hardware_refresh_rate()
            temp_timer.stop()
            return refresh_rate
        except Exception as e:
            print(f"⚠️ Refresh rate detection error: {e}")
            return None
    
    def fallback_timer(self):
        """Fallback to regular QTimer if VSync fails"""
        print("⚠️ Using fallback QTimer")
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self.update_frame)
        self.frame_timer.start(16)  # ~60 FPS
    
    def on_frame_signal(self, frame_number):
        """VSync frame signal callback (like ps_camera.py on_frame_signal)"""
        current_time = time.time()
        
        # Calculate frame interval
        if self.last_frame_time is not None:
            self.frame_interval_ms = (current_time - self.last_frame_time) * 1000
        
        self.frame_count += 1
        
        # Increment number every even frame (like ps_camera.py cycle logic)
        if self.frame_count % 2 == 0:
            self.number_counter += 1
        
        # Create frame image similar to ps_camera add_number_to_frame
        self.create_display_frame()
        
        # Update info panel
        self.update_info_panel()
        
        self.last_frame_time = current_time
        
        # Status output every 20 frames
        if self.frame_count % 20 == 0:
            print(f"Frame #{self.frame_count}: Number {self.number_counter}, {self.frame_interval_ms:.1f}ms (VSync)")
    
    def update_frame(self):
        """Fallback frame update for QTimer"""
        current_time = time.time()
        
        # Calculate frame interval
        if self.last_frame_time is not None:
            self.frame_interval_ms = (current_time - self.last_frame_time) * 1000
        
        self.frame_count += 1
        
        # Increment number every even frame
        if self.frame_count % 2 == 0:
            self.number_counter += 1
        
        # Create frame image similar to ps_camera add_number_to_frame
        self.create_display_frame()
        
        # Update info panel
        self.update_info_panel()
        
        self.last_frame_time = current_time
        
        # Status output every 20 frames
        if self.frame_count % 20 == 0:
            print(f"Frame #{self.frame_count}: Number {self.number_counter}, {self.frame_interval_ms:.1f}ms (Fallback)")
    
    def create_display_frame(self):
        """Create display frame similar to ps_camera.py style"""
        # Create frame based on frame count (even/odd)
        is_even_frame = (self.frame_count % 2) == 0
        
        if is_even_frame:
            # Even frame: White background with number
            frame = np.ones((self.height, self.width, 3), dtype=np.uint8) * 255
            
            # Add number text using OpenCV (like ps_camera.py)
            text = f"NUM: {self.number_counter}"
            cv2.putText(frame, text, (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
            
            # Add timing info
            time_text = f"TIME: {self.frame_interval_ms:.1f}ms"
            cv2.putText(frame, time_text, (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            
            # Add frame count
            frame_text = f"FRAME: {self.frame_count}"
            cv2.putText(frame, frame_text, (50, 350), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            
        else:
            # Odd frame: Black screen
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Convert to QImage and display (like ps_camera.py update_camera_frame)
        self.update_display_frame(frame)
    
    def update_display_frame(self, frame):
        """Update display frame similar to ps_camera.py update_camera_frame"""
        try:
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            
            # Ensure data is contiguous (like ps_camera.py)
            frame_contiguous = np.ascontiguousarray(frame)
            
            # Convert to QImage (similar to ps_camera.py grab_callback)
            q_image = QImage(frame_contiguous.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            
            if not q_image.isNull():
                pixmap = QPixmap.fromImage(q_image)
                # Update display label (like camera_label in ps_camera.py)
                self.display_label.setPixmap(pixmap)
                
        except Exception as e:
            print(f"Frame update error: {e}")
    
    def update_info_panel(self):
        """Update info panel similar to ps_camera.py"""
        texts = [
            f"Number: {self.number_counter}  Frame: {self.frame_count}",
            f"Interval: {self.frame_interval_ms:.2f}ms  FPS: {1000.0/self.frame_interval_ms:.1f}" if self.frame_interval_ms > 0 else "Interval: 0.0ms  FPS: 0.0",
            f"Status: {'Number Display' if self.frame_count % 2 == 0 else 'Black Screen'}"
        ]
        
        for i, text in enumerate(texts):
            self.info_labels[i].setText(text)
    
    def close_app(self):
        """Close application"""
        print("🔴 Close button clicked!")
        self.running = False
        
        # Stop timers
        if hasattr(self, 'vsync_timer'):
            self.vsync_timer.stop()
        if hasattr(self, 'frame_timer'):
            self.frame_timer.stop()
            
        self.close()
    
def main():
    print("🎯 Simple UI Test")
    print("=" * 50)
    
    app = QApplication(sys.argv)
    
    ui_test = SimpleUITest()
    ui_test.show()
    
    try:
        print("\n🚀 UI Test Started")
        print("Even frames: Number display, Odd frames: Black screen")
        print("Click Close button or close window to exit")
        
        return app.exec()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
