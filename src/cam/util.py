#coding=utf-8
"""범용 유틸리티"""
import time
import functools

def measure_time(func):
    """함수 실행 시간을 측정하는 decorator"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            print(f"⏱️ {func.__name__} 실행시간: {execution_time_ms:.3f}ms")
    return wrapper
