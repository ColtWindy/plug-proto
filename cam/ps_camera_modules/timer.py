#coding=utf-8
"""
VSync 동기화 프레임 타이머 모듈

핵심 원리 (vsync_test.py 기반):
1. 절대 시간 기준점으로 누적 드리프트 방지
2. 정밀한 프레임 타이밍으로 하드웨어 VSync와 동기화
3. Qt Signal을 통한 스레드 안전 통신
"""
import time
import threading
import subprocess
import re
import os
from PySide6.QtCore import QObject, Signal

# 젯슨 디스플레이 환경 설정
os.environ['DISPLAY'] = ':0'

class VSyncFrameTimer(QObject):
    """VSync 동기화 프레임 신호 발생기"""
    
    frame_signal = Signal(int)  # 프레임 번호만 전달 (오버플로우 방지)
    
    def __init__(self, target_fps=60):
        super().__init__()
        self.target_fps = target_fps
        self.frame_interval_ns = int(1000000000.0 / target_fps)
        
        # VSync 동기화 상태
        self.start_time = 0
        self.frame_number = 0
        self.is_running = False
        
        # 하드웨어 주사율과 동기화
        self._sync_with_hardware()
    
    def _sync_with_hardware(self):
        """실제 하드웨어 주사율과 동기화"""
        try:
            result = subprocess.run(['xrandr'], capture_output=True, text=True, env={'DISPLAY': ':0'})
            for line in result.stdout.split('\n'):
                if '*' in line:
                    match = re.search(r'(\d+\.?\d*)\*', line)
                    if match:
                        hardware_fps = float(match.group(1))
                        self.frame_interval_ns = int(1000000000.0 / hardware_fps)
                        return
        except:
            pass
        # 기본값 사용
        self.frame_interval_ns = int(1000000000.0 / self.target_fps)
    
    def add_frame_callback(self, callback):
        """프레임 신호 콜백 등록 (Qt Signal 연결)"""
        self.frame_signal.connect(callback)
    
    def start(self):
        """VSync 동기화 프레임 신호 시작"""
        if self.is_running:
            return
            
        self.is_running = True
        self.start_time = time.time_ns()
        self.frame_number = 0
        
        def frame_loop():
            while self.is_running:
                self.frame_number += 1
                
                # 절대 시간 기준 다음 프레임 시점 계산 (누적 드리프트 방지)
                target_time = self.start_time + (self.frame_number * self.frame_interval_ns)
                
                # 정밀 대기
                while True:
                    current_time = time.time_ns()
                    remaining = target_time - current_time
                    
                    if remaining <= 0:
                        break
                        
                    if remaining > 1000000:  # 1ms 이상
                        time.sleep((remaining - 500000) / 1000000000.0)
                
                # 스레드 안전 프레임 신호 발생
                self.frame_signal.emit(self.frame_number)
        
        self.timer_thread = threading.Thread(target=frame_loop, daemon=True)
        self.timer_thread.start()
    
    def stop(self):
        """프레임 신호 중지"""
        self.is_running = False
