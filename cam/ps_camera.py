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

# VSync 타이밍 조정 상수 (실행 전 설정)
VSYNC_DELAY_MS = 1      # 화면 그리기 딜레이 보정 (1-10ms)
EXPOSURE_REDUCTION_MS = 10  # 노출시간 단축 (0-10ms)

class App:
    def __init__(self):
        self.camera = CameraController(TARGET_CAMERA_IP)
        self.ui = PSCameraUI()
        self.timer = VSyncFrameTimer(target_fps=30)
        
        # VSync 동기화 상태
        self.display_state = 'black'  # 'black' 또는 'camera'
        self.current_display_frame = None  # 현재 표시용 프레임 (고정)
        self.black_frame_counter = 0
        self.fps = 30.0
        
        # VSync 타이밍 설정 (상수값, 실행 중 변경 금지)
        self.vsync_delay_ms = VSYNC_DELAY_MS
        self.exposure_reduction_ms = EXPOSURE_REDUCTION_MS
        
        # 지연 처리용 QTimer (스레드 블로킹 방지)
        self.delay_timer = QTimer()
        self.delay_timer.setSingleShot(True)
        self.pending_action = None
        
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
        
        # VSync 설정 표시 (읽기 전용)
        self.ui.update_delay_display(self.vsync_delay_ms)
        self.ui.update_exposure_adj_display(self.exposure_reduction_ms)
        
        # 노출시간 초기 설정
        self._update_camera_exposure()
        
        # VSync 동기화 시작
        self.timer.start()
    
    def on_new_frame(self, q_image):
        """새 프레임 콜백 - 카메라가 새 프레임을 생성할 때마다 자동 호출"""
        # 캡처된 프레임 저장 (타이밍과 무관하게 언제든 사용 가능)
        processed_frame = self.add_number_to_frame(q_image)
        if processed_frame:
            self.current_display_frame = processed_frame
        
        # 자동 노출 모드 실시간 값 업데이트
        exposure_ms = self.camera.get_exposure_ms()
        self.camera.camera_info['exposure'] = int(exposure_ms)
        self.camera.camera_info['fps'] = self.fps
        self.ui.update_info_panel(self.camera.camera_info)
    
    def on_frame_signal(self, frame_number):
        """VSync 동기화 프레임 신호 콜백 (메인 스레드에서 안전 실행)"""
        # VSync 동기화 상태 전환 (30Hz 기준)
        # 4프레임 주기: 검은화면 2프레임 (0,1) + 카메라 2프레임 (2,3)
        cycle_position = frame_number % 4
        
        if cycle_position == 0:  # 첫 번째 검은화면 - 카메라 트리거
            self.black_frame_counter += 1
            if self.camera.hCamera:
                mvsdk.CameraSoftTrigger(self.camera.hCamera)
            self._schedule_delayed_action(self.show_black_screen)
            
        elif cycle_position == 1:  # 두 번째 검은화면
            self._schedule_delayed_action(self.show_black_screen)
            
        else:  # cycle_position == 2 or 3, 카메라 표시 2프레임
            # 저장된 프레임 표시 (노출시간과 무관)
            if self.current_display_frame:
                self._schedule_delayed_action(lambda: self.ui.update_camera_frame(self.current_display_frame))
            else:
                self._schedule_delayed_action(self.show_black_screen)  # 백업용
    
    
    def on_gain_change(self, value):
        """게인 슬라이더 변경"""
        self.camera.set_gain(value)
        self.ui.update_gain_display(value)
    
    def _update_camera_exposure(self):
        """노출시간 조정 (절대 시간 기준 단축)"""
        # 30fps 기준 최대 노출시간 (33.33ms = 33,333μs)
        base_max_exposure_us = int(1000000.0 / 30.0)
        
        # 절대 시간 단축 적용
        reduction_us = self.exposure_reduction_ms * 1000
        adjusted_max_exposure_us = max(100, base_max_exposure_us - reduction_us)
        
        # 카메라에 설정 적용
        self.camera.set_exposure_range(adjusted_max_exposure_us)
    
    def show_black_screen(self):
        """검은 화면 표시"""
        # 640x480 검은 이미지 생성
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # QImage로 변환
        height, width, channel = black_frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(black_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        self.ui.update_camera_frame(q_image)
    
    def _schedule_delayed_action(self, action):
        """VSync 딜레이를 비동기로 처리 (스레드 블로킹 방지)"""
        self.pending_action = action
        
        if self.vsync_delay_ms > 0:
            # QTimer로 비동기 지연 처리
            self.delay_timer.timeout.connect(self._execute_pending_action)
            self.delay_timer.start(self.vsync_delay_ms)
        else:
            # 지연 없이 즉시 실행
            self._execute_pending_action()
    
    def _execute_pending_action(self):
        """대기 중인 액션 실행"""
        # QTimer 연결 해제 (중복 실행 방지)
        self.delay_timer.timeout.disconnect()
        
        if self.pending_action:
            self.pending_action()
            self.pending_action = None
    
    def add_number_to_frame(self, q_image):
        """캡처된 프레임에 숫자 추가 (안전한 방식)"""
        try:
            # QImage 유효성 검사
            if q_image.isNull() or q_image.width() == 0 or q_image.height() == 0:
                return None
                
            # QImage를 numpy 배열로 변환
            width = q_image.width()
            height = q_image.height()
            ptr = q_image.bits()
            
            # 안전한 배열 변환
            if ptr is None:
                return q_image
                
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape(height, width, 3)
            frame = arr.copy()
            
            # 숫자 텍스트 추가
            text = str(self.black_frame_counter)
            cv2.putText(frame, text, (width//2-50, height//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 4, (255, 255, 255), 4)
            
            # 안전한 QImage 생성
            bytes_per_line = 3 * width
            return QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
        except Exception as e:
            print(f"프레임 처리 오류: {e}")
            return q_image  # 원본 반환
     
    def show(self):
        """UI 표시"""
        self.ui.show()
    
    def cleanup(self):
        """정리"""
        self.timer.stop()
        self.delay_timer.stop()  # 지연 타이머 정리
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
