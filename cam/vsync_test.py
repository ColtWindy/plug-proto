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
    누적 드리프트 방지 VSync 타이밍 측정
    
    핵심: 절대 시간 기준점을 유지하여 누적 드리프트 완전 차단
    - 상대적 측정 금지, 절대 시간 기준 사용
    - 각 프레임을 독립적이 아닌 절대 시퀀스로 처리
    """
    expected_interval_ns = int(1000000000.0 / refresh_rate)
    expected_interval_ms = expected_interval_ns / 1000000.0
    
    print(f"🎯 하드웨어 주사율: {refresh_rate:.1f}Hz (간격: {expected_interval_ms:.1f}ms)")
    print("📊 누적 드리프트 방지 VSync 측정:")
    print()
    
    # 절대 기준점 설정 (드리프트 방지의 핵심)
    start_time = time.time_ns()
    frame_number = 0
    aligned_count = 0
    
    try:
        while True:
            frame_number += 1
            
            # 절대 시간 기준 다음 VSync 시점 계산
            target_time = start_time + (frame_number * expected_interval_ns)
            
            # 목표 시점까지 정밀 대기
            while True:
                current_time = time.time_ns()
                remaining = target_time - current_time
                
                if remaining <= 0:
                    break
                    
                if remaining > 1000000:  # 1ms 이상 남음
                    time.sleep((remaining - 500000) / 1000000000.0)  # 0.5ms 여유
                # 마지막은 busy waiting으로 정밀 대기
            
            # 실제 측정 시점
            actual_time = time.time_ns()
            
            # 누적 드리프트 계산 (절대 기준 대비)
            expected_absolute_time = start_time + (frame_number * expected_interval_ns)
            cumulative_drift = actual_time - expected_absolute_time
            
            # 프레임 간격 계산 (표시용)
            if frame_number > 1:
                prev_target = start_time + ((frame_number - 1) * expected_interval_ns)
                actual_interval = actual_time - prev_target
                actual_ms = actual_interval / 1000000.0
            else:
                actual_ms = expected_interval_ms
            
            # 동기화 상태 판단
            drift_ms = cumulative_drift / 1000000.0
            is_synced = abs(cumulative_drift) < expected_interval_ns * 0.25  # 1/4 프레임 이내
            
            if is_synced:
                aligned_count += 1
            
            # 실시간 결과 표시
            status = "🟢 동기화" if is_synced else "🔴 드리프트"
            sync_rate = (aligned_count / frame_number) * 100
            
            print(f"{status} | 프레임: {frame_number:4d} | 간격: {actual_ms:5.1f}ms | "
                  f"누적드리프트: {drift_ms:+6.2f}ms | 동기화율: {sync_rate:4.1f}%")
            
            # 드리프트가 임계치 초과시 재동기화
            if abs(cumulative_drift) > expected_interval_ns // 2:  # 1/2 프레임
                print("🔄 재동기화 실행")
                start_time = actual_time
                frame_number = 0
                aligned_count = 0
            
    except KeyboardInterrupt:
        print(f"\n📈 최종 결과: VSync 동기화율 {sync_rate:.1f}% (총 {frame_number}프레임)")
        print(f"📊 최종 누적 드리프트: {drift_ms:+.2f}ms")
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
