#coding=utf-8
"""정밀 타이머 모듈"""
import sys
import os
import time

class Timer:
    """하드웨어/소프트웨어 타이머 통합 클래스"""
    
    def __init__(self):
        self.timer_module = None
        self.hw_available = False
        self._init_hardware_timer()
    
    def _init_hardware_timer(self):
        """하드웨어 타이머 초기화"""
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), '../../lib'))
            import timer_module
            self.timer_module = timer_module
            self.hw_available = True
            print("하드웨어 타이머 모듈 로드 완료")
        except ImportError:
            self.hw_available = False
            print("하드웨어 타이머 모듈을 찾을 수 없습니다. Python 타이머를 사용합니다.")
    
    def get_time(self):
        """현재 시간 반환 (ms)"""
        if self.hw_available:
            return self.timer_module.get_hardware_timer()
        else:
            return time.time() * 1000
    
    def get_diff_ms(self, start_time, end_time):
        """시간 차이 계산 (ms)"""
        if self.hw_available:
            return self.timer_module.get_timer_diff_ms(start_time, end_time)
        else:
            return end_time - start_time
    
    def is_hardware_available(self):
        """하드웨어 타이머 사용 가능 여부"""
        return self.hw_available
