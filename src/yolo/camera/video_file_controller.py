#coding=utf-8
"""
비디오 파일 제어 모듈
카메라 컨트롤러와 동일한 인터페이스 제공
"""
import time
import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal, QTimer


class VideoSignals(QObject):
    """비디오 시그널"""
    frame_ready = Signal(np.ndarray)  # BGR 프레임


class VideoFileController:
    """비디오 파일 제어 클래스 (카메라 컨트롤러 인터페이스 호환)"""
    
    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = None
        self.is_running = False
        self.target_fps = 30
        
        # 시그널
        self.signals = VideoSignals()
        
        # 타이머
        self.timer = QTimer()
        self.timer.timeout.connect(self._read_frame)
        
        # 비디오 정보
        self.frame_width = 0
        self.frame_height = 0
        self.total_frames = 0
        self.video_fps = 30
    
    def initialize(self):
        """비디오 파일 초기화"""
        try:
            self.cap = cv2.VideoCapture(self.video_path)
            
            if not self.cap.isOpened():
                raise Exception(f"비디오 파일을 열 수 없습니다: {self.video_path}")
            
            # 비디오 정보
            self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            print(f"✅ 비디오: {self.video_path}")
            print(f"   해상도: {self.frame_width}x{self.frame_height}")
            print(f"   FPS: {self.video_fps:.1f}")
            print(f"   프레임 수: {self.total_frames}")
            
            return True
            
        except Exception as e:
            print(f"❌ 비디오 초기화 실패: {e}")
            raise
    
    def start_trigger(self, target_fps):
        """재생 시작"""
        self.target_fps = target_fps
        interval_ms = int(1000 / self.target_fps)
        self.timer.start(interval_ms)
        print(f"✅ 비디오 재생 시작 ({target_fps} FPS, interval={interval_ms}ms)")
    
    def _update_timer_interval(self):
        """타이머 간격 업데이트 (실행 중)"""
        if not self.timer.isActive():
            return
        
        interval_ms = int(1000 / self.target_fps)
        self.timer.stop()
        self.timer.start(interval_ms)
        print(f"⏩ 타이머 간격 업데이트: {interval_ms}ms")
    
    def stop_trigger(self):
        """재생 중지"""
        if self.timer.isActive():
            self.timer.stop()
            # Qt 이벤트 루프가 대기 중인 timeout 처리하도록 잠시 대기
            from PySide6.QtCore import QCoreApplication
            QCoreApplication.processEvents()
    
    def _read_frame(self):
        """프레임 읽기 (타이머 콜백)"""
        if not self.is_running or not self.cap:
            return
        
        try:
            ret, frame = self.cap.read()
            
            if not ret:
                # 영상 끝 - 처음으로 되감기
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            
            if ret:
                # BGR 프레임 시그널 발생
                self.signals.frame_ready.emit(frame)
                
        except Exception as e:
            print(f"⚠️ 프레임 읽기 오류: {e}")
    
    def cleanup(self):
        """리소스 정리"""
        self.is_running = False
        self.stop_trigger()
        
        if self.cap:
            try:
                self.cap.release()
            except Exception as e:
                print(f"⚠️ 비디오 해제 실패: {e}")
            self.cap = None
    
    # 카메라 컨트롤러 호환 메서드 (더미)
    def get_resolutions(self):
        """해상도 목록 (더미)"""
        return [], 0
    
    def get_exposure_range(self):
        """노출 범위 (더미)"""
        return 0, 0
    
    def get_gain_range(self):
        """게인 범위 (더미)"""
        return 0, 0
    
    def get_current_gain(self):
        """현재 게인 (더미)"""
        return 0
    
    def set_resolution(self, resolution_desc):
        """해상도 변경 (더미)"""
        pass
    
    def set_exposure(self, exposure_ms):
        """노출 설정 (더미)"""
        pass
    
    def set_gain(self, gain):
        """게인 설정 (더미)"""
        pass
    
    def set_manual_exposure(self, exposure_ms):
        """수동 노출 (더미)"""
        pass
    
    # hCamera 속성 (호환성)
    @property
    def hCamera(self):
        return self.cap

