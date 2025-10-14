#coding=utf-8
"""
카메라 제어 위젯
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QGroupBox
from PySide6.QtCore import Signal


class CameraControlWidget(QWidget):
    """카메라 전용 제어 위젯"""
    
    # 시그널
    resolution_changed = Signal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 해상도
        res_group = QGroupBox("해상도")
        res_layout = QVBoxLayout()
        self.resolution_combo = QComboBox()
        self.resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        res_layout.addWidget(self.resolution_combo)
        res_group.setLayout(res_layout)
        layout.addWidget(res_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def setup_resolution(self, resolutions, current_index):
        """해상도 설정"""
        self.resolution_combo.clear()
        for res in resolutions:
            self.resolution_combo.addItem(res['text'], res['desc'])
        self.resolution_combo.setCurrentIndex(current_index)
    
    def _on_resolution_changed(self, index):
        """해상도 변경"""
        if index >= 0:
            resolution = self.resolution_combo.itemData(index)
            if resolution:
                self.resolution_changed.emit(resolution)

