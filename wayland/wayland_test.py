#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pywayland를 사용한 실제 VSync 구현 - 시뮬레이션 절대 금지
실제 디스플레이 refresh에 동기화된 프레임 콜백만 사용
"""

import time
import sys
import os
import tempfile
import mmap
from pywayland.client import Display
from pywayland.protocol.wayland import WlCompositor, WlShm, WlSurface, WlRegistry, WlShell, WlOutput
from pywayland.protocol.xdg_shell import XdgWmBase, XdgSurface, XdgToplevel


class WaylandVSync:
    def __init__(self):
        self.display = None
        self.registry = None
        self.compositor = None
        self.shm = None
        self.shell = None
        self.output = None
        self.xdg_wm_base = None
        self.surface = None
        self.shell_surface = None
        self.xdg_surface = None
        self.xdg_toplevel = None
        self.configured = False
        self.buffer = None
        self.pool = None
        self.fd = None
        self.data = None
        
        self.frame_count = 0
        self.start_time = 0
        self.frame_times = []
        self.running = True
        self.last_frame_time = 0
        self.pending_frame = None
        
        # 화면 크기 - 최대 성능을 위해 최소화
        self.width = 320
        self.height = 240
    
    def connect(self):
        """Wayland 연결"""
        try:
            wayland_display = os.getenv('WAYLAND_DISPLAY')
            self.display = Display(wayland_display) if wayland_display else Display()
            print("✓ Display 객체 생성됨")
            
            if not hasattr(self.display, '_ptr') or self.display._ptr is None:
                self.display.connect()
                print("✓ Wayland 서버에 연결됨")
            
            if not hasattr(self.display, '_ptr') or self.display._ptr is None:
                raise RuntimeError("Wayland 서버 연결 실패")
            
            self.registry = self.display.get_registry()
            self.registry.dispatcher["global"] = self._handle_global
            
            self.display.dispatch(block=True)
            self.display.roundtrip()
            
            if not self.compositor or not self.shm:
                raise RuntimeError("필수 Wayland 인터페이스를 찾을 수 없습니다")
            
            print("✓ Wayland 연결 및 초기화 완료")
            return True
            
        except Exception as e:
            print(f"✗ Wayland 연결 실패: {e}")
            raise
    
    def _handle_global(self, registry, id_, interface, version):
        """글로벌 객체 핸들러"""
        try:
            if interface == "wl_compositor":
                self.compositor = registry.bind(id_, WlCompositor, min(4, version))
                print(f"✓ Compositor 바인딩됨")
            elif interface == "wl_shm":
                self.shm = registry.bind(id_, WlShm, 1)
                print(f"✓ SHM 바인딩됨")
            elif interface == "wl_shell":
                self.shell = registry.bind(id_, WlShell, 1)
                print(f"✓ Shell 바인딩됨")
            elif interface == "wl_output":
                self.output = registry.bind(id_, WlOutput, min(2, version))
                # Output 이벤트 핸들러 등록
                self.output.dispatcher["mode"] = self._output_mode
                self.output.dispatcher["done"] = self._output_done
                print(f"✓ Output 바인딩됨")
            elif interface == "xdg_wm_base":
                self.xdg_wm_base = registry.bind(id_, XdgWmBase, 1)
                # ping/pong 핸들러 (필수)
                self.xdg_wm_base.dispatcher["ping"] = lambda base, serial: self.xdg_wm_base.pong(serial)
                print(f"✓ xdg_wm_base 바인딩됨")
        except Exception as e:
            print(f"✗ 바인딩 실패 ({interface}): {e}")
    
    def _output_mode(self, output, flags, width, height, refresh):
        """Output 모드 정보"""
        if flags & 0x1:  # WL_OUTPUT_MODE_CURRENT
            refresh_hz = refresh / 1000.0
            print(f"✓ 디스플레이: {width}x{height}@{refresh_hz:.1f}Hz")
            self.display_refresh_rate = refresh_hz
    
    def _output_done(self, output):
        """Output 설정 완료"""
        print("✓ Output 설정 완료")
    
    def create_surface(self):
        """표면 생성 - xdg-shell 사용"""
        self.surface = self.compositor.create_surface()
        print("✓ Surface 생성됨")
        
        if not self.xdg_wm_base:
            raise RuntimeError("xdg_wm_base가 필요합니다 (wl_shell 대신 xdg-shell 사용)")
        
        # xdg-surface / toplevel 생성
        self.xdg_surface = self.xdg_wm_base.get_xdg_surface(self.surface)
        self.xdg_toplevel = self.xdg_surface.get_toplevel()
        self.xdg_toplevel.set_title("VSync Test (xdg-shell)")
        
        # configure 이벤트 등록
        self.xdg_surface.dispatcher["configure"] = self._on_xdg_configure
        self.xdg_toplevel.dispatcher["configure"] = lambda top, w, h, states: None
        self.xdg_toplevel.dispatcher["close"] = lambda top: setattr(self, "running", False)
        
        # 첫 configure를 받기 위한 빈 커밋
        self.surface.commit()
        self.display.flush()
        print("✓ xdg-surface 요청, 첫 커밋 완료 (configure 대기)")
    
    def _on_xdg_configure(self, xdg_surface, serial):
        """xdg configure 이벤트 - 실제 화면 표시 시작점"""
        # compositor에게 설정 수락 통지
        self.xdg_surface.ack_configure(serial)
        print(f"✓ configure 수신 (serial: {serial})")
        
        if not self.configured:
            self.configured = True
            # 최초 한 번: 버퍼 준비 + 첫 프레임 콜백 비동기 체인 시작
            self.draw_frame()
            self.commit_frame()  # 여기서 request_frame_callback() 포함
            print("✓ configure 수신 → 첫 프레임 커밋 (VSync 체인 시작)")
    
    def create_buffer(self):
        """버퍼 생성"""
        stride = self.width * 4
        size = stride * self.height
        
        self.fd = tempfile.TemporaryFile()
        self.fd.write(b'\x00' * size)
        self.fd.flush()
        
        self.pool = self.shm.create_pool(self.fd.fileno(), size)
        # SHM 포맷을 enum으로 사용
        self.buffer = self.pool.create_buffer(0, self.width, self.height, stride, WlShm.format.argb8888.value)
        self.data = mmap.mmap(self.fd.fileno(), size)
        
        print("✓ Buffer 생성됨")
    
    def draw_frame(self):
        """프레임 그리기 - 최적화됨"""
        if not self.data:
            return
        
        # 최소한의 색상 변화 - 성능 최적화
        color = (self.frame_count & 0xFF)  # 비트 연산으로 최적화
        
        # 메모리 블록 단위로 빠르게 채우기
        pixel_data = bytes([color, 0, 0, 255]) * (len(self.data) // 4)
        self.data[:len(pixel_data)] = pixel_data
    
    def request_frame_callback(self):
        """실제 VSync 프레임 콜백 요청"""
        if not self.surface:
            return
        
        # 실제 디스플레이 refresh에 동기화된 콜백
        callback = self.surface.frame()
        callback.dispatcher["done"] = self._on_frame_done
        self.pending_frame = callback
        return callback
    
    def _on_frame_done(self, callback, time_ms):
        """실제 VSync 완료 콜백 - 디스플레이가 실제로 refresh되었을 때 호출됨"""
        current_time = time_ms / 1000.0
        
        # 프레임 시간 계산 (실제 디스플레이 refresh 간격)
        if self.frame_count > 0 and hasattr(self, 'last_frame_time'):
            frame_time = (current_time - self.last_frame_time) * 1000
            self.frame_times.append(frame_time)
            
            if self.frame_count % 10 == 0:
                fps = 1000.0 / frame_time if frame_time > 0 else 0
                print(f"Frame #{self.frame_count:3d}: {frame_time:6.2f}ms, {fps:5.1f}fps (실제 VSync)")
        
        self.last_frame_time = current_time
        self.frame_count += 1
        self.pending_frame = None
        
        # 다음 프레임 준비 (1000프레임까지 - 최대 성능 테스트)
        if self.running and self.frame_count < 1000:
            self.draw_frame()
            self.commit_frame()
        else:
            self.running = False
            print("테스트 완료 - 1000프레임 도달")
    
    def commit_frame(self):
        """프레임 커밋 - 올바른 순서 보장"""
        if not self.surface or not self.configured:
            return
        
        # 1. VSync 콜백 요청 (디스플레이 refresh에 동기화)
        self.request_frame_callback()
        
        # 2. 버퍼 첨부
        if self.buffer:
            self.surface.attach(self.buffer, 0, 0)
            self.surface.damage(0, 0, self.width, self.height)
        
        # 3. 커밋
        self.surface.commit()
        
        # 4. 즉시 플러시
        self.display.flush()
    
    def run_vsync_test(self):
        """실제 VSync 테스트 - configure 대기 후 콜백 기반"""
        print("\n실제 VSync 테스트 시작 - xdg-shell configure 대기")
        print("(프레임 콜백만 사용, 시뮬레이션 절대 없음)")
        
        self.start_time = time.time()
        self.frame_count = 0
        self.frame_times = []
        
        # configure 이벤트 대기 및 VSync 콜백 처리
        try:
            max_time = 15  # 최대 15초
            configure_timeout = 5  # configure 대기 5초
            
            print("configure 이벤트 대기 중...")
            
            while self.running:
                # 블로킹 방식으로 이벤트 처리 (더 자연스러움)
                result = self.display.dispatch(block=True)
                
                if result <= 0:
                    print("디스플레이 연결 끊어짐")
                    break
                
                # configure 받으면 VSync 체인이 자동으로 시작됨
                if self.configured and self.frame_count >= 1000:
                    print("테스트 완료 - 1000프레임 도달")
                    break
                
                # configure 없이 너무 오래 대기
                elapsed = time.time() - self.start_time
                if not self.configured and elapsed > configure_timeout:
                    print(f"{configure_timeout}초간 configure 없음 - xdg-shell 문제")
                    break
                
                # 최대 시간 초과
                if elapsed > max_time:
                    print("최대 시간 초과 - 종료")
                    break
                
        except KeyboardInterrupt:
            print("\n사용자에 의해 중단됨")
            self.running = False
        
        self._print_results()
    
    def _print_results(self):
        """결과 출력"""
        elapsed = time.time() - self.start_time
        
        print(f"\n=== 실제 VSync 테스트 결과 ===")
        print(f"총 프레임: {self.frame_count}")
        print(f"측정된 프레임: {len(self.frame_times)}")
        print(f"경과 시간: {elapsed:.2f}초")
        
        if self.frame_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            avg_fps = len(self.frame_times) / elapsed if elapsed > 0 else 0
            min_time = min(self.frame_times)
            max_time = max(self.frame_times)
            
            print(f"실제 디스플레이 refresh 기준:")
            print(f"  평균 FPS: {avg_fps:.2f}")
            print(f"  평균 프레임 시간: {avg_frame_time:.2f}ms")
            print(f"  최소 프레임 시간: {min_time:.2f}ms")
            print(f"  최대 프레임 시간: {max_time:.2f}ms")
            
            # 실제 디스플레이 refresh rate 추정
            if avg_frame_time > 0:
                estimated_refresh = 1000.0 / avg_frame_time
                print(f"  추정 디스플레이 refresh rate: {estimated_refresh:.1f}Hz")
            
            # VSync 안정성
            std_dev = (sum((t - avg_frame_time) ** 2 for t in self.frame_times) / len(self.frame_times)) ** 0.5
            print(f"  프레임 시간 편차: {std_dev:.2f}ms")
            print(f"  VSync 안정성: {'매우 양호' if std_dev < 1.0 else '양호' if std_dev < 2.0 else '불안정'}")
        else:
            print("❌ VSync 콜백이 호출되지 않았습니다")
            print("   디스플레이가 실제로 화면에 표시되지 않는 환경일 수 있습니다")
    
    def cleanup(self):
        """리소스 정리"""
        try:
            if self.data:
                self.data.close()
            if self.pool:
                self.pool.destroy()
            if self.fd:
                self.fd.close()
            if self.display:
                self.display.disconnect()
            print("✓ 리소스 정리 완료")
        except Exception as e:
            print(f"정리 중 오류: {e}")


def setup_wayland_environment():
    """Wayland 환경 자동 설정"""
    xdg_runtime_dir = os.getenv('XDG_RUNTIME_DIR')
    if not xdg_runtime_dir:
        user_id = os.getuid() if hasattr(os, 'getuid') else 1000
        xdg_runtime_dir = f"/run/user/{user_id}"
        os.environ['XDG_RUNTIME_DIR'] = xdg_runtime_dir
        print(f"XDG_RUNTIME_DIR 자동 설정: {xdg_runtime_dir}")
    
    wayland_display = os.getenv('WAYLAND_DISPLAY')
    if not wayland_display:
        possible_displays = ['wayland-0', 'wayland-1', 'weston-wayland-0', 'weston-wayland-1']
        
        for display_name in possible_displays:
            socket_path = os.path.join(xdg_runtime_dir, display_name)
            if os.path.exists(socket_path):
                os.environ['WAYLAND_DISPLAY'] = display_name
                wayland_display = display_name
                print(f"WAYLAND_DISPLAY 자동 설정: {display_name}")
                break
    
    return wayland_display, xdg_runtime_dir


def main():
    print("🚀 실제 Wayland VSync 테스트 (시뮬레이션 절대 금지)")
    print("=" * 60)
    
    wayland_display, xdg_runtime_dir = setup_wayland_environment()
    
    if not wayland_display:
        print("❌ 사용 가능한 Wayland 디스플레이를 찾을 수 없습니다")
        return 1
    
    socket_path = os.path.join(xdg_runtime_dir, wayland_display)
    if not os.path.exists(socket_path):
        print(f"❌ Wayland 소켓이 존재하지 않습니다: {socket_path}")
        return 1
    
    print(f"✓ WAYLAND_DISPLAY: {wayland_display}")
    print(f"✓ 소켓 경로: {socket_path}")
    
    vsync = WaylandVSync()
    
    try:
        vsync.connect()
        vsync.create_surface()
        vsync.create_buffer()
        vsync.run_vsync_test()
        
        print("\n🎉 실제 VSync 테스트 완료")
        return 0
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        vsync.cleanup()


if __name__ == "__main__":
    sys.exit(main())