#coding=utf-8
import sys
import os
import time
import mvsdk
import numpy as np
import cv2
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage
from ps_camera_modules.camera import CameraController
from ps_camera_modules.ui import PSCameraUI

# C++ 타이머 모듈 import
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
    import timer_module
    TIMER_AVAILABLE = True
    print("하드웨어 타이머 모듈 로드 완료")
except ImportError:
    TIMER_AVAILABLE = False
    print("하드웨어 타이머 모듈을 찾을 수 없습니다. Python 타이머를 사용합니다.")

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
        if TIMER_AVAILABLE:
            self.last_time = timer_module.get_hardware_timer()
        else:
            self.last_time = time.time() * 1000000
        self.fps = 0
        
        # 60fps 타이밍 제어용
        self.frame_duration_us = 16667  # 60fps = 16.67ms = 16667 마이크로초
        self.display_state = 'black'  # 'black' 또는 'camera'
        if TIMER_AVAILABLE:
            self.cycle_start_time = timer_module.get_hardware_timer()
        else:
            self.cycle_start_time = time.time() * 1000000
        self.last_captured_frame = None
        
        self.setup_connections()
        self.setup_camera()
    
    def setup_connections(self):
        """UI 연결"""
        self.ui.info_button.clicked.connect(self.ui.toggle_info)
        self.ui.gain_slider.valueChanged.connect(self.on_gain_change)
        
        # 60fps 디스플레이 타이머 초기화
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.update_display)
        self.display_timer.start(8)  # 8ms마다 체크 (60fps보다 빠르게)
    
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
        # 캡처된 프레임 저장
        self.last_captured_frame = q_image
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
        
        if TIMER_AVAILABLE:
            current_time = timer_module.get_hardware_timer()
            elapsed_ms = timer_module.get_timer_diff_ms(self.last_time, current_time)
            elapsed_us = elapsed_ms * 1000
        else:
            current_time = time.time() * 1000000
            elapsed_us = current_time - self.last_time
        
        # 1초마다 FPS 계산
        if elapsed_us >= 1000000:  # 1초 = 1,000,000 마이크로초
            self.fps = self.frame_count / (elapsed_us / 1000000.0)
            self.frame_count = 0
            self.last_time = current_time
    
    
    def on_gain_change(self, value):
        """게인 슬라이더 변경"""
        self.camera.set_gain(value)
        self.ui.update_gain_display(value)
    
    def update_display(self):
        """60fps 디스플레이 업데이트"""
        if TIMER_AVAILABLE:
            current_time = timer_module.get_hardware_timer()
            elapsed_ms = timer_module.get_timer_diff_ms(self.cycle_start_time, current_time)
            elapsed_us = elapsed_ms * 1000
        else:
            current_time = time.time() * 1000000
            elapsed_us = current_time - self.cycle_start_time
        
        if self.display_state == 'black':
            # 검은 화면 표시 중
            if elapsed_us >= self.frame_duration_us:
                # 한 프레임 시간이 지나면 카메라 화면으로 전환
                self.display_state = 'camera'
                self.cycle_start_time = current_time
                
                # 캡처된 프레임이 있으면 표시
                if self.last_captured_frame:
                    self.ui.update_camera_frame(self.last_captured_frame)
            else:
                # 검은 화면 표시 및 카메라 트리거
                self.show_black_screen()
                mvsdk.CameraSoftTrigger(self.camera.hCamera)
        
        elif self.display_state == 'camera':
            # 카메라 화면 표시 중
            if elapsed_us >= self.frame_duration_us:
                # 한 프레임 시간이 지나면 검은 화면으로 전환
                self.display_state = 'black'
                self.cycle_start_time = current_time
    
    def show_black_screen(self):
        """검은 화면 표시"""
        # 640x480 검은 이미지 생성
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # QImage로 변환
        height, width, channel = black_frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(black_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        self.ui.update_camera_frame(q_image)
     
    def show(self):
        """UI 표시"""
        self.ui.show()
    
    def cleanup(self):
        """정리"""
        self.display_timer.stop()
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
