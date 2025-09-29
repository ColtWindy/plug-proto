#coding=utf-8
"""UI 구성"""
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, 
                              QWidget, QLabel, QSlider, QPushButton)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap

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
        
        # 카메라 화면
        self.camera_label = QLabel("카메라 연결 중...")
        self.camera_label.setFixedSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("border: 1px solid gray; background: black; color: white;")
        layout.addWidget(self.camera_label)
        
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
        
        # 노출시간
        exposure_layout = QHBoxLayout()
        exposure_layout.addWidget(QLabel("노출시간:"))
        self.exposure_slider = QSlider(Qt.Horizontal)
        self.exposure_slider.setRange(1, 30)
        exposure_layout.addWidget(self.exposure_slider)
        self.exposure_label = QLabel()
        exposure_layout.addWidget(self.exposure_label)
        controls_layout.addLayout(exposure_layout)
        
        # VSync 딜레이
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("VSync 딜레이:"))
        self.delay_slider = QSlider(Qt.Horizontal)
        self.delay_slider.setRange(-50, 50)
        delay_layout.addWidget(self.delay_slider)
        self.delay_label = QLabel()
        delay_layout.addWidget(self.delay_label)
        controls_layout.addLayout(delay_layout)
        
        layout.addWidget(controls)
        
    
    def update_camera_frame(self, q_image):
        """카메라 프레임 업데이트"""
        if q_image:
            pixmap = QPixmap.fromImage(q_image)
            self.camera_label.setPixmap(pixmap)
    
    def update_info_panel(self, camera_info):
        """정보 패널 업데이트"""
        if not self.show_info_panel:
            return
            
        texts = [
            f"Camera: {camera_info.get('name', 'N/A')}",
            f"IP: {camera_info.get('ip', 'N/A')}  FPS: {camera_info.get('fps', 0):.1f}Hz (2프레임주기)",
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
        
    def update_exposure_display(self, value):
        """노출시간 표시 업데이트"""
        self.exposure_label.setText(f"{value}ms")
        
    def update_delay_display(self, value):
        """딜레이 표시 업데이트"""
        self.delay_label.setText(f"{value}ms")
    
    def set_slider_values(self, gain_value, exposure_value, delay_value):
        """슬라이더 값 설정 (시그널 방지)"""
        self.gain_slider.blockSignals(True)
        self.exposure_slider.blockSignals(True)
        self.delay_slider.blockSignals(True)
        
        self.gain_slider.setValue(int(gain_value))
        self.exposure_slider.setValue(int(exposure_value))
        self.delay_slider.setValue(int(delay_value))
        
        self.gain_slider.blockSignals(False)
        self.exposure_slider.blockSignals(False)
        self.delay_slider.blockSignals(False)
    
    def show_error(self, message):
        """오류 메시지 표시"""
        self.camera_label.clear()
        self.camera_label.setText(message)
