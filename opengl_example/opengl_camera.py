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
from PySide6.QtGui import QSurfaceFormat, QPainter, QFont, QColor, QPixmap, QImage
from PySide6.QtCore import Qt, QTimer
from OpenGL import GL
from camera_controller import OpenGLCameraController
from cam import mvsdk


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
        self.display_number = 0  # 표시할 숫자 (홀수 프레임에서만 증가)
        self.parent_window = parent_window  # 메인 윈도우 참조
        
        # frameSwapped 시그널을 사용하여 vsync 기반 프레임 업데이트
        self.frameSwapped.connect(self.on_frame_swapped, Qt.QueuedConnection)

    def initializeGL(self):
        """OpenGL 초기화"""
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
    
    def resizeGL(self, w, h):
        """윈도우 크기 변경 처리"""
        GL.glViewport(0, 0, w, h)

    def paintGL(self):
        """
        프레임 렌더링
        frameSwapped 시그널에 의해 vsync와 동기화되어 호출됨
        짝수 프레임: 검은 화면, 홀수 프레임: 카메라 화면
        """
        self._frame += 1
        cycle_position = self._frame % 2
        
        # 배경 클리어
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        
        # QPainter로 렌더링
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        
        w = self.width()
        h = self.height()
        
        if cycle_position == 0:
            # 짝수 프레임: 검은 화면만 표시
            painter.fillRect(0, 0, w, h, QColor(0, 0, 0))
            
        else:
            # 홀수 프레임: 카메라 화면 + 숫자 표시
            self.display_number += 1
            
            # 대기 중인 픽셀맵이 있으면 교체
            if self.pending_pixmap is not None:
                self.current_pixmap = self.pending_pixmap
                self.pending_pixmap = None
            
            # 카메라 이미지 표시
            if self.current_pixmap and not self.current_pixmap.isNull():
                # 윈도우 크기에 맞춰 스케일링 (비율 유지)
                scaled_pixmap = self.current_pixmap.scaled(
                    w, h, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                # 중앙 정렬
                x = (w - scaled_pixmap.width()) // 2
                y = (h - scaled_pixmap.height()) // 2
                painter.drawPixmap(x, y, scaled_pixmap)
            else:
                # 카메라 이미지가 없으면 검은 화면
                painter.fillRect(0, 0, w, h, QColor(0, 0, 0))
        
        # 프레임 정보 표시 (좌측 상단, 항상 표시)
        painter.setFont(QFont("Monospace", 12))
        painter.setPen(QColor(0, 255, 0))
        cycle_name = "검은화면" if cycle_position == 0 else "카메라화면"
        info_text = f"Frame: {self._frame} | Num: {self.display_number} | {cycle_name}"
        painter.drawText(10, 25, info_text)
        
        painter.end()

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
        
        # 종료 버튼
        button_layout = QHBoxLayout()
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
    
    def on_vsync_frame(self, cycle_position):
        """VSync 프레임 신호 처리 - 고정밀 타이밍"""
        if not self.camera or not self.camera.hCamera:
            return
        
        if cycle_position == 0:
            # 짝수 프레임: 검은 화면 표시 시점에 카메라 트리거
            if self.vsync_delay_ms > 0:
                # 고정밀 딜레이를 위해 별도 스레드에서 처리
                threading.Thread(
                    target=self._precise_delay_trigger,
                    args=(self.vsync_delay_ms,),
                    daemon=True
                ).start()
            else:
                # 딜레이 0이면 즉시 트리거
                mvsdk.CameraSoftTrigger(self.camera.hCamera)
    
    def _precise_delay_trigger(self, delay_ms):
        """
        고정밀 딜레이 후 카메라 트리거
        busy-wait 방식으로 마이크로초 수준의 정확도 보장
        """
        if delay_ms <= 0:
            return
        
        # 시작 시간 기록
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
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
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
