#coding=utf-8
"""
카메라 제어 위젯
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QComboBox, QGroupBox
from PySide6.QtCore import Qt, Signal


class CameraControlWidget(QWidget):
    """카메라 전용 제어 위젯"""
    
    # 시그널
    resolution_changed = Signal(object)
    fps_changed = Signal(int)
    exposure_changed = Signal(int)
    gain_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 해상도
        res_group = QGroupBox("해상도")
        res_layout = QVBoxLayout()
        self.resolution_combo = QComboBox()
        self.resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        res_layout.addWidget(self.resolution_combo)
        res_group.setLayout(res_layout)
        layout.addWidget(res_group)
        
        # FPS
        fps_group = QGroupBox("프레임 속도")
        fps_layout = QVBoxLayout()
        
        fps_control = QHBoxLayout()
        fps_control.addWidget(QLabel("FPS:"))
        self.fps_slider = QSlider(Qt.Horizontal)
        self.fps_slider.setMinimum(15)
        self.fps_slider.setMaximum(60)
        self.fps_slider.setValue(30)
        self.fps_slider.valueChanged.connect(self._on_fps_changed)
        fps_control.addWidget(self.fps_slider)
        
        self.fps_label = QLabel("30")
        self.fps_label.setMinimumWidth(30)
        fps_control.addWidget(self.fps_label)
        fps_layout.addLayout(fps_control)
        
        fps_group.setLayout(fps_layout)
        layout.addWidget(fps_group)
        
        # 노출
        exposure_group = QGroupBox("노출 시간")
        exposure_layout = QVBoxLayout()
        
        exposure_control = QHBoxLayout()
        self.exposure_slider = QSlider(Qt.Horizontal)
        self.exposure_slider.valueChanged.connect(self._on_exposure_changed)
        exposure_control.addWidget(self.exposure_slider)
        
        self.exposure_label = QLabel("0 ms")
        self.exposure_label.setMinimumWidth(60)
        exposure_control.addWidget(self.exposure_label)
        exposure_layout.addLayout(exposure_control)
        
        exposure_group.setLayout(exposure_layout)
        layout.addWidget(exposure_group)
        
        # 게인
        gain_group = QGroupBox("게인")
        gain_layout = QVBoxLayout()
        
        gain_control = QHBoxLayout()
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.valueChanged.connect(self._on_gain_changed)
        gain_control.addWidget(self.gain_slider)
        
        self.gain_label = QLabel("0")
        self.gain_label.setMinimumWidth(60)
        gain_control.addWidget(self.gain_label)
        gain_layout.addLayout(gain_control)
        
        gain_group.setLayout(gain_layout)
        layout.addWidget(gain_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def setup_resolution(self, resolutions, current_index):
        """해상도 설정"""
        self.resolution_combo.clear()
        for res in resolutions:
            self.resolution_combo.addItem(res['text'], res['desc'])
        self.resolution_combo.setCurrentIndex(current_index)
    
    def setup_exposure(self, min_val, max_val, current_val):
        """노출 설정"""
        self.exposure_slider.setMinimum(min_val)
        self.exposure_slider.setMaximum(max_val)
        self.exposure_slider.setValue(current_val)
        self.exposure_label.setText(f"{current_val} ms")
    
    def setup_gain(self, min_val, max_val, current_val):
        """게인 설정"""
        self.gain_slider.setMinimum(min_val)
        self.gain_slider.setMaximum(max_val)
        self.gain_slider.setValue(current_val)
        self.gain_label.setText(f"{current_val}")
    
    def update_max_exposure(self, fps):
        """FPS에 따른 최대 노출 시간 업데이트"""
        max_exposure_ms = int(1000 / fps * 0.8)
        self.exposure_slider.setMaximum(max_exposure_ms)
        
        if self.exposure_slider.value() > max_exposure_ms:
            self.exposure_slider.setValue(max_exposure_ms)
    
    def _on_resolution_changed(self, index):
        """해상도 변경"""
        if index >= 0:
            resolution = self.resolution_combo.itemData(index)
            if resolution:
                self.resolution_changed.emit(resolution)
    
    def _on_fps_changed(self, value):
        """FPS 변경"""
        self.fps_label.setText(f"{value}")
        self.fps_changed.emit(value)
    
    def _on_exposure_changed(self, value):
        """노출 변경"""
        self.exposure_label.setText(f"{value} ms")
        self.exposure_changed.emit(value)
    
    def _on_gain_changed(self, value):
        """게인 변경"""
        self.gain_label.setText(f"{value}")
        self.gain_changed.emit(value)

