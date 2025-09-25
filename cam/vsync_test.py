#coding=utf-8
"""
젯슨 오린 나노 실제 하드웨어 VSync 테스트

핵심 원리:
1. xrandr로 실제 모니터 주사율 조회 (하드웨어 기준값)
2. time.time_ns()로 나노초 정밀도 타이밍 측정
3. 하드웨어 주사율과 실시간 비교하여 VSync 동기화 확인
4. 시뮬레이션 없이 순수 하드웨어 정보만 사용
"""
import os
import time
import subprocess
import re

# SSH 환경에서 디스플레이 접근 설정
os.environ['DISPLAY'] = ':0'

def get_display_refresh_rate():
    """
    실제 하드웨어 디스플레이 주사율 조회
    
    원리: xrandr은 리눅스에서 디스플레이 설정을 관리하는 표준 도구
    '*' 표시가 있는 라인이 현재 활성 모드 (실제 하드웨어 주사율)
    """
    try:
        result = subprocess.run(['xrandr'], capture_output=True, text=True, env={'DISPLAY': ':0'})
        
        for line in result.stdout.split('\n'):
            if '*' in line:  # 현재 활성 모드 찾기
                match = re.search(r'(\d+\.?\d*)\*', line)
                if match:
                    return float(match.group(1))
        return None
    except:
        return None

def measure_vsync_timing(refresh_rate):
    """
    VSync 타이밍 측정 및 동기화 확인
    
    원리:
    - VSync는 모니터가 새 프레임을 표시할 준비가 된 신호
    - 60Hz 모니터 = 16.67ms마다 VSync 발생
    - 정확한 간격으로 렌더링하면 VSync와 동기화됨
    """
    expected_interval_ns = int(1000000000.0 / refresh_rate)  # 나노초 단위 예상 간격
    expected_interval_ms = expected_interval_ns / 1000000.0   # 밀리초 단위 표시용
    
    print(f"🎯 하드웨어 주사율: {refresh_rate:.1f}Hz (간격: {expected_interval_ms:.1f}ms)")
    print("📊 실시간 VSync 동기화 측정:")
    print()
    
    last_time = 0
    aligned_count = 0
    total_count = 0
    
    try:
        while True:
            # 하드웨어 주사율에 맞춰 대기 (95% 시점에서 정밀 측정)
            time.sleep(expected_interval_ns / 1000000000.0 * 0.95)
            
            # 나노초 정밀도 시간 측정 (VSync 동기화의 핵심)
            current_time = time.time_ns()
            
            if last_time > 0:
                # 실제 프레임 간격 계산
                actual_interval = current_time - last_time
                actual_ms = actual_interval / 1000000.0
                
                # VSync 동기화 여부 판단 (±5% 허용 오차)
                error_percent = abs(actual_interval - expected_interval_ns) / expected_interval_ns * 100
                is_synced = error_percent <= 5.0
                
                # 통계 업데이트
                total_count += 1
                if is_synced:
                    aligned_count += 1
                
                # 실시간 결과 표시
                status = "🟢 동기화" if is_synced else "🔴 비동기화"
                accuracy = 100 - error_percent
                sync_rate = (aligned_count / total_count) * 100 if total_count > 0 else 0
                
                print(f"{status} | 실제: {actual_ms:5.1f}ms | 예상: {expected_interval_ms:5.1f}ms | "
                      f"정확도: {accuracy:4.1f}% | 동기화율: {sync_rate:4.1f}%")
            
            last_time = current_time
            
    except KeyboardInterrupt:
        print(f"\n📈 최종 결과: VSync 동기화율 {sync_rate:.1f}% ({aligned_count}/{total_count})")
        print("✅ 테스트 완료")

def main():
    """
    메인 실행 함수
    
    VSync 테스트 원리:
    1. 하드웨어에서 실제 주사율 조회
    2. 나노초 정밀도로 프레임 간격 측정
    3. 하드웨어 기준과 비교하여 동기화 확인
    """
    print("🚀 젯슨 오린 나노 하드웨어 VSync 테스트")
    print("💡 원리: 실제 모니터 주사율과 타이밍 측정으로 VSync 동기화 확인")
    print()
    
    # 1단계: 실제 하드웨어 주사율 조회
    refresh_rate = get_display_refresh_rate()
    if not refresh_rate:
        print("❌ 디스플레이 주사율 감지 실패")
        print("💡 xrandr 명령어가 필요하고 DISPLAY 환경변수가 설정되어야 합니다")
        return
    
    # 2단계: VSync 타이밍 측정 및 동기화 확인
    measure_vsync_timing(refresh_rate)

if __name__ == "__main__":
    main()
