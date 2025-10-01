#coding=utf-8
"""
QOpenGLWindow 기반 카메라 애플리케이션
frameSwapped 콜백을 사용하여 프레임 드랍 방지
"""
import sys
import os
import time
import threading

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication, QMainWindow, QToolBar, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSizePolicy
from PySide6.QtOpenGL import QOpenGLWindow
from PySide6.QtGui import QSurfaceFormat, QPainter, QFont, QColor, QPen, QPixmap, QImage
from PySide6.QtCore import Qt, QTimer, QElapsedTimer, QDateTime
from OpenGL import GL
from camera_controller import OpenGLCameraController
from cam import mvsdk


class FrameMonitor:
    """프레임 드랍/스킵 정밀 검출"""
    
    def __init__(self, window, expected_hz=60.0):
        self.win = window
        screen = self.win.screen() if hasattr(self.win, "screen") else None
        hz = screen.refreshRate() if screen and screen.refreshRate() > 1.0 else expected_hz
        self.target_ms = 1000.0 / hz
        
        self.swap_timer = QElapsedTimer()
        self.cpu_timer = QElapsedTimer()
        self.last_swap_ms = None
        self.frame_idx = 0
        self.last_fence = None
        self.drop_count = 0
        
        # frameSwapped 연결
        if hasattr(self.win, "frameSwapped"):
            self.win.frameSwapped.connect(self._on_swap)
        
        self.swap_timer.start()
    
    def begin_frame(self):
        """paintGL 시작 직전"""
        self.cpu_timer.start()
        
        # GPU 백로그 검사
        if self.last_fence:
            status = GL.glClientWaitSync(self.last_fence, 0, 0)
            if status == GL.GL_TIMEOUT_EXPIRED:
                self._log("GPU", "GPU backlog - 이전 프레임 미완료")
            GL.glDeleteSync(self.last_fence)
            self.last_fence = None
    
    def end_frame(self):
        """paintGL 끝 직후"""
        self.last_fence = GL.glFenceSync(GL.GL_SYNC_GPU_COMMANDS_COMPLETE, 0)
        
        cpu_ms = self.cpu_timer.elapsed()
        if cpu_ms > 0.8 * self.target_ms:
            self._log("CPU", f"느린 렌더링: {cpu_ms:.2f}ms (예산: {self.target_ms:.2f}ms)")
    
    def _on_swap(self):
        """frameSwapped 시 호출"""
        now_ms = self.swap_timer.elapsed()
        if self.last_swap_ms is not None:
            delta = now_ms - self.last_swap_ms
            missed = int(round(delta / self.target_ms)) - 1
            if missed > 0:
                self.drop_count += 1
                self._log("DROP", f"프레임 스킵 {missed}개 - 간격: {delta:.2f}ms (목표: {self.target_ms:.2f}ms)")
        self.last_swap_ms = now_ms
        self.frame_idx += 1
    
    def _log(self, level, msg):
        ts = QDateTime.currentDateTime().toString("hh:mm:ss.zzz")
        print(f"[{ts}] [{level}] {msg}")


def setup_wayland_environment():
    """Wayland 환경 설정 (SSH 접속 시 필수)"""
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


class CameraOpenGLWindow(QOpenGLWindow):
    """카메라 화면을 표시하는 OpenGL 윈도우 (VSync 동기화)"""
    
    def __init__(self, parent_window=None):
        super().__init__()
        self.setTitle("OpenGL Camera - VSync")
        self.current_pixmap = None
        self.pending_pixmap = None
        self._frame = 0
        self.display_number = 0
        self.parent_window = parent_window
        
        # 스케일 캐시 (성능 최적화)
        self._scaled_cache = None
        self._cache_key = None  # (pixmap.cacheKey(), w, h)
        
        # 텍스트 렌더링 캐시
        self._info_font = QFont("Monospace", 12)
        self._info_pen = QPen(QColor(0, 255, 0))
        
        # 프레임 모니터 (정밀 드랍 검출)
        self.monitor = FrameMonitor(self, expected_hz=60.0)
        self._stress_test = False
        
        # frameSwapped 시그널을 사용하여 vsync 기반 프레임 업데이트
        self.frameSwapped.connect(self.on_frame_swapped, Qt.QueuedConnection)

    def initializeGL(self):
        """OpenGL 초기화"""
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glDisable(GL.GL_DEPTH_TEST)  # 깊이 테스트 비활성화
    
    def resizeGL(self, w, h):
        """윈도우 크기 변경 처리"""
        GL.glViewport(0, 0, w, h)

    def paintGL(self):
        """
        프레임 렌더링
        frameSwapped 시그널에 의해 vsync와 동기화되어 호출됨
        짝수 프레임: 검은 화면, 홀수 프레임: 카메라 화면
        """
        self.monitor.begin_frame()  # 모니터링 시작
        
        self._frame += 1
        cycle_position = self._frame % 2
        
        # 배경 클리어 (깊이 버퍼 제거)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        
        w = self.width()
        h = self.height()
        
        if cycle_position == 0:
            # 짝수 프레임: 검은 화면 (OpenGL 클리어만 사용, QPainter 생략)
            # 텍스트만 표시
            painter = QPainter(self)
            painter.setFont(self._info_font)
            painter.setPen(self._info_pen)
            info_text = f"Frame: {self._frame} | Num: {self.display_number} | 검은화면 | Drop: {self.monitor.drop_count}"
            painter.drawText(10, 25, info_text)
            painter.end()
            
        else:
            # 홀수 프레임: 카메라 화면
            self.display_number += 1
            
            # 대기 중인 픽셀맵이 있으면 교체
            if self.pending_pixmap is not None:
                self.current_pixmap = self.pending_pixmap
                self.pending_pixmap = None
                # 캐시 무효화
                self._cache_key = None
            
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
            
            # 카메라 이미지 표시
            if self.current_pixmap and not self.current_pixmap.isNull():
                # 스케일 캐시: 창 크기나 이미지가 바뀔 때만 스케일
                key = (self.current_pixmap.cacheKey(), w, h)
                if key != self._cache_key:
                    self._scaled_cache = self.current_pixmap.scaled(
                        w, h, 
                        Qt.KeepAspectRatio, 
                        Qt.FastTransformation  # 빠른 변환
                    )
                    self._cache_key = key
                
                # 캐시된 스케일 이미지 사용
                x = (w - self._scaled_cache.width()) // 2
                y = (h - self._scaled_cache.height()) // 2
                painter.drawPixmap(x, y, self._scaled_cache)
            
                # 부하 테스트: 의도적 지연
                if self._stress_test:
                    time.sleep(0.030)  # 30ms 지연
            
            # 프레임 정보 표시
            painter.setFont(self._info_font)
            painter.setPen(self._info_pen)
            info_text = f"Frame: {self._frame} | Num: {self.display_number} | 카메라화면 | Drop: {self.monitor.drop_count}"
            painter.drawText(10, 25, info_text)
            
            painter.end()
        
        self.monitor.end_frame()  # 모니터링 종료

    def update_camera_frame(self, q_image):
        """카메라 프레임 업데이트 (메인 스레드에서 안전)"""
        if q_image is None or q_image.isNull():
            self.pending_pixmap = None
        else:
            self.pending_pixmap = QPixmap.fromImage(q_image)
    
    def on_frame_swapped(self):
        """frameSwapped 시그널 처리 - VSync 타이밍에서 카메라 트리거"""
        # 메인 윈도우에 VSync 프레임 신호 전달 (렌더링 전)
        cycle_position = self._frame % 2
        if self.parent_window:
            self.parent_window.on_vsync_frame(cycle_position)
        
        # 다음 프레임 업데이트
        self.update()
    
    def keyPressEvent(self, event):
        """ESC 키로 종료"""
        if event.key() == Qt.Key_Escape or event.key() == Qt.Key_Q:
            self.close()


class MainWindow(QMainWindow):
    """OpenGL 카메라 메인 윈도우"""
    
    def __init__(self, camera_ip="192.168.0.100"):
        super().__init__()
        self.camera_ip = camera_ip
        self.camera = None
        self.exposure_time_ms = 9
        self.vsync_delay_ms = 17  # VSync 딜레이 (셔터 타이밍 조정)
        
        self.setWindowTitle("OpenGL Camera - No Frame Drop")
        
        # OpenGL 윈도우 생성
        self.opengl_window = CameraOpenGLWindow(parent_window=self)
        
        # QOpenGLWindow를 QWidget 컨테이너로 변환
        container = QWidget.createWindowContainer(self.opengl_window, self)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 메인 레이아웃
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(container, stretch=1)  # stretch로 공간 채우기
        
        # 컨트롤 패널
        self.setup_controls(main_layout)
        
        # 윈도우 크기 설정 (리사이즈 가능)
        self.resize(1024, 768)
        
        # 카메라 초기화
        self.setup_camera()

    def setup_controls(self, parent_layout):
        """컨트롤 패널 설정"""
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls.setMaximumHeight(100)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # 부하 테스트 버튼
        self.stress_btn = QPushButton("부하 테스트 OFF")
        self.stress_btn.clicked.connect(self.toggle_stress_test)
        self.stress_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        button_layout.addWidget(self.stress_btn)
        
        # 종료 버튼
        quit_btn = QPushButton("종료 (Q)")
        quit_btn.clicked.connect(self.close)
        quit_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        button_layout.addWidget(quit_btn)
        button_layout.addStretch()
        controls_layout.addLayout(button_layout)
        
        # 게인 슬라이더
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("Gain:"))
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setRange(0, 100)
        self.gain_slider.valueChanged.connect(self.on_gain_change)
        gain_layout.addWidget(self.gain_slider)
        self.gain_label = QLabel("0")
        gain_layout.addWidget(self.gain_label)
        controls_layout.addLayout(gain_layout)
        
        # 노출시간 슬라이더
        exposure_layout = QHBoxLayout()
        exposure_layout.addWidget(QLabel("노출시간:"))
        self.exposure_slider = QSlider(Qt.Horizontal)
        self.exposure_slider.setRange(1, 30)
        self.exposure_slider.setValue(self.exposure_time_ms)
        self.exposure_slider.valueChanged.connect(self.on_exposure_change)
        exposure_layout.addWidget(self.exposure_slider)
        self.exposure_label = QLabel(f"{self.exposure_time_ms}ms")
        exposure_layout.addWidget(self.exposure_label)
        controls_layout.addLayout(exposure_layout)
        
        # VSync 딜레이 슬라이더 (셔터 타이밍 조정)
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("셔터 딜레이:"))
        self.delay_slider = QSlider(Qt.Horizontal)
        self.delay_slider.setRange(0, 50)
        self.delay_slider.setValue(self.vsync_delay_ms)
        self.delay_slider.valueChanged.connect(self.on_delay_change)
        delay_layout.addWidget(self.delay_slider)
        self.delay_label = QLabel(f"{self.vsync_delay_ms}ms")
        delay_layout.addWidget(self.delay_label)
        controls_layout.addLayout(delay_layout)
        
        parent_layout.addWidget(controls)

    def setup_camera(self):
        """카메라 설정"""
        self.camera = OpenGLCameraController(self.camera_ip)
        success, message = self.camera.setup_camera()
        
        if not success:
            print(f"❌ 카메라 초기화 실패: {message}")
            return
        
        # 카메라 프레임 콜백 등록
        self.camera.set_frame_callback(self.on_new_camera_frame)
        
        # 초기 설정
        gain_value = self.camera.get_gain()
        self.gain_slider.setValue(int(gain_value))
        self.gain_label.setText(str(int(gain_value)))
        
        # 노출시간 설정
        exposure_us = self.exposure_time_ms * 1000
        self.camera.set_exposure_time(exposure_us)
        
        # 트리거 모드 설정
        if self.camera.hCamera:
            mvsdk.CameraSetTriggerMode(self.camera.hCamera, 1)  # 수동 트리거 모드
            # 초기 트리거 발생 (첫 프레임 캡처 시작)
            mvsdk.CameraSoftTrigger(self.camera.hCamera)
        
        print(f"✅ 카메라 연결 성공: {self.camera.camera_info['name']}")
        print(f"🎬 초기 셔터 트리거 발생")

    def on_new_camera_frame(self, q_image):
        """카메라에서 새 프레임이 도착했을 때"""
        if q_image and not q_image.isNull():
            # OpenGL 윈도우에 프레임 전달
            self.opengl_window.update_camera_frame(q_image)

    def on_gain_change(self, value):
        """게인 슬라이더 변경"""
        if self.camera:
            self.camera.set_gain(value)
        self.gain_label.setText(str(int(value)))

    def on_exposure_change(self, value):
        """노출시간 슬라이더 변경"""
        self.exposure_time_ms = value
        if self.camera:
            exposure_us = self.exposure_time_ms * 1000
            self.camera.set_exposure_time(exposure_us)
        self.exposure_label.setText(f"{value}ms")
    
    def on_delay_change(self, value):
        """VSync 딜레이 슬라이더 변경"""
        self.vsync_delay_ms = value
        self.delay_label.setText(f"{value}ms")
    
    def toggle_stress_test(self):
        """부하 테스트 토글"""
        self.opengl_window._stress_test = not self.opengl_window._stress_test
        status = "ON" if self.opengl_window._stress_test else "OFF"
        self.stress_btn.setText(f"부하 테스트 {status}")
        print(f"{'🔥 부하 테스트 활성화 (30ms 지연)' if self.opengl_window._stress_test else '✅ 부하 테스트 비활성화'}")
    
    def on_vsync_frame(self, cycle_position):
        """VSync 프레임 신호 처리 - 고정밀 타이밍"""
        if not self.camera or not self.camera.hCamera:
            return
        
        if cycle_position == 0:
            # 짝수 프레임: 검은 화면 표시 시점에 카메라 트리거
            threading.Thread(
                target=self._precise_delay_trigger,
                args=(self.vsync_delay_ms,),
                daemon=True
            ).start()
    
    def _precise_delay_trigger(self, delay_ms):
        """
        고정밀 딜레이 후 카메라 트리거
        busy-wait 방식으로 마이크로초 수준의 정확도 보장
        """
        if delay_ms > 0:
            start_time = time.perf_counter()
            target_time = start_time + (delay_ms / 1000.0)
            
            # busy-wait: 1ms 전까지는 sleep
            while time.perf_counter() < target_time - 0.001:
                time.sleep(0.0001)  # 100 마이크로초 sleep
            
            # 마지막 1ms는 busy-wait으로 정확도 보장
            while time.perf_counter() < target_time:
                pass
        
        # 정확한 시점에 트리거
        if self.camera and self.camera.hCamera:
            mvsdk.CameraSoftTrigger(self.camera.hCamera)

    def keyPressEvent(self, event):
        """ESC 또는 Q 키로 종료"""
        if event.key() == Qt.Key_Escape or event.key() == Qt.Key_Q:
            self.close()

    def closeEvent(self, event):
        """윈도우 종료 시 정리"""
        if self.camera:
            self.camera.cleanup()
        event.accept()


def main():
    """애플리케이션 진입점"""
    # Wayland 환경 설정 (SSH 접속 시)
    wayland_display, xdg_runtime_dir = setup_wayland_environment()
    
    if not wayland_display:
        print("❌ 사용 가능한 Wayland 디스플레이를 찾을 수 없습니다")
        print("💡 DISPLAY=:0 환경변수를 설정하거나 X11 디스플레이를 확인하세요")
        sys.exit(1)
    
    socket_path = os.path.join(xdg_runtime_dir, wayland_display)
    if not os.path.exists(socket_path):
        print(f"❌ Wayland 소켓이 존재하지 않습니다: {socket_path}")
        sys.exit(1)
    
    print(f"✅ Wayland 디스플레이: {wayland_display}")
    print(f"✅ Wayland 소켓: {socket_path}")
    
    # Wayland EGL 플랫폼 설정 (Jetson 공식 지원)
    os.environ['QT_QPA_PLATFORM'] = 'wayland-egl'
    
    # OpenGL ES + VSync 설정 (Wayland + EGL)
    # Jetson은 OpenGL ES 3.2 + EGL + Wayland를 공식 지원
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.OpenGLES)    # EGL 사용 (GLX 대신)
    fmt.setVersion(3, 2)                              # OpenGL ES 3.2
    fmt.setSwapInterval(1)                            # vsync 활성화
    fmt.setSwapBehavior(QSurfaceFormat.DoubleBuffer)  # Double Buffer
    fmt.setDepthBufferSize(0)                         # 깊이 버퍼 비활성화 (성능 최적화)
    QSurfaceFormat.setDefaultFormat(fmt)
    
    print(f"🎨 OpenGL ES 3.2 + EGL + Wayland + VSync 설정 완료")
    print(f"📌 QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM')}")
    
    app = QApplication(sys.argv)
    
    # 카메라 IP 설정 (필요시 변경)
    camera_ip = "192.168.0.100"
    
    window = MainWindow(camera_ip)
    window.show()
    
    # 초기 렌더링 트리거
    window.opengl_window.update()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
