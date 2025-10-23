#coding=utf-8
"""
추론 엔진
YOLO 추론 수행 및 성능 통계 관리
"""
import time
import cv2
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt


class InferenceEngine:
    """YOLO 추론 및 통계 관리"""
    
    def __init__(self, model, model_path=None, config=None):
        """
        Args:
            model: YOLO 모델 객체
            model_path: 모델 파일 경로 (확장자 확인용)
            config: EngineConfig 또는 PTConfig 객체
        """
        self.model = model
        self.model_path = model_path
        self.is_engine = model_path and model_path.endswith('.engine') if model_path else False
        self.config = config
        self.visual_prompt = None  # visual prompt 이미지 경로
        
        # FPS 계산
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self.current_fps = 0.0
        
        # 추론 시간 통계
        self.infer_times = []
        self.last_infer_time = 0.0
        self.avg_infer_time = 0.0
    
    def process_frame(self, frame_bgr):
        """
        프레임 추론 및 시각화
        
        Args:
            frame_bgr: BGR 포맷의 입력 프레임
        
        Returns:
            (q_image, stats): 시각화된 QImage와 통계 딕셔너리
        """
        # FPS 업데이트
        self._update_fps()
        
        # YOLO 추론
        start_time = time.time()
        
        kwargs = {'verbose': False}
        if self.config:
            kwargs.update(self.config.to_dict())
        
        # Visual prompt (YOLOE) - 여러 레퍼런스 지원
        if self.visual_prompt:
            from ultralytics.models.yolo.yoloe import YOLOEVPSegPredictor
            
            # list 형태면 첫 번째 것만 사용 (또는 병합)
            if isinstance(self.visual_prompt, list):
                # 모든 레퍼런스를 병합
                all_bboxes = []
                all_cls = []
                for prompt in self.visual_prompt:
                    all_bboxes.append(prompt['bboxes'])
                    all_cls.append(prompt['cls'])
                
                # 첫 번째 이미지를 refer_image로 사용
                kwargs.update({
                    'refer_image': self.visual_prompt[0]['image_path'],
                    'visual_prompts': {
                        'bboxes': all_bboxes[0],  # 첫 번째만 사용
                        'cls': all_cls[0]
                    },
                    'predictor': YOLOEVPSegPredictor
                })
            else:
                # 단일 프롬프트
                kwargs.update({
                    'refer_image': self.visual_prompt['image_path'],
                    'visual_prompts': {
                        'bboxes': self.visual_prompt['bboxes'],
                        'cls': self.visual_prompt['cls']
                    },
                    'predictor': YOLOEVPSegPredictor
                })
        
        results = self.model(frame_bgr, **kwargs)
        infer_time = (time.time() - start_time) * 1000
        
        # 추론 시간 통계
        self._update_infer_stats(infer_time)
        
        # 결과 처리
        if self.is_engine:
            result = results if not isinstance(results, list) else results[0]
        else:
            result = results[0] if isinstance(results, list) else results
        
        # 결과 렌더링
        annotated_frame = result.plot()
        detected_count = len(result.boxes) if hasattr(result, 'boxes') else 0
        
        # BGR → RGB → QImage
        frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        q_image = self._numpy_to_qimage(frame_rgb)
        
        # 통계
        stats = {
            'fps': self.current_fps,
            'infer_time': self.last_infer_time,
            'avg_infer_time': self.avg_infer_time,
            'detected_count': detected_count,
            'frame_width': frame_bgr.shape[1],
            'frame_height': frame_bgr.shape[0]
        }
        
        return q_image, stats
    
    def reset_stats(self):
        """통계 초기화"""
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self.current_fps = 0.0
        self.infer_times = []
        self.last_infer_time = 0.0
        self.avg_infer_time = 0.0
    
    def _update_fps(self):
        """FPS 계산"""
        self.fps_frame_count += 1
        elapsed = time.time() - self.fps_start_time
        
        if elapsed >= 1.0:
            self.current_fps = self.fps_frame_count / elapsed
            self.fps_start_time = time.time()
            self.fps_frame_count = 0
    
    def _update_infer_stats(self, infer_time):
        """추론 시간 통계 업데이트"""
        self.last_infer_time = infer_time
        self.infer_times.append(infer_time)
        
        if len(self.infer_times) > 30:
            self.infer_times.pop(0)
        
        self.avg_infer_time = sum(self.infer_times) / len(self.infer_times)
    
    @staticmethod
    def _numpy_to_qimage(frame_rgb):
        """numpy 배열을 QImage로 변환"""
        height, width, channel = frame_rgb.shape
        bytes_per_line = 3 * width
        return QImage(frame_rgb.data, width, height, 
                     bytes_per_line, QImage.Format_RGB888).copy()
    
    @staticmethod
    def scale_pixmap(q_image, label_size, cache=None):
        """QImage를 레이블 크기에 맞게 스케일링"""
        pixmap = QPixmap.fromImage(q_image)
        cache_key = (label_size.width(), label_size.height(), pixmap.cacheKey())
        
        if cache and cache[0] == cache_key:
            return cache[1], cache_key
        
        scaled = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.FastTransformation)
        return scaled, cache_key


