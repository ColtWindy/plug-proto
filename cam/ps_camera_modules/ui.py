#coding=utf-8
"""UI 구성"""
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, 
                              QWidget, QLabel, QSlider, QPushButton)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *
import numpy as np

class FastOpenGLWidget(QOpenGLWidget):
    """최소 딜레이 OpenGL 렌더링 위젯"""
    
    def __init__(self):
        super().__init__()
        self.frame_data = None
        self.texture_id = 0
        self.is_black = True
        
    def initializeGL(self):
        """OpenGL 초기화"""
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glEnable(GL_TEXTURE_2D)
        
        # 텍스처 생성
        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
    def paintGL(self):
        """OpenGL 렌더링 (최소 딜레이)"""
        glClear(GL_COLOR_BUFFER_BIT)
        
        if self.is_black:
            # 검은 화면 (즉시 렌더링)
            glClearColor(0.0, 0.0, 0.0, 1.0)
        elif self.frame_data is not None:
            # 텍스처 업데이트 및 렌더링
            glBindTexture(GL_TEXTURE_2D, self.texture_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 640, 480, 0, GL_RGB, GL_UNSIGNED_BYTE, self.frame_data)
            
            # 전체 화면에 텍스처 렌더링
            glBegin(GL_QUADS)
            glTexCoord2f(0.0, 1.0); glVertex2f(-1.0, -1.0)
            glTexCoord2f(1.0, 1.0); glVertex2f(1.0, -1.0)
            glTexCoord2f(1.0, 0.0); glVertex2f(1.0, 1.0)
            glTexCoord2f(0.0, 0.0); glVertex2f(-1.0, 1.0)
            glEnd()
            
    def update_frame(self, q_image):
        """프레임 업데이트 (즉시 반영)"""
        if q_image and not q_image.isNull():
            # QImage → OpenGL 텍스처 데이터 변환
            width, height = q_image.width(), q_image.height()
            ptr = q_image.bits()
            
            if ptr and width == 640 and height == 480:
                self.frame_data = np.frombuffer(ptr, dtype=np.uint8).reshape(height, width, 3)
                self.is_black = False
            else:
                self.is_black = True
        else:
            self.is_black = True
            
        self.update()  # 즉시 다시 그리기

class PSCameraUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.show_info_panel = True
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("PS Camera")
        self.setFixedSize(660, 600)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # OpenGL 카메라 화면 (최소 딜레이)
        self.gl_widget = FastOpenGLWidget()
        self.gl_widget.setFixedSize(640, 480)
        layout.addWidget(self.gl_widget)
        
        # 정보 패널
        self.info_widget = QWidget()
        info_layout = QVBoxLayout(self.info_widget)
        info_layout.setContentsMargins(5, 5, 5, 5)
        info_layout.setSpacing(2)
        
        self.info_labels = [QLabel() for _ in range(4)]
        for label in self.info_labels:
            label.setStyleSheet("color: white; font-size: 11px;")
            info_layout.addWidget(label)
        
        self.info_widget.setStyleSheet("background: rgba(40,40,40,200);")
        self.info_widget.setFixedSize(640, 80)
        layout.addWidget(self.info_widget)
        
        # 컨트롤
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        
        # 토글 버튼
        self.info_button = QPushButton("Hide Info")
        controls_layout.addWidget(self.info_button)
        
        
        
        
        # 게인
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("Gain:"))
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setRange(0, 100)
        gain_layout.addWidget(self.gain_slider)
        self.gain_label = QLabel()
        gain_layout.addWidget(self.gain_label)
        controls_layout.addLayout(gain_layout)
        
        # VSync 설정 표시 (읽기 전용)
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("VSync 딜레이:"))
        self.delay_label = QLabel("1ms")
        delay_layout.addWidget(self.delay_label)
        controls_layout.addLayout(delay_layout)
        
        # 노출시간 설정 표시 (읽기 전용)
        exposure_layout = QHBoxLayout()
        exposure_layout.addWidget(QLabel("노출 단축:"))
        self.exposure_adj_label = QLabel("0ms")
        exposure_layout.addWidget(self.exposure_adj_label)
        controls_layout.addLayout(exposure_layout)
        
        layout.addWidget(controls)
        
    
    def update_camera_frame(self, q_image):
        """카메라 프레임 업데이트 (OpenGL 직접 렌더링)"""
        self.gl_widget.update_frame(q_image)
    
    def update_info_panel(self, camera_info):
        """정보 패널 업데이트"""
        if not self.show_info_panel:
            return
            
        texts = [
            f"Camera: {camera_info.get('name', 'N/A')}",
            f"IP: {camera_info.get('ip', 'N/A')}  FPS: {camera_info.get('fps', 0):.1f} (30fps)",
            f"Resolution: {camera_info.get('width', 0)}x{camera_info.get('height', 0)}",
            f"Exposure: {camera_info.get('exposure', 0)}ms (Auto)  Gain: {camera_info.get('gain', 0)}"
        ]
        
        for i, text in enumerate(texts):
            self.info_labels[i].setText(text)
    
    def toggle_info(self):
        """정보 패널 토글"""
        self.show_info_panel = not self.show_info_panel
        self.info_widget.setVisible(self.show_info_panel)
        self.info_button.setText("Show Info" if not self.show_info_panel else "Hide Info")
    
    
    
    def update_gain_display(self, gain_value):
        """게인 표시 업데이트"""
        self.gain_label.setText(str(int(gain_value)))
        
    def update_delay_display(self, value):
        """딜레이 표시 업데이트"""
        self.delay_label.setText(f"{value}ms")
        
    def update_exposure_adj_display(self, value):
        """노출 보정 표시 업데이트"""
        self.exposure_adj_label.setText(f"{value}ms")
    
    
    def set_slider_values(self, gain_value):
        """슬라이더 값 설정 (시그널 방지)"""
        self.gain_slider.blockSignals(True)
        self.gain_slider.setValue(int(gain_value))
        self.gain_slider.blockSignals(False)
    
    def show_error(self, message):
        """오류 메시지 표시"""
        self.camera_label.clear()
        self.camera_label.setText(message)
