#coding=utf-8
"""
QOpenGLWidget 기반 프레임 드랍 방지 예제
VSync + Triple Buffer를 사용하여 프레임 동기화
"""
import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QToolBar, QPushButton
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QSurfaceFormat, QPainter, QFont, QColor
from PySide6.QtCore import Qt
from OpenGL import GL


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


class FrameCounterWidget(QOpenGLWidget):
    """프레임 카운터를 표시하는 OpenGL 위젯 (VSync 동기화)"""
    
    def __init__(self):
        super().__init__()
        self._frame = 0
        self._needs_update = True

    def initializeGL(self):
        """OpenGL 초기화"""
        GL.glClearColor(0.1, 0.1, 0.15, 1.0)

    def paintGL(self):
        """
        프레임 렌더링
        VSync와 자동 동기화됨 (SwapInterval=1)
        """
        self._frame += 1
        
        # 배경색을 프레임에 따라 변경 (시각적 피드백)
        c = (self._frame % 255) / 255.0
        GL.glClearColor(0.1, 0.1, c * 0.3 + 0.15, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        
        # QPainter로 텍스트 렌더링
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        # 프레임 번호 표시
        painter.setFont(QFont("Arial", 72, QFont.Bold))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(self.rect(), Qt.AlignCenter, f"{self._frame}")
        
        # FPS 정보 표시 (좌측 상단)
        painter.setFont(QFont("Monospace", 14))
        painter.setPen(QColor(200, 200, 200))
        info_text = "VSync: ON | Triple Buffer | OpenGL ES 3.2"
        painter.drawText(10, 30, info_text)
        
        painter.end()
        
        # 다음 프레임 예약 (VSync와 동기화)
        if self._needs_update:
            self.update()
    
    def resizeGL(self, w, h):
        """윈도우 리사이즈 처리"""
        GL.glViewport(0, 0, w, h)
    
    def showEvent(self, event):
        """위젯이 표시될 때 연속 업데이트 시작"""
        super().showEvent(event)
        self._needs_update = True
        self.update()
    
    def hideEvent(self, event):
        """위젯이 숨겨질 때 업데이트 중지"""
        super().hideEvent(event)
        self._needs_update = False


class MainWindow(QMainWindow):
    """종료 버튼이 있는 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VSync Frame Counter - No Drop (OpenGL ES 3.2)")
        
        # OpenGL 위젯 생성
        self.opengl_widget = FrameCounterWidget()
        self.setCentralWidget(self.opengl_widget)
        
        # 툴바 추가
        toolbar = QToolBar("Controls")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
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
        toolbar.addWidget(quit_btn)
        
        # 윈도우 크기 설정
        self.resize(1024, 768)

    def keyPressEvent(self, event):
        """ESC 또는 Q 키로 종료"""
        if event.key() == Qt.Key_Escape or event.key() == Qt.Key_Q:
            self.close()


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
    
    # VSync 및 트리플 버퍼링 설정 (Wayland + EGL)
    # Jetson은 OpenGL ES 3.2 + EGL + Wayland를 공식 지원
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.OpenGLES)    # EGL 사용 (GLX 대신)
    fmt.setVersion(3, 2)                              # OpenGL ES 3.2
    fmt.setSwapInterval(1)                            # vsync 활성화
    fmt.setSwapBehavior(QSurfaceFormat.TripleBuffer)  # 스톨 완화 (지연 +1프레임)
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)
    
    print(f"🎨 OpenGL ES 3.2 + EGL + Wayland + Triple Buffer 설정 완료")
    print(f"📌 QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM')}")
    
    app = QApplication(sys.argv)
    
    # Wayland 환경에서 GPU 가속 사용
    # 필요시 환경변수: export QT_QPA_PLATFORM=wayland-egl
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
