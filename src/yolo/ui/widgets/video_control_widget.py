#coding=utf-8
"""
비디오 파일 제어 위젯
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QGroupBox
from PySide6.QtCore import Qt, Signal


class VideoControlWidget(QWidget):
    """비디오 파일 전용 제어 위젯"""
    
    # 시그널
    fps_changed = Signal(int)
    
    def __init__(self, video_files=None, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # FPS (재생 속도)
        fps_group = QGroupBox("재생 속도")
        fps_layout = QVBoxLayout()
        
        fps_control = QHBoxLayout()
        self.fps_slider = QSlider(Qt.Horizontal)
        self.fps_slider.setMinimum(1)
        self.fps_slider.setMaximum(60)
        self.fps_slider.setValue(30)
        self.fps_slider.valueChanged.connect(self._on_fps_changed)
        fps_control.addWidget(self.fps_slider)
        
        self.fps_label = QLabel("30 FPS")
        self.fps_label.setMinimumWidth(60)
        fps_control.addWidget(self.fps_label)
        fps_layout.addLayout(fps_control)
        
        fps_group.setLayout(fps_layout)
        layout.addWidget(fps_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _on_fps_changed(self, value):
        """FPS 변경"""
        self.fps_label.setText(f"{value} FPS")
        self.fps_changed.emit(value)

