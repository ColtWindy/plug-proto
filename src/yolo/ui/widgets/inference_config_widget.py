#coding=utf-8
"""
추론 설정 위젯
"""
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
                                QLabel, QCheckBox, QSpinBox, QWidget)
from PySide6.QtCore import Qt, Signal
from inference.config import EngineConfig, PTConfig
from ui.widgets.click_slider import ClickSlider


class InferenceConfigWidget(QGroupBox):
    """추론 파라미터 설정 위젯"""
    
    config_changed = Signal(object)
    
    def __init__(self, config):
        super().__init__("추론 설정")
        self.config = config
        self.is_pt = isinstance(config, PTConfig)
        self._init_ui()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        layout.addWidget(self._create_conf_slider())
        layout.addWidget(self._create_iou_slider())
        layout.addWidget(self._create_max_det_spinbox())
        
        # PT 전용 옵션
        if self.is_pt:
            layout.addWidget(self._create_imgsz_spinbox())
        
        layout.addWidget(self._create_advanced_options())
        
        self.setLayout(layout)
    
    def _create_conf_slider(self):
        """신뢰도 임계값 슬라이더"""
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("신뢰도:")
        label.setMinimumWidth(60)
        
        self.conf_slider = ClickSlider(Qt.Horizontal)
        self.conf_slider.setMinimum(0)
        self.conf_slider.setMaximum(100)
        self.conf_slider.setValue(int(self.config.conf * 100))
        self.conf_slider.valueChanged.connect(self._on_conf_changed)
        
        self.conf_value = QLabel(f"{self.config.conf:.2f}")
        self.conf_value.setMinimumWidth(40)
        
        layout.addWidget(label)
        layout.addWidget(self.conf_slider)
        layout.addWidget(self.conf_value)
        
        container.setLayout(layout)
        return container
    
    def _create_iou_slider(self):
        """IoU 임계값 슬라이더"""
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("IoU:")
        label.setMinimumWidth(60)
        
        self.iou_slider = ClickSlider(Qt.Horizontal)
        self.iou_slider.setMinimum(0)
        self.iou_slider.setMaximum(100)
        self.iou_slider.setValue(int(self.config.iou * 100))
        self.iou_slider.valueChanged.connect(self._on_iou_changed)
        
        self.iou_value = QLabel(f"{self.config.iou:.2f}")
        self.iou_value.setMinimumWidth(40)
        
        layout.addWidget(label)
        layout.addWidget(self.iou_slider)
        layout.addWidget(self.iou_value)
        
        container.setLayout(layout)
        return container
    
    def _create_imgsz_spinbox(self):
        """이미지 크기 설정"""
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("이미지 크기:")
        label.setMinimumWidth(60)
        
        self.imgsz_spinbox = QSpinBox()
        self.imgsz_spinbox.setMinimum(320)
        self.imgsz_spinbox.setMaximum(1280)
        self.imgsz_spinbox.setSingleStep(32)
        self.imgsz_spinbox.setValue(self.config.imgsz)
        self.imgsz_spinbox.valueChanged.connect(self._on_imgsz_changed)
        
        layout.addWidget(label)
        layout.addWidget(self.imgsz_spinbox)
        layout.addStretch()
        
        container.setLayout(layout)
        return container
    
    def _create_max_det_spinbox(self):
        """최대 탐지 수 설정"""
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("최대 탐지:")
        label.setMinimumWidth(60)
        
        self.max_det_spinbox = QSpinBox()
        self.max_det_spinbox.setMinimum(1)
        self.max_det_spinbox.setMaximum(1000)
        self.max_det_spinbox.setSingleStep(50)
        self.max_det_spinbox.setValue(self.config.max_det)
        self.max_det_spinbox.valueChanged.connect(self._on_max_det_changed)
        
        layout.addWidget(label)
        layout.addWidget(self.max_det_spinbox)
        layout.addStretch()
        
        container.setLayout(layout)
        return container
    
    def _create_advanced_options(self):
        """고급 옵션"""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.agnostic_nms_check = QCheckBox("Class-Agnostic NMS")
        self.agnostic_nms_check.setChecked(self.config.agnostic_nms)
        self.agnostic_nms_check.toggled.connect(self._on_agnostic_nms_changed)
        layout.addWidget(self.agnostic_nms_check)
        
        # PT 전용 옵션
        if self.is_pt:
            self.augment_check = QCheckBox("Test-Time Augmentation")
            self.augment_check.setChecked(self.config.augment)
            self.augment_check.toggled.connect(self._on_augment_changed)
            layout.addWidget(self.augment_check)
        
        container.setLayout(layout)
        return container
    
    def _on_conf_changed(self, value):
        """신뢰도 변경"""
        self.config.conf = value / 100.0
        self.conf_value.setText(f"{self.config.conf:.2f}")
        self.config_changed.emit(self.config)
    
    def _on_iou_changed(self, value):
        """IoU 변경"""
        self.config.iou = value / 100.0
        self.iou_value.setText(f"{self.config.iou:.2f}")
        self.config_changed.emit(self.config)
    
    def _on_imgsz_changed(self, value):
        """이미지 크기 변경"""
        self.config.imgsz = value
        self.config_changed.emit(self.config)
    
    def _on_max_det_changed(self, value):
        """최대 탐지 수 변경"""
        self.config.max_det = value
        self.config_changed.emit(self.config)
    
    def _on_agnostic_nms_changed(self, checked):
        """Agnostic NMS 변경"""
        self.config.agnostic_nms = checked
        self.config_changed.emit(self.config)
    
    def _on_augment_changed(self, checked):
        """Augmentation 변경 (PT 전용)"""
        if self.is_pt:
            self.config.augment = checked
            self.config_changed.emit(self.config)

