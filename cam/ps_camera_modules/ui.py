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
        
        # 노출 모드 토글
        exposure_mode_layout = QHBoxLayout()
        exposure_mode_layout.addWidget(QLabel("Exposure Mode:"))
        self.exposure_mode_button = QPushButton("Manual")
        self.exposure_mode_button.setFixedWidth(80)
        exposure_mode_layout.addWidget(self.exposure_mode_button)
        exposure_mode_layout.addStretch()
        controls_layout.addLayout(exposure_mode_layout)
        
        # FPS 설정 버튼들
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("FPS:"))
        
        self.fps_15_button = QPushButton("15")
        self.fps_15_button.setFixedWidth(40)
        self.fps_30_button = QPushButton("30")
        self.fps_30_button.setFixedWidth(40)
        self.fps_60_button = QPushButton("60")
        self.fps_60_button.setFixedWidth(40)
        self.fps_auto_button = QPushButton("Auto")
        self.fps_auto_button.setFixedWidth(50)
        self.fps_auto_button.setStyleSheet("background-color: #0078d4; color: white;")  # 기본 선택
        
        fps_layout.addWidget(self.fps_15_button)
        fps_layout.addWidget(self.fps_30_button)
        fps_layout.addWidget(self.fps_60_button)
        fps_layout.addWidget(self.fps_auto_button)
        fps_layout.addStretch()
        controls_layout.addLayout(fps_layout)
        
        # 노출시간
        exp_layout = QHBoxLayout()
        exp_layout.addWidget(QLabel("Exposure:"))
        self.exposure_slider = QSlider(Qt.Horizontal)
        self.exposure_slider.setRange(1, 100)
        exp_layout.addWidget(self.exposure_slider)
        self.exposure_label = QLabel()
        exp_layout.addWidget(self.exposure_label)
        controls_layout.addLayout(exp_layout)
        
        # 게인
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("Gain:"))
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setRange(0, 100)
        gain_layout.addWidget(self.gain_slider)
        self.gain_label = QLabel()
        gain_layout.addWidget(self.gain_label)
        controls_layout.addLayout(gain_layout)
        
        layout.addWidget(controls)
        
        # 초기 상태 설정
        self.manual_exposure = True  # 수동 노출로 시작
        self.current_fps_mode = "Auto"  # 자동 FPS로 시작
    
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
            f"IP: {camera_info.get('ip', 'N/A')}  FPS: {camera_info.get('fps', 0):.1f} ({self.current_fps_mode})",
            f"Resolution: {camera_info.get('width', 0)}x{camera_info.get('height', 0)}",
            f"Exposure: {camera_info.get('exposure', 0)}ms  Gain: {camera_info.get('gain', 0)}"
        ]
        
        for i, text in enumerate(texts):
            self.info_labels[i].setText(text)
    
    def toggle_info(self):
        """정보 패널 토글"""
        self.show_info_panel = not self.show_info_panel
        self.info_widget.setVisible(self.show_info_panel)
        self.info_button.setText("Show Info" if not self.show_info_panel else "Hide Info")
    
    def toggle_exposure_mode(self):
        """노출 모드 토글"""
        self.manual_exposure = not self.manual_exposure
        if self.manual_exposure:
            self.exposure_mode_button.setText("Manual")
            self.exposure_slider.setEnabled(True)
        else:
            self.exposure_mode_button.setText("Auto")
            self.exposure_slider.setEnabled(False)
        return self.manual_exposure
    
    def update_exposure_display(self, exposure_ms, is_auto=False):
        """노출시간 표시 업데이트"""
        if is_auto:
            self.exposure_label.setText(f"{exposure_ms:.1f}ms (Auto)")
        else:
            self.exposure_label.setText(f"{int(exposure_ms)}ms")
    
    def update_gain_display(self, gain_value):
        """게인 표시 업데이트"""
        self.gain_label.setText(str(int(gain_value)))
    
    def set_fps_mode(self, fps_mode):
        """FPS 모드 설정"""
        # 모든 버튼 기본 스타일로 초기화
        for btn in [self.fps_15_button, self.fps_30_button, self.fps_60_button, self.fps_auto_button]:
            btn.setStyleSheet("")
        
        # 선택된 버튼 하이라이트
        if fps_mode == "15":
            self.fps_15_button.setStyleSheet("background-color: #0078d4; color: white;")
        elif fps_mode == "30":
            self.fps_30_button.setStyleSheet("background-color: #0078d4; color: white;")
        elif fps_mode == "60":
            self.fps_60_button.setStyleSheet("background-color: #0078d4; color: white;")
        else:
            self.fps_auto_button.setStyleSheet("background-color: #0078d4; color: white;")
        
        self.current_fps_mode = fps_mode
        return fps_mode
    
    def set_slider_values(self, exposure_ms, gain_value):
        """슬라이더 값 설정 (시그널 방지)"""
        self.exposure_slider.blockSignals(True)
        self.gain_slider.blockSignals(True)
        
        self.exposure_slider.setValue(int(exposure_ms))
        self.gain_slider.setValue(int(gain_value))
        
        self.exposure_slider.blockSignals(False)
        self.gain_slider.blockSignals(False)
    
    def show_error(self, message):
        """오류 메시지 표시"""
        self.camera_label.clear()
        self.camera_label.setText(message)
