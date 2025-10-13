#coding=utf-8
"""
추론 워커 스레드
메인 스레드를 블로킹하지 않고 백그라운드에서 YOLO 추론 수행
"""
import time
import numpy as np
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker


class InferenceWorker(QThread):
    """
    비동기 추론 워커
    
    메인 스레드를 블로킹하지 않고 백그라운드에서 YOLO 추론 수행
    """
    
    # 시그널
    result_ready = Signal(object, dict)  # (QImage, stats)
    
    def __init__(self, inference_engine):
        """
        Args:
            inference_engine: InferenceEngine 인스턴스
        """
        super().__init__()
        self.inference_engine = inference_engine
        
        # 프레임 큐 (최신 프레임만 유지)
        self.current_frame = None
        self.frame_mutex = QMutex()
        
        # 실행 제어
        self.running = False
        self.processing = False
    
    def submit_frame(self, frame_bgr):
        """
        새 프레임 제출 (항상 최신 프레임으로 덮어씀)
        
        Args:
            frame_bgr: BGR 포맷 프레임
        """
        with QMutexLocker(self.frame_mutex):
            self.current_frame = frame_bgr
    
    def run(self):
        """워커 스레드 메인 루프"""
        self.running = True
        
        while self.running:
            # 프레임 가져오기
            frame = None
            with QMutexLocker(self.frame_mutex):
                if self.current_frame is not None:
                    frame = self.current_frame
                    self.current_frame = None
            
            # 프레임이 있으면 추론
            if frame is not None:
                self.processing = True
                try:
                    q_image, stats = self.inference_engine.process_frame(frame)
                    self.result_ready.emit(q_image, stats)
                except Exception as e:
                    print(f"⚠️ 추론 오류: {e}")
                finally:
                    self.processing = False
            else:
                # 프레임이 없으면 잠시 대기
                self.msleep(1)
    
    def stop(self):
        """워커 중지"""
        self.running = False
        self.wait(2000)  # 최대 2초 대기

