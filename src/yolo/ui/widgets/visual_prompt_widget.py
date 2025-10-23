#coding=utf-8
"""
Visual Prompt 위젯 (간단 버전)
train 폴더의 모든 이미지를 자동으로 레퍼런스로 사용
"""
from pathlib import Path
import numpy as np
import cv2
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QLabel)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont


class VisualPromptWidget(QGroupBox):
    """Visual Prompt 정보 표시 위젯"""
    
    visual_prompts_loaded = Signal(list)  # [{image_path, bboxes, cls}, ...]
    
    def __init__(self, train_images_dir):
        super().__init__("Visual Prompt 정보")
        
        self.train_images_dir = Path(train_images_dir)
        self.labels_dir = self.train_images_dir.parent / "labels"
        self.prompts = []
        
        self._init_ui()
        self._load_all_prompts()
    
    def _init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 정보 라벨
        self.info_label = QLabel("로딩 중...")
        self.info_label.setWordWrap(True)
        font = QFont()
        font.setPointSize(9)
        self.info_label.setFont(font)
        layout.addWidget(self.info_label)
        
        self.setLayout(layout)
    
    def _load_all_prompts(self):
        """모든 train 이미지의 레퍼런스 자동 로드"""
        if not self.train_images_dir.exists():
            self.info_label.setText("❌ train/images 폴더 없음")
            return
        
        extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        image_files = []
        for ext in extensions:
            image_files.extend(self.train_images_dir.glob(f"*{ext}"))
        
        if not image_files:
            self.info_label.setText("❌ 이미지 없음")
            return
        
        # 모든 이미지의 bbox 로드
        self.prompts = []
        total_objects = 0
        all_classes = set()
        
        for img_path in sorted(image_files):
            bboxes, cls = self._load_single_image(img_path)
            if bboxes is not None:
                self.prompts.append({
                    'image_path': str(img_path),
                    'bboxes': bboxes,
                    'cls': cls
                })
                total_objects += len(bboxes)
                all_classes.update(cls.tolist())
        
        # 정보 표시
        if self.prompts:
            classes_str = ', '.join(map(str, sorted(all_classes)))
            info = f"✅ 레퍼런스: {len(self.prompts)}개 이미지\n"
            info += f"   객체: {total_objects}개\n"
            info += f"   클래스: [{classes_str}]"
            self.info_label.setText(info)
            self.info_label.setStyleSheet("color: green;")
            
            # 콘솔 출력
            print(f"\n📸 Visual Prompt 레퍼런스 로드:")
            for i, prompt in enumerate(self.prompts):
                img_name = Path(prompt['image_path']).stem
                print(f"   [{i}] {img_name}: {len(prompt['bboxes'])}개 객체 (클래스: {set(prompt['cls'])})")
            
            # 시그널 발생
            self.visual_prompts_loaded.emit(self.prompts)
        else:
            self.info_label.setText("⚠️ 유효한 레퍼런스 없음")
            self.info_label.setStyleSheet("color: orange;")
    
    def _load_single_image(self, image_path):
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
            return bboxes, cls
            
        except Exception as e:
            print(f"❌ Label 파싱 실패: {e}")
            return None, None
    
    def get_prompts(self):
        """모든 visual prompts 반환"""
        return self.prompts

