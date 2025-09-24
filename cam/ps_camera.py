#coding=utf-8
import sys
import os
import time
import mvsdk
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from ps_camera_modules.camera import CameraController
from ps_camera_modules.ui import PSCameraUI

# 젯슨 로컬 디스플레이 환경 설정 (SSH 접속 시)
os.environ['DISPLAY'] = ':0'

# 카메라 설정 정보
TARGET_CAMERA_IP = "192.168.0.100"

class App:
    def __init__(self):
        self.camera = CameraController(TARGET_CAMERA_IP)
        self.ui = PSCameraUI()
        
        # FPS 측정용
        self.frame_count = 0
        self.last_time = time.time()
        self.fps = 0
        
        self.setup_connections()
        self.setup_camera()
    
    def setup_connections(self):
        """UI 연결"""
        self.ui.info_button.clicked.connect(self.ui.toggle_info)
        self.ui.gain_slider.valueChanged.connect(self.on_gain_change)
        
        # 30fps 트리거 타이머 초기화
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.trigger_frame)
        self.fps_timer.start(33)  # 30fps (1000ms / 30 = 33.33ms)
    
    def setup_camera(self):
        """카메라 설정"""
        success, message = self.camera.setup_camera()
        if not success:
            self.ui.show_error(message)
            return
        
        # 콜백 함수 등록
        self.camera.set_frame_callback(self.on_new_frame)
        
        # 초기 UI 값 설정
        gain_value = self.camera.get_gain()
        self.ui.set_slider_values(gain_value)
        self.ui.update_gain_display(gain_value)
    
    def on_new_frame(self, q_image):
        """새 프레임 콜백 - 카메라가 새 프레임을 생성할 때마다 자동 호출"""
        self.ui.update_camera_frame(q_image)
        self.calculate_fps()
        
        # 자동 노출 모드 실시간 값 업데이트
        exposure_ms = self.camera.get_exposure_ms()
        self.camera.camera_info['exposure'] = int(exposure_ms)
        
        # FPS를 camera_info에 추가
        self.camera.camera_info['fps'] = self.fps
        self.ui.update_info_panel(self.camera.camera_info)
    
    def calculate_fps(self):
        """FPS 계산"""
        self.frame_count += 1
        current_time = time.time()
        
        # 1초마다 FPS 계산
        if current_time - self.last_time >= 1.0:
            self.fps = self.frame_count / (current_time - self.last_time)
            self.frame_count = 0
            self.last_time = current_time
    
    
    def on_gain_change(self, value):
        """게인 슬라이더 변경"""
        self.camera.set_gain(value)
        self.ui.update_gain_display(value)
    
    def trigger_frame(self):
        """30fps 트리거"""
        mvsdk.CameraSoftTrigger(self.camera.hCamera)
     
    def show(self):
        """UI 표시"""
        self.ui.show()
    
    def cleanup(self):
        """정리"""
        self.fps_timer.stop()
        self.camera.cleanup()

def main():
    app = QApplication(sys.argv)
    window = App()
    window.show()
    
    # 앱 종료 시 정리
    app.aboutToQuit.connect(window.cleanup)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
