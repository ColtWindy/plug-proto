#coding=utf-8
"""
QOpenGL 프레임 카운터 예제
프레임을 1씩 증가시키며 OpenGL로 렌더링
"""
import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPainter, QFont, QColor, QSurfaceFormat
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
    """프레임 카운터를 표시하는 OpenGL 위젯"""
    
    def __init__(self):
        super().__init__()
        self.frame_count = 0
        
        # 60 FPS로 프레임 업데이트
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(16)  # ~60 FPS (1000ms / 60 ≈ 16ms)
        
    def initializeGL(self):
        """OpenGL 초기화"""
        GL.glClearColor(0.1, 0.1, 0.15, 1.0)
        
    def paintGL(self):
        """OpenGL 렌더링"""
        # OpenGL로 배경 클리어
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        
        # QPainter로 텍스트 렌더링
        painter = QPainter(self)
        painter.setFont(QFont("Arial", 48, QFont.Bold))
        painter.setPen(QColor(255, 255, 255))
        
        # 프레임 카운터 표시
        text = f"Frame: {self.frame_count}"
        painter.drawText(self.rect(), 0x0084, text)  # Qt.AlignCenter
        
        painter.end()
        
    def resizeGL(self, w, h):
        """윈도우 리사이즈 처리"""
        GL.glViewport(0, 0, w, h)
        
    def update_frame(self):
        """프레임 카운터 증가 및 업데이트"""
        self.frame_count += 1
        self.update()  # paintGL 호출


class MainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QOpenGL Frame Counter")
        self.setGeometry(100, 100, 800, 600)
        
        # OpenGL 위젯 설정
        self.opengl_widget = FrameCounterWidget()
        self.setCentralWidget(self.opengl_widget)


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
    
    # OpenGL ES Surface Format 설정 (Wayland + EGL)
    # Jetson은 OpenGL ES 3.2 + EGL + Wayland를 공식 지원
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.OpenGLES)  # EGL 사용 (GLX 대신)
    fmt.setVersion(3, 2)                            # OpenGL ES 3.2
    fmt.setSwapInterval(1)                          # vsync
    fmt.setSwapBehavior(QSurfaceFormat.DoubleBuffer)
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)
    
    print(f"🎨 OpenGL ES 3.2 + EGL + Wayland 설정 완료")
    print(f"📌 QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM')}")
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
