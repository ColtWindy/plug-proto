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
from ps_camera_modules.timer import Timer


# 젯슨 로컬 디스플레이 환경 설정 (SSH 접속 시)
os.environ['DISPLAY'] = ':0'

# 카메라 설정 정보
TARGET_CAMERA_IP = "192.168.0.100"

class App:
    def __init__(self):
        self.camera = CameraController(TARGET_CAMERA_IP)
        self.ui = PSCameraUI()
        self.timer = Timer()
        
        # FPS 측정용
        self.frame_count = 0
        self.last_time = self.timer.get_time()
        self.fps = 0
        
        # 디스플레이 타이밍 제어
        self.display_state = 'black'  # 'black' 또는 'camera'
        self.cycle_start_time = self.timer.get_time()
        self.last_captured_frame = None
        self.black_frame_counter = 0  # 검은 화면 카운터
        self.last_trigger_time = 0  # 마지막 트리거 시간
        self.black_screen_updated = False  # 검은 화면 업데이트 플래그
        self.camera_triggered = False  # 카메라 트리거 완료 플래그
        
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
        
        # 초기 UI 값 설정
        gain_value = self.camera.get_gain()
        self.ui.set_slider_values(gain_value)
        self.ui.update_gain_display(gain_value)
        
        # 하드웨어 타이머 기반 메인 루프 시작
        self.start_display_loop()
    
    def on_new_frame(self, q_image):
        """새 프레임 콜백 - 카메라가 새 프레임을 생성할 때마다 자동 호출"""
        # 캡처된 프레임에 숫자 추가
        self.last_captured_frame = self.add_number_to_frame(q_image)
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
        current_time = self.timer.get_time()
        elapsed_ms = self.timer.get_diff_ms(self.last_time, current_time)
        
        # 1초마다 FPS 계산
        if elapsed_ms >= 1000:  # 1초 = 1000ms
            self.fps = self.frame_count / (elapsed_ms / 1000.0)
            self.frame_count = 0
            self.last_time = current_time
    
    
    def on_gain_change(self, value):
        """게인 슬라이더 변경"""
        self.camera.set_gain(value)
        self.ui.update_gain_display(value)
    
    def start_display_loop(self):
        """하드웨어 타이머 기반 메인 디스플레이 루프"""
        import threading
        
        def display_loop():
            target_frame_ms = 16.67
            
            while True:
                current_time = self.timer.get_time()
                elapsed_ms = self.timer.get_diff_ms(self.cycle_start_time, current_time)
                
                if self.display_state == 'black':
                    # 검은 화면 시작 시 즉시 트리거
                    if not self.black_screen_updated:
                        self.black_frame_counter += 1
                        self.show_black_screen()
                        mvsdk.CameraSoftTrigger(self.camera.hCamera)
                        self.black_screen_updated = True
                    
                    # 16.67ms 후 카메라 화면으로 전환
                    if elapsed_ms >= target_frame_ms:
                        self.display_state = 'camera'
                        self.cycle_start_time = self.timer.get_time()
                        if self.last_captured_frame:
                            self.ui.update_camera_frame(self.last_captured_frame)
                
                elif self.display_state == 'camera':
                    # 16.67ms 후 검은 화면으로 전환
                    if elapsed_ms >= target_frame_ms:
                        self.display_state = 'black'
                        self.cycle_start_time = self.timer.get_time()
                        self.black_screen_updated = False
                
                # 매우 짧은 대기 (CPU 사용량 제어)
                time.sleep(0.0001)  # 0.1ms
        
        # 백그라운드 스레드에서 실행
        self.display_thread = threading.Thread(target=display_loop, daemon=True)
        self.display_thread.start()
    
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
