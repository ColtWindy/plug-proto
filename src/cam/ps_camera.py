#coding=utf-8
import sys
import os
import time
import numpy as np
import cv2
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage
from ps_camera_modules.camera import CameraController
from ps_camera_modules.ui import PSCameraUI
from ps_camera_modules.timer import VSyncFrameTimer
from util import measure_time
from _lib import mvsdk

# 프로젝트 루트 경로 추가 (config import를 위해)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config import CAMERA_IP

# Jetson 디스플레이 환경 설정
# OpenGL 대신 QPainter 사용으로 변경

# 젯슨 Wayland 디스플레이 환경 설정 (SSH 접속 시)
def setup_wayland_environment():
    """Wayland 환경 설정"""
    xdg_runtime_dir = os.getenv('XDG_RUNTIME_DIR')
    if not xdg_runtime_dir:
        user_id = os.getuid() if hasattr(os, 'getuid') else 1000
        xdg_runtime_dir = f"/run/user/{user_id}"
        os.environ['XDG_RUNTIME_DIR'] = xdg_runtime_dir
    
    wayland_display = os.getenv('WAYLAND_DISPLAY')
    if not wayland_display:
        possible_displays = ['wayland-0', 'wayland-1', 'weston-wayland-0', 'weston-wayland-1']
        
        for display_name in possible_displays:
            socket_path = os.path.join(xdg_runtime_dir, display_name)
            if os.path.exists(socket_path):
                os.environ['WAYLAND_DISPLAY'] = display_name
                wayland_display = display_name
                break
    
    return wayland_display, xdg_runtime_dir

# Wayland 환경 설정 - wayland_test.py 방식
wayland_display, xdg_runtime_dir = setup_wayland_environment()

if not wayland_display:
    print("❌ 사용 가능한 Wayland 디스플레이를 찾을 수 없습니다")
    sys.exit(1)
else:
    # wayland_display: wayland-0
    print(f"Wayland 디스플레이를 찾았습니다: {wayland_display}")

socket_path = os.path.join(xdg_runtime_dir, wayland_display)
if not os.path.exists(socket_path):
    print(f"❌ Wayland 소켓이 존재하지 않습니다: {socket_path}")
    sys.exit(1)
else:
    # socket_path: /run/user/1000/wayland-0
    print(f"Wayland 소켓이 존재합니다: {socket_path}")

# VSync 타이밍 조정 상수 (실행 전 설정)
EXPOSURE_TIME_MS = 10   # 노출시간 직접 설정 (5-30ms)
VSYNC_DELAY_MS = -15    # 화면 그리기 딜레이 보정 (-50~+50ms)

class App:
    def __init__(self):
        self.camera = CameraController(CAMERA_IP)
        self.ui = PSCameraUI()
        # 하드웨어 주사율 감지
        self.hardware_fps = self._detect_hardware_refresh_rate()
        if not self.hardware_fps:
            print("❌ 하드웨어 주사율 감지 실패 - 종료")
            sys.exit(1)
        
        # 타이밍 계산
        self.frame_interval_ms = 1000.0 / self.hardware_fps
        self.cycle_length = 2  # 2프레임 주기
        self.cycle_duration_ms = self.frame_interval_ms * self.cycle_length
        
        print(f"🎯 하드웨어 주사율: {self.hardware_fps:.2f}Hz")
        print(f"🔄 2프레임 주기: {self.cycle_duration_ms:.2f}ms")
        
        self.timer = VSyncFrameTimer()  # Wayland VSync 동기화
        
        # VSync 동기화 상태
        self.display_state = 'black'
        self.current_display_frame = None
        self.last_valid_frame = None  # 마지막 유효 프레임 백업
        self.black_frame_counter = 0
        
        # VSync 타이밍 설정
        self.vsync_delay_ms = VSYNC_DELAY_MS
        self.exposure_time_ms = EXPOSURE_TIME_MS
        
        # 지연 처리용 QTimer (스레드 블로킹 방지)
        self.delay_timer = QTimer()
        self.delay_timer.setSingleShot(True)
        self.pending_action = None
        
        # 카메라 선행 트리거용 QTimer
        self.camera_timer = QTimer()
        self.camera_timer.setSingleShot(True)
        
        
        self.setup_connections()
        self.setup_camera()
    
    def setup_connections(self):
        """UI 연결"""
        self.ui.info_button.clicked.connect(self.ui.toggle_info)
        self.ui.gain_slider.valueChanged.connect(self.on_gain_change)
        self.ui.exposure_slider.valueChanged.connect(self.on_exposure_change)
        self.ui.delay_slider.valueChanged.connect(self.on_delay_change)
    
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
        self.ui.set_slider_values(gain_value, self.exposure_time_ms, self.vsync_delay_ms)
        self.ui.update_gain_display(gain_value)
        self.ui.update_exposure_display(self.exposure_time_ms)
        self.ui.update_delay_display(self.vsync_delay_ms)
        
        # 노출시간 초기 설정
        self._update_camera_exposure()
        
        # VSync 동기화 시작
        self.timer.start()
    
    def on_new_frame(self, q_image):
        """새 프레임 콜백 - 카메라가 새 프레임을 생성할 때마다 자동 호출"""
        # 캡처된 프레임 저장 (VSync와 독립적으로 저장만)
        processed_frame = self.add_number_to_frame(q_image)
        if processed_frame:
            self.current_display_frame = processed_frame
            self.last_valid_frame = processed_frame  # 백업 저장
        
        # 자동 노출 모드 실시간 값 업데이트
        exposure_ms = self.camera.get_exposure_ms()
        self.camera.camera_info['exposure'] = int(exposure_ms)
        self.camera.camera_info['fps'] = self.hardware_fps
        self.ui.update_info_panel(self.camera.camera_info)
    
    def on_frame_signal(self, frame_number):
        """VSync 동기화 프레임 신호 콜백 (메인 스레드에서 안전 실행)"""
        cycle_position = frame_number % 2
        
        # 음수 딜레이: 카메라 트리거를 먼저 보냄
        if self.vsync_delay_ms < 0 and cycle_position == 1:
            if self.camera.hCamera:
                self._schedule_camera_trigger(abs(self.vsync_delay_ms))
        
        if cycle_position == 0:  # 검은화면 + 카메라 트리거
            self.display_state = 'black'
            self.black_frame_counter += 1
            # 양수/0 딜레이에서만 트리거 
            if self.vsync_delay_ms >= 0 and self.camera.hCamera:
                mvsdk.CameraSoftTrigger(self.camera.hCamera)
            self._schedule_delayed_action(self.show_black_screen)
            
        else:  # cycle_position == 1, 카메라 표시
            self.display_state = 'camera'
            if self.current_display_frame:
                frame_to_show = self.current_display_frame
                self.current_display_frame = None  # 사용 후 클리어
                self._schedule_delayed_action(lambda: self.ui.update_camera_frame(frame_to_show))
            elif self.last_valid_frame:
                # 새 프레임이 없으면 마지막 유효 프레임 재사용
                self._schedule_delayed_action(lambda: self.ui.update_camera_frame(self.last_valid_frame))
            else:
                # 백업도 없으면 검은화면
                self._schedule_delayed_action(self.show_black_screen)
    
    
    def on_gain_change(self, value):
        """게인 슬라이더 변경"""
        self.camera.set_gain(value)
        self.ui.update_gain_display(value)
    
    def on_exposure_change(self, value):
        """노출시간 슬라이더 변경"""
        self.exposure_time_ms = value
        self._update_camera_exposure()
        self.ui.update_exposure_display(value)
    
    def on_delay_change(self, value):
        """딜레이 슬라이더 변경"""
        self.vsync_delay_ms = value
        self.ui.update_delay_display(value)
    
    def _detect_hardware_refresh_rate(self):
        """하드웨어에서 주사율 직접 가져오기"""
        temp_timer = VSyncFrameTimer()
        refresh_rate = temp_timer.get_hardware_refresh_rate()
        temp_timer.stop()
        return refresh_rate
    
    def _update_camera_exposure(self):
        """노출시간 직접 설정"""
        exposure_us = self.exposure_time_ms * 1000
        self.camera.set_exposure_range(exposure_us)
        print(f"📸 노출시간: {self.exposure_time_ms}ms = {exposure_us}μs")
    
    def show_black_screen(self):
        """검은 화면 표시"""
        # QPainter 위젯에 None 전달하면 자동으로 검은 화면 표시
        self.ui.update_camera_frame(None)
    
    def _schedule_delayed_action(self, action):
        """VSync 딜레이를 비동기로 처리 (스레드 블로킹 방지)"""
        # 기존 연결 안전하게 해제
        if self.delay_timer.isActive():
            self.delay_timer.stop()
        
        # 특정 시그널만 연결 해제
        try:
            self.delay_timer.timeout.disconnect(self._execute_pending_action)
        except:
            pass  # 연결되지 않은 경우 무시
            
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
        # QTimer 안전하게 정리
        if self.delay_timer.isActive():
            self.delay_timer.stop()
        
        # 특정 시그널만 연결 해제
        try:
            self.delay_timer.timeout.disconnect(self._execute_pending_action)
        except:
            pass  # 연결되지 않은 경우 무시
        
        if self.pending_action:
            self.pending_action()
            self.pending_action = None
    
    def _schedule_camera_trigger(self, delay_ms):
        """카메라 트리거 선행 실행"""
        if self.camera_timer.isActive():
            self.camera_timer.stop()
        
        # 특정 시그널만 연결 해제
        try:
            self.camera_timer.timeout.disconnect(self._execute_camera_trigger)
        except:
            pass  # 연결되지 않은 경우 무시
            
        self.camera_timer.timeout.connect(self._execute_camera_trigger)
        self.camera_timer.start(delay_ms)
    
    def _execute_camera_trigger(self):
        """카메라 트리거 실행"""
        if self.camera_timer.isActive():
            self.camera_timer.stop()
        
        # 특정 시그널만 연결 해제
        try:
            self.camera_timer.timeout.disconnect(self._execute_camera_trigger)
        except:
            pass  # 연결되지 않은 경우 무시
            
        if self.camera.hCamera:
            mvsdk.CameraSoftTrigger(self.camera.hCamera)
    
    def add_number_to_frame(self, q_image):
        """캡처된 프레임에 숫자 추가 (안전한 방식)"""
        try:
            # QImage 유효성 검사
            if not q_image or q_image.isNull() or q_image.width() == 0 or q_image.height() == 0:
                return None
                
            # QImage를 numpy 배열로 변환
            width = q_image.width()
            height = q_image.height()
            ptr = q_image.bits()
            
            # 안전한 배열 변환
            if ptr is None:
                return q_image
            
            # 예상 크기 검증
            expected_size = width * height * 3
            buffer_size = len(ptr)
            if buffer_size != expected_size:
                print(f"⚠️ 버퍼 크기 불일치: {buffer_size} != {expected_size}")
                return q_image
                
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape(height, width, 3)
            frame = arr.copy()
            
            # 숫자 텍스트 추가 (크기 검증 후)
            if width >= 100 and height >= 50:
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
        self.delay_timer.stop()
        self.camera_timer.stop()
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
