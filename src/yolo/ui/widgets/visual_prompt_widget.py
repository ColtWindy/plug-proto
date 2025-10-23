#coding=utf-8
"""
Visual Prompt 위젯
train/images 폴더의 이미지를 visual prompt로 사용
"""
from pathlib import Path
import numpy as np
import cv2
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QComboBox, 
                                QPushButton, QLabel, QHBoxLayout)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPixmap


class VisualPromptWidget(QGroupBox):
    """Visual Prompt 제어 위젯"""
    
    visual_prompt_changed = Signal(dict)  # {image_path, bboxes, cls}
    
    def __init__(self, train_images_dir):
        super().__init__("Visual Prompt")
        
        self.train_images_dir = Path(train_images_dir)
        self.labels_dir = self.train_images_dir.parent / "labels"
        self.image_files = self._scan_images()
        self.current_prompt = None
        
        self._init_ui()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 이미지 선택
        self.image_combo = QComboBox()
        self.image_combo.addItem("사용 안 함", "")
        
        for img_path in self.image_files:
            img_name = Path(img_path).name
            self.image_combo.addItem(img_name, str(img_path))
        
        layout.addWidget(QLabel("Reference 이미지:"))
        layout.addWidget(self.image_combo)
        
        # 적용 버튼
        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("적용")
        self.apply_btn.clicked.connect(self._on_apply)
        self.clear_btn = QPushButton("해제")
        self.clear_btn.clicked.connect(self._on_clear)
        self.clear_btn.setEnabled(False)
        
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)
        
        # 프리뷰
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedHeight(100)
        self.preview_label.setStyleSheet("border: 1px solid gray;")
        layout.addWidget(self.preview_label)
        
        # 상태
        self.status_label = QLabel("미사용")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def _scan_images(self):
        """train/images 폴더에서 이미지 스캔"""
        if not self.train_images_dir.exists():
            return []
        
        extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        images = []
        for ext in extensions:
            images.extend(self.train_images_dir.glob(f"*{ext}"))
        
        return sorted([str(f) for f in images])
    
    def _on_apply(self):
        """Visual prompt 적용"""
        image_path = self.image_combo.currentData()
        
        if not image_path:
            self.status_label.setText("이미지를 선택하세요")
            return
        
        # label 파일에서 bbox 정보 읽기
        bboxes, cls = self._load_bboxes(image_path)
        
        if bboxes is None:
            self.status_label.setText("Label 파일을 찾을 수 없습니다")
            self.status_label.setStyleSheet("color: red;")
            return
        
        self.current_prompt = {
            'image_path': image_path,
            'bboxes': bboxes,
            'cls': cls
        }
        
        self._update_preview(image_path)
        self.status_label.setText(f"적용됨: {Path(image_path).name} ({len(bboxes)}개)")
        self.status_label.setStyleSheet("color: green;")
        self.clear_btn.setEnabled(True)
        
        self.visual_prompt_changed.emit(self.current_prompt)
    
    def _on_clear(self):
        """Visual prompt 해제"""
        self.current_prompt = None
        self.image_combo.setCurrentIndex(0)
        self.preview_label.clear()
        self.status_label.setText("미사용")
        self.status_label.setStyleSheet("color: gray;")
        self.clear_btn.setEnabled(False)
        
        self.visual_prompt_changed.emit({})
    
    def _update_preview(self, image_path):
        """프리뷰 업데이트"""
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
    
    def _load_bboxes(self, image_path):
        """
        Label 파일에서 bbox 읽기 → 픽셀 좌표로 변환
        
        Returns:
            (bboxes, cls): pixel xyxy numpy arrays or (None, None)
        """
        image_name = Path(image_path).stem
        label_path = self.labels_dir / f"{image_name}.txt"
        
        if not label_path.exists():
            print(f"❌ Label 파일 없음: {label_path}")
            return None, None
        
        # 이미지 크기 읽기
        img = cv2.imread(str(image_path))
        if img is None:
            print(f"❌ 이미지 로드 실패: {image_path}")
            return None, None
        
        img_h, img_w = img.shape[:2]
        
        try:
            bboxes_list = []
            cls_list = []
            
            with open(label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                    
                    cls_id = int(parts[0])
                    coords = [float(x) for x in parts[1:]]
                    
                    # Segmentation polygon → bbox
                    if len(coords) > 4:
                        x_coords = coords[0::2]
                        y_coords = coords[1::2]
                        x1 = min(x_coords) * img_w
                        y1 = min(y_coords) * img_h
                        x2 = max(x_coords) * img_w
                        y2 = max(y_coords) * img_h
                    # Detection xywh → xyxy
                    else:
                        x_center, y_center, width, height = coords
                        x1 = (x_center - width / 2) * img_w
                        y1 = (y_center - height / 2) * img_h
                        x2 = (x_center + width / 2) * img_w
                        y2 = (y_center + height / 2) * img_h
                    
                    bboxes_list.append([x1, y1, x2, y2])
                    cls_list.append(cls_id)
            
            if not bboxes_list:
                return None, None
            
            bboxes = np.array(bboxes_list, dtype=np.float32)
            cls = np.array(cls_list, dtype=np.int32)
            
            print(f"✅ Visual prompt: {len(bboxes)}개 객체 (이미지: {img_w}x{img_h})")
            print(f"   픽셀 좌표 (xyxy):")
            for i, (bbox, c) in enumerate(zip(bboxes, cls)):
                print(f"   [{i}] class={c}, x1={bbox[0]:.1f}, y1={bbox[1]:.1f}, x2={bbox[2]:.1f}, y2={bbox[3]:.1f}")
            
            return bboxes, cls
            
        except Exception as e:
            print(f"❌ Label 파싱 실패: {e}")
            return None, None
    
    def get_current_prompt(self):
        """현재 visual prompt 반환"""
        return self.current_prompt

