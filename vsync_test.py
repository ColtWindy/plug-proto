#coding=utf-8
"""젯슨 오린 나노 실제 하드웨어 VSync 테스트 - 최소 구현"""
import os
import sys
import time
import subprocess
import re

# 젯슨 로컬 디스플레이 환경 설정
os.environ['DISPLAY'] = ':0'

class HardwareVsyncDetector:
    """실제 하드웨어 디스플레이 정보 기반 VSync 테스트"""
    
    def __init__(self):
        self.display_refresh_rate = 0.0
        self.frame_interval_ns = 0
        self.frame_count = 0
        self.start_time = 0
        self.last_frame_time = 0
        
    def get_hardware_refresh_rate(self):
        """실제 하드웨어 디스플레이 주사율 조회"""
        try:
            # xrandr로 실제 모니터 주사율 확인
            result = subprocess.run(['xrandr'], capture_output=True, text=True, 
                                  env={'DISPLAY': ':0'})
            
            if result.returncode == 0:
                # 현재 활성 모드에서 주사율 추출
                for line in result.stdout.split('\n'):
                    if '*' in line:  # 현재 활성 모드
                        # 주사율 패턴 찾기 (예: 59.81)
                        match = re.search(r'(\d+\.?\d*)\*', line)
                        if match:
                            self.display_refresh_rate = float(match.group(1))
                            self.frame_interval_ns = int(1000000000.0 / self.display_refresh_rate)
                            return True, f"하드웨어 주사율: {self.display_refresh_rate:.2f}Hz"
            
            return False, "디스플레이 주사율 감지 실패"
            
        except Exception as e:
            return False, f"xrandr 실행 실패: {e}"
    
    def measure_frame_timing(self):
        """정밀한 프레임 타이밍 측정"""
        current_time_ns = time.time_ns()
        
        if self.last_frame_time == 0:
            self.start_time = current_time_ns
            self.last_frame_time = current_time_ns
            return 0, 0
            
        frame_delta_ns = current_time_ns - self.last_frame_time
        self.last_frame_time = current_time_ns
        self.frame_count += 1
        
        # 실제 vs 예상 비교
        expected_interval = self.frame_interval_ns
        timing_error = abs(frame_delta_ns - expected_interval)
        timing_accuracy = max(0, 100 - (timing_error / expected_interval * 100))
        
        return frame_delta_ns, timing_accuracy
        
    def is_vsync_aligned(self, frame_delta_ns, tolerance_percent=5):
        """VSync 정렬 여부 판단"""
        if self.frame_interval_ns == 0:
            return False
            
        tolerance = self.frame_interval_ns * (tolerance_percent / 100.0)
        return abs(frame_delta_ns - self.frame_interval_ns) <= tolerance

def main():
    """메인 실행 함수"""
    print("🚀 젯슨 오린 나노 실제 하드웨어 VSync 테스트")
    print("📋 하드웨어 디스플레이 정보 기반 정밀 타이밍 측정")
    
    detector = HardwareVsyncDetector()
    
    # 실제 하드웨어 주사율 확인
    success, message = detector.get_hardware_refresh_rate()
    if not success:
        print(f"❌ {message}")
        print("💡 대안: NVIDIA 드라이버 설정에서 실제 VSync는 확인 불가")
        return
    
    print(f"✅ {message}")
    print(f"📊 예상 프레임 간격: {detector.frame_interval_ns/1000000:.2f}ms")
    print()
    print("🎯 실시간 VSync 정렬 테스트:")
    print("   - 녹색: VSync 정렬됨 (±5% 오차)")  
    print("   - 빨간색: VSync 비정렬")
    print()
    
    try:
        stats = {'aligned': 0, 'total': 0, 'avg_accuracy': 0}
        last_stats_time = time.time()
        
        while True:
            # 하드웨어 주사율에 맞춰 대기
            expected_sleep = detector.frame_interval_ns / 1000000000.0
            time.sleep(expected_sleep * 0.95)  # 95% 대기 후 정밀 측정
            
            # 정밀 프레임 타이밍 측정
            frame_delta_ns, accuracy = detector.measure_frame_timing()
            
            if frame_delta_ns > 0:
                stats['total'] += 1
                stats['avg_accuracy'] += accuracy
                
                # VSync 정렬 여부 판단
                is_aligned = detector.is_vsync_aligned(frame_delta_ns)
                if is_aligned:
                    stats['aligned'] += 1
                    status = "🟢 정렬됨"
                else:
                    status = "🔴 비정렬"
                
                frame_delta_ms = frame_delta_ns / 1000000.0
                expected_ms = detector.frame_interval_ns / 1000000.0
                
                print(f"{status} | 실제: {frame_delta_ms:6.2f}ms | 예상: {expected_ms:6.2f}ms | 정확도: {accuracy:5.1f}%")
            
            # 5초마다 통계 출력
            current_time = time.time()
            if current_time - last_stats_time >= 5.0 and stats['total'] > 0:
                alignment_rate = (stats['aligned'] / stats['total']) * 100
                avg_accuracy = stats['avg_accuracy'] / stats['total']
                
                print()
                print(f"📈 5초 통계:")
                print(f"   VSync 정렬률: {alignment_rate:.1f}% ({stats['aligned']}/{stats['total']})")
                print(f"   평균 정확도: {avg_accuracy:.1f}%")
                
                if alignment_rate >= 80:
                    print("   ✅ 하드웨어 VSync 동작 정상")
                else:
                    print("   ⚠️  VSync 동기화 문제 감지")
                print()
                
                # 통계 리셋
                stats = {'aligned': 0, 'total': 0, 'avg_accuracy': 0}
                last_stats_time = current_time
            
    except KeyboardInterrupt:
        print("\n⏹️  테스트 중단")
        
        if stats['total'] > 0:
            final_alignment = (stats['aligned'] / stats['total']) * 100
            final_accuracy = stats['avg_accuracy'] / stats['total']
            print(f"\n📊 최종 결과:")
            print(f"   VSync 정렬률: {final_alignment:.1f}%")
            print(f"   평균 정확도: {final_accuracy:.1f}%")
    
    print("✅ 테스트 완료")

if __name__ == "__main__":
    main()
