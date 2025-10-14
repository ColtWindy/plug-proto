#coding=utf-8
"""
추론 설정 관리
"""
from dataclasses import dataclass


@dataclass
class EngineConfig:
    """TensorRT 엔진 추론 파라미터 (런타임 변경 가능)"""
    
    conf: float = 0.25          # confidence threshold
    iou: float = 0.7            # 값이 높을수록 더 많이 남김, 낮을수록 과감히 지움.
    max_det: int = 300          # maximum detections
    agnostic_nms: bool = False  # 클래스 구분 없이 모든 박스를 한 바구니에 넣고 NMS. 점수 높은 박스 하나만 남기고, 다른 클래스라도 많이 겹치면 제거.
    
    def to_dict(self):
        return {
            'conf': self.conf,
            'iou': self.iou,
            'max_det': self.max_det,
            'agnostic_nms': self.agnostic_nms,
            'verbose': False
        }


@dataclass
class PTConfig:
    """PyTorch 모델 추론 파라미터 (모든 옵션 사용 가능)"""
    
    conf: float = 0.25          # confidence threshold
    iou: float = 0.7            # 값이 높을수록 더 많이 남김, 낮을수록 과감히 지움.
    max_det: int = 300          # maximum detections
    agnostic_nms: bool = False  # 클래스 구분 없이 모든 박스를 한 바구니에 넣고 NMS. 점수 높은 박스 하나만 남기고, 다른 클래스라도 많이 겹치면 제거.
    imgsz: int = 640            # input image size
    augment: bool = False       # test-time augmentation
    
    def to_dict(self):
        return {
            'conf': self.conf,
            'iou': self.iou,
            'max_det': self.max_det,
            'agnostic_nms': self.agnostic_nms,
            'imgsz': self.imgsz,
            'augment': self.augment,
            'verbose': False
        }

