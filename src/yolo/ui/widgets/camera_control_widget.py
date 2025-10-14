#coding=utf-8
"""
카메라 제어 위젯
"""
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox
from PySide6.QtCore import Qt, Signal


class CameraControlWidget(QGroupBox):
    """카메라 전용 제어 위젯"""
    
    # 시그널
    start_camera = Signal()
    stop_camera = Signal()
    
    def __init__(self, parent=None):
        super().__init__("카메라 제어", parent)
        self.is_running = False
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 제어 버튼
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ 시작")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ 중지")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        
        # 상태 표시
        self.status_label = QLabel("대기 중")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _on_start(self):
        """카메라 시작"""
        self.is_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("실행 중")
        self.start_camera.emit()
    
    def _on_stop(self):
        """카메라 중지"""
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("중지됨")
        self.stop_camera.emit()
