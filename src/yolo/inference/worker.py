#coding=utf-8
"""
추론 워커 스레드
백그라운드에서 YOLO 추론 수행
"""
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker


class InferenceWorker(QThread):
    """비동기 추론 워커"""
    
    result_ready = Signal(object, dict)  # (QImage, stats)
    
    def __init__(self, inference_engine):
        super().__init__()
        self.inference_engine = inference_engine
        self.current_frame = None
        self.frame_mutex = QMutex()
        self.running = False
        self.processing = False
    
    def submit_frame(self, frame_bgr):
        """새 프레임 제출 (최신 프레임으로 덮어씀)"""
        with QMutexLocker(self.frame_mutex):
            self.current_frame = frame_bgr
    
    def run(self):
        """워커 스레드 메인 루프"""
        self.running = True
        
        while self.running:
            frame = None
            with QMutexLocker(self.frame_mutex):
                if self.current_frame is not None:
                    frame = self.current_frame
                    self.current_frame = None
            
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
                self.msleep(1)
    
    def stop(self):
        """워커 중지"""
        self.running = False
        self.wait(2000)


