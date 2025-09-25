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
from ps_camera_modules.timer import VSyncFrameTimer


# 젯슨 로컬 디스플레이 환경 설정 (SSH 접속 시)
os.environ['DISPLAY'] = ':0'

# 카메라 설정 정보
TARGET_CAMERA_IP = "192.168.0.100"

class App:
    def __init__(self):
        self.camera = CameraController(TARGET_CAMERA_IP)
        self.ui = PSCameraUI()
        self.timer = VSyncFrameTimer(target_fps=60)
        
        # VSync 동기화 상태
        self.display_state = 'black'  # 'black' 또는 'camera'
        self.last_captured_frame = None
        self.black_frame_counter = 0
        self.fps = 60.0
        
        self.setup_connections()
        self.setup_camera()
    
    def setup_connections(self):
        """UI 연결"""
        self.ui.info_button.clicked.connect(self.ui.toggle_info)
        self.ui.gain_slider.valueChanged.connect(self.on_gain_change)
    
    def setup_camera(self):
        """카메라 설정"""
        success, message = self.camera.setup_camera()
        if not success:
            self.ui.show_error(message)
            return
        
        # 콜백 함수 등록
        self.camera.set_frame_callback(self.on_new_frame)
        
        # VSync 프레임 신호 콜백 등록
        self.timer.add_frame_callback(self.on_frame_signal)
        
        # 초기 UI 값 설정
        gain_value = self.camera.get_gain()
        self.ui.set_slider_values(gain_value)
        self.ui.update_gain_display(gain_value)
        
        # VSync 동기화 시작
        self.timer.start()
    
    def on_new_frame(self, q_image):
        """새 프레임 콜백 - 카메라가 새 프레임을 생성할 때마다 자동 호출"""
        # 캡처된 프레임에 숫자 추가
        self.last_captured_frame = self.add_number_to_frame(q_image)
        
        # 자동 노출 모드 실시간 값 업데이트
        exposure_ms = self.camera.get_exposure_ms()
        self.camera.camera_info['exposure'] = int(exposure_ms)
        self.camera.camera_info['fps'] = self.fps
        self.ui.update_info_panel(self.camera.camera_info)
    
    def on_frame_signal(self, frame_number, timestamp):
        """VSync 동기화 프레임 신호 콜백"""
        if self.display_state == 'black':
            # 검은 화면 표시 및 카메라 트리거
            self.black_frame_counter += 1
            self.show_black_screen()
            mvsdk.CameraSoftTrigger(self.camera.hCamera)
            self.display_state = 'camera'
            
        elif self.display_state == 'camera':
            # 캡처된 프레임 표시
            if self.last_captured_frame:
                self.ui.update_camera_frame(self.last_captured_frame)
            self.display_state = 'black'
    
    
    def on_gain_change(self, value):
        """게인 슬라이더 변경"""
        self.camera.set_gain(value)
        self.ui.update_gain_display(value)
    
    def show_black_screen(self):
        """검은 화면 표시"""
        # 640x480 검은 이미지 생성
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # QImage로 변환
        height, width, channel = black_frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(black_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        self.ui.update_camera_frame(q_image)
    
    def add_number_to_frame(self, q_image):
        """캡처된 프레임에 숫자 추가"""
        # QImage를 numpy 배열로 변환
        width = q_image.width()
        height = q_image.height()
        ptr = q_image.bits()
        arr = np.array(ptr).reshape(height, width, 3)
        frame = arr.copy()
        
        # 중앙에 흰색 숫자 표시
        text = str(self.black_frame_counter)
        font_scale = 4
        thickness = 4
        
        # 텍스트 크기 계산
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        text_y = (frame.shape[0] + text_size[1]) // 2
        
        # 흰색 텍스트 그리기
        cv2.putText(frame, text, (text_x, text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)
        
        # 다시 QImage로 변환
        bytes_per_line = 3 * width
        return QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
     
    def show(self):
        """UI 표시"""
        self.ui.show()
    
    def cleanup(self):
        """정리"""
        self.timer.stop()
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
