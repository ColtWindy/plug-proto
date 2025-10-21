#coding=utf-8
"""
커스텀 YOLO 렌더러
바운딩 박스 + 중앙 도형 시각화
"""
import cv2
import numpy as np
from PySide6.QtGui import QImage


class CustomYOLORenderer:
    """커스텀 YOLO 탐지 결과 렌더러"""
    
    def __init__(self, model):
        """
        Args:
            model: YOLO 모델 객체 (names 속성 필요)
        """
        self.model = model
        self.draw_boxes = True  # 바운딩 박스/라벨 표시 여부
        self.draw_camera_feed = True  # 촬영화면 표시 여부
    
    def render(self, frame_bgr, result):
        """
        YOLO 결과를 커스텀 시각화
        
        Args:
            frame_bgr: BGR 포맷 원본 프레임
            result: YOLO 추론 결과
        
        Returns:
            QImage: 시각화된 QImage
        """
        if not hasattr(result, 'boxes') or len(result.boxes) == 0:
            # 탐지 결과 없으면 원본 또는 검은 배경 반환
            if self.draw_camera_feed:
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            else:
                # 검은 배경
                frame_rgb = np.zeros_like(frame_bgr)
            return self._numpy_to_qimage(frame_rgb)
        
        # 촬영화면 또는 검은 배경
        if self.draw_camera_feed:
            annotated = frame_bgr.copy()
        else:
            # 검은 배경 생성
            annotated = np.zeros_like(frame_bgr)
        
        # 각 탐지 결과 그리기
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            
            # 클래스명 및 색상
            class_name = self.model.names[cls] if hasattr(self.model, 'names') else f"class_{cls}"
            color = self._get_class_color(cls)
            
            # 바운딩 박스 및 라벨 (옵션)
            if self.draw_boxes:
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                
                label = f"{class_name} {conf:.2f}"
                (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(annotated, (x1, y1 - label_h - 4), (x1 + label_w, y1), color, -1)
                cv2.putText(annotated, label, (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # 중앙 도형 (항상 표시)
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            size = min(x2 - x1, y2 - y1) // 3
            self._draw_shape(annotated, cls, cx, cy, size, color)
        
        # BGR → RGB → QImage
        frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        return self._numpy_to_qimage(frame_rgb)
    
    @staticmethod
    def _get_class_color(cls):
        """클래스별 고유 색상 (HSV 기반)"""
        hue = (cls * 47) % 180
        hsv = np.uint8([[[hue, 255, 255]]])
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0]
        return tuple(map(int, bgr))
    
    @staticmethod
    def _draw_shape(frame, cls, cx, cy, size, color):
        """클래스별 도형 그리기 (원, 삼각형, 사각형 - 채워짐)"""
        shape_type = cls % 3
        
        if shape_type == 0:  # 원
            cv2.circle(frame, (cx, cy), size, color, -1)
        elif shape_type == 1:  # 삼각형
            pts = np.array([
                [cx, cy - size],
                [cx - size, cy + size],
                [cx + size, cy + size]
            ], np.int32)
            cv2.fillPoly(frame, [pts], color)
        else:  # 사각형
            cv2.rectangle(frame, (cx - size, cy - size), (cx + size, cy + size), color, -1)
    
    @staticmethod
    def _numpy_to_qimage(frame_rgb):
        """numpy 배열을 QImage로 변환"""
        height, width, channel = frame_rgb.shape
        bytes_per_line = 3 * width
        return QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()

