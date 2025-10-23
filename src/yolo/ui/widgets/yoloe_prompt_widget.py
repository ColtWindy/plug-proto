#coding=utf-8
"""
YOLOE 프롬프트 제어 위젯
"""
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
                                QLineEdit, QPushButton, QLabel)
from PySide6.QtCore import Signal


class YOLOEPromptWidget(QGroupBox):
    """YOLOE 프롬프트 입력 위젯"""
    
    prompt_changed = Signal(list)  # 클래스 리스트
    
    def __init__(self, default_classes=None, parent=None):
        super().__init__("🎯 YOLOE 프롬프트", parent)
        self.default_classes = default_classes or ["car"]
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 현재 프롬프트 표시
        self.current_label = QLabel()
        self.current_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self._update_current_label(self.default_classes)
        layout.addWidget(self.current_label)
        
        # 입력 필드 + 적용 버튼
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("클래스 입력 (쉼표로 구분)")
        self.input_field.setText(", ".join(self.default_classes))
        self.input_field.returnPressed.connect(self._on_apply)
        input_layout.addWidget(self.input_field)
        
        self.apply_btn = QPushButton("적용")
        self.apply_btn.setMinimumHeight(30)
        self.apply_btn.clicked.connect(self._on_apply)
        input_layout.addWidget(self.apply_btn)
        
        layout.addLayout(input_layout)
        
        # 프리셋 버튼
        preset_layout = QHBoxLayout()
        
        presets = [
            ("교통", ["car", "truck", "bus", "motorcycle", "bicycle"]),
            ("사람", ["person"]),
            ("동물", ["cat", "dog", "bird"]),
            ("전체", ["car", "person", "bicycle", "motorcycle"])
        ]
        
        for name, classes in presets:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, c=classes: self._apply_preset(c))
            preset_layout.addWidget(btn)
        
        layout.addLayout(preset_layout)
        
        # 도움말
        help_label = QLabel("💡 예시: car, person, bicycle")
        help_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(help_label)
        
        self.setLayout(layout)
    
    def _on_apply(self):
        """프롬프트 적용"""
        text = self.input_field.text().strip()
        if not text:
            return
        
        # 쉼표로 분리하고 공백 제거
        classes = [c.strip() for c in text.split(",") if c.strip()]
        
        if not classes:
            return
        
        self._update_current_label(classes)
        self.prompt_changed.emit(classes)
    
    def _apply_preset(self, classes):
        """프리셋 적용"""
        self.input_field.setText(", ".join(classes))
        self._on_apply()
    
    def _update_current_label(self, classes):
        """현재 프롬프트 레이블 업데이트"""
        self.current_label.setText(f"현재: {', '.join(classes)}")
    
    def update_classes(self, classes):
        """외부에서 클래스 업데이트"""
        self.input_field.setText(", ".join(classes))
        self._update_current_label(classes)

