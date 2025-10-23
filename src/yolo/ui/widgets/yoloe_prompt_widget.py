#coding=utf-8
"""
YOLOE 프롬프트 제어 위젯
"""
from pathlib import Path
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
                                QLineEdit, QPushButton, QLabel)
from PySide6.QtCore import Signal


class YOLOEPromptWidget(QGroupBox):
    """YOLOE 프롬프트 입력 위젯"""
    
    prompt_changed = Signal(list)  # 클래스 리스트
    
    def __init__(self, default_classes=None, parent=None):
        super().__init__("🎯 YOLOE 프롬프트", parent)
        self.default_classes = default_classes or ["car"]
        self.prompt_file = Path(__file__).parent.parent.parent / "prompts" / "current.txt"
        self.prompt_file.parent.mkdir(exist_ok=True)
        self.init_ui()
        self._load_prompt()  # 시작 시 자동 불러오기
    
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
        
        # 도움말
        help_label = QLabel("💡 예시: car, person, bicycle | 자동 저장됨")
        help_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(help_label)
        
        self.setLayout(layout)
    
    def _on_apply(self):
        """프롬프트 적용 + 자동 저장"""
        text = self.input_field.text().strip()
        if not text:
            return
        
        # 쉼표로 분리하고 공백 제거
        classes = [c.strip() for c in text.split(",") if c.strip()]
        
        if not classes:
            return
        
        self._update_current_label(classes)
        self._save_prompt(classes)  # 자동 저장
        self.prompt_changed.emit(classes)
    
    def _update_current_label(self, classes):
        """현재 프롬프트 레이블 업데이트"""
        self.current_label.setText(f"현재: {', '.join(classes)}")
    
    def update_classes(self, classes):
        """외부에서 클래스 업데이트"""
        self.input_field.setText(", ".join(classes))
        self._update_current_label(classes)
    
    def _load_prompt(self):
        """이전 프롬프트 불러오기"""
        if not self.prompt_file.exists():
            return
        
        try:
            with open(self.prompt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                return
            
            # 여러 줄 또는 쉼표 구분 모두 지원
            if '\n' in content:
                # 여러 줄 형식
                classes = [line.strip() for line in content.split('\n') if line.strip()]
            else:
                # 한 줄에 쉼표 구분 형식
                classes = [c.strip() for c in content.split(',') if c.strip()]
            
            if classes:
                self.input_field.setText(", ".join(classes))
                self._update_current_label(classes)
                print(f"✅ 이전 프롬프트 불러오기: {', '.join(classes)}")
        except Exception:
            pass
    
    def _save_prompt(self, classes):
        """프롬프트 자동 저장"""
        try:
            with open(self.prompt_file, 'w', encoding='utf-8') as f:
                for cls in classes:
                    f.write(f"{cls}\n")
        except Exception:
            pass

