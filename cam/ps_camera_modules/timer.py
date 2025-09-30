#coding=utf-8
"""
Wayland VSync 동기화 프레임 타이머 모듈

핵심 원리 (wayland_test.py 기반):
1. 실제 Wayland VSync 콜백 사용
2. 디스플레이 refresh에 동기화된 프레임 신호
3. Qt Signal을 통한 스레드 안전 통신
"""
import time
import threading
import tempfile
import mmap
import os
from PySide6.QtCore import QObject, Signal
from pywayland.client import Display
from pywayland.protocol.wayland import WlCompositor, WlShm, WlSurface
from pywayland.protocol.xdg_shell import XdgWmBase, XdgSurface, XdgToplevel

# 젯슨 Wayland 디스플레이 환경 설정
def setup_wayland_environment():
    """Wayland 환경 설정"""
    xdg_runtime_dir = os.getenv('XDG_RUNTIME_DIR')
    if not xdg_runtime_dir:
        user_id = os.getuid() if hasattr(os, 'getuid') else 1000
        xdg_runtime_dir = f"/run/user/{user_id}"
        os.environ['XDG_RUNTIME_DIR'] = xdg_runtime_dir
    
    wayland_display = os.getenv('WAYLAND_DISPLAY')
    if not wayland_display:
        possible_displays = ['wayland-0', 'wayland-1', 'weston-wayland-0', 'weston-wayland-1']
        
        for display_name in possible_displays:
            socket_path = os.path.join(xdg_runtime_dir, display_name)
            if os.path.exists(socket_path):
                os.environ['WAYLAND_DISPLAY'] = display_name
                wayland_display = display_name
                break
    
    return wayland_display, xdg_runtime_dir

# Wayland 환경 설정 - 에러 시 조용히 넘어감 (ps_camera.py에서 처리)
try:
    setup_wayland_environment()
except:
    pass  # 메인에서 처리하도록 함

class VSyncFrameTimer(QObject):
    """Wayland VSync 동기화 프레임 신호 발생기"""
    
    frame_signal = Signal(int)  # 프레임 번호만 전달
    
    def __init__(self):
        super().__init__()
        self.frame_number = 0
        self.is_running = False
        
        # Wayland 객체들
        self.display = None
        self.compositor = None
        self.shm = None
        self.xdg_wm_base = None
        self.surface = None
        self.xdg_surface = None
        self.xdg_toplevel = None
        self.configured = False
        self.buffer = None
        self.pool = None
        self.fd = None
        self.data = None
        self._pending_cb = None  # 콜백 객체 참조 보관
        
        # 최소 화면 크기
        self.width = 32
        self.height = 32
        
        # Wayland 연결 및 초기화
        self._init_wayland()
    
    def _init_wayland(self):
        """Wayland 연결 및 초기화"""
        try:
            print("🔧 Wayland VSync 초기화 시작")
            wayland_display = os.getenv('WAYLAND_DISPLAY')
            self.display = Display(wayland_display) if wayland_display else Display()
            
            # 연결 확인
            if not hasattr(self.display, '_ptr') or self.display._ptr is None:
                self.display.connect()
            
            if not hasattr(self.display, '_ptr') or self.display._ptr is None:
                raise RuntimeError("Wayland 서버 연결 실패")
            
            print("✓ Wayland 서버 연결됨")
            
            registry = self.display.get_registry()
            registry.dispatcher["global"] = self._handle_global
            
            self.display.dispatch(block=True)
            self.display.roundtrip()
            
            if not self.compositor or not self.shm or not self.xdg_wm_base:
                raise RuntimeError("Wayland 필수 인터페이스 없음")
            
            print("✓ Wayland 인터페이스 바인딩 완료")
            
            # 표면 및 버퍼 생성
            self._create_surface_and_buffer()
            print("✓ VSync 타이머 초기화 완료")
            
        except Exception as e:
            raise RuntimeError(f"Wayland VSync 초기화 실패: {e}")
    
    def _handle_global(self, registry, id_, interface, version):
        """Wayland 글로벌 객체 핸들러"""
        if interface == "wl_compositor":
            self.compositor = registry.bind(id_, WlCompositor, min(4, version))
        elif interface == "wl_shm":
            self.shm = registry.bind(id_, WlShm, 1)
        elif interface == "xdg_wm_base":
            self.xdg_wm_base = registry.bind(id_, XdgWmBase, 1)
            self.xdg_wm_base.dispatcher["ping"] = lambda base, serial: self.xdg_wm_base.pong(serial)
    
    def _create_surface_and_buffer(self):
        """표면과 버퍼 생성"""
        self.surface = self.compositor.create_surface()
        
        # xdg-surface 생성
        self.xdg_surface = self.xdg_wm_base.get_xdg_surface(self.surface)
        self.xdg_toplevel = self.xdg_surface.get_toplevel()
        self.xdg_toplevel.set_title("VSync Timer")
        
        # configure 이벤트 등록
        self.xdg_surface.dispatcher["configure"] = self._on_xdg_configure
        self.xdg_toplevel.dispatcher["configure"] = lambda top, w, h, states: None
        self.xdg_toplevel.dispatcher["close"] = lambda top: setattr(self, "is_running", False)
        
        # 버퍼 생성
        stride = self.width * 4
        size = stride * self.height
        
        self.fd = tempfile.TemporaryFile()
        self.fd.truncate(size)
        
        self.pool = self.shm.create_pool(self.fd.fileno(), size)
        self.buffer = self.pool.create_buffer(0, self.width, self.height, stride, WlShm.format.argb8888.value)
        self.data = mmap.mmap(self.fd.fileno(), size)
        
        # 검은 화면으로 초기화
        self.data[:] = bytes([255, 0, 0, 0]) * (self.width * self.height)
        
        # 첫 configure를 받기 위한 빈 커밋
        self.surface.commit()
        self.display.flush()
    
    def _on_xdg_configure(self, xdg_surface, serial):
        """xdg configure 이벤트"""
        self.xdg_surface.ack_configure(serial)
        
        if not self.configured:
            self.configured = True
            # configure 후 즉시 첫 프레임 커밋
            if self.is_running:
                self._commit_frame()
    
    def _request_frame_callback(self):
        """VSync 프레임 콜백 요청"""
        if not self.surface:
            return
        
        callback = self.surface.frame()
        callback.dispatcher["done"] = self._on_frame_done
        self._pending_cb = callback  # 참조 보관 (GC 방지)
        return callback
    
    def _on_frame_done(self, callback, time_ms):
        """VSync 완료 콜백 - 실제 디스플레이 refresh 시점"""
        self._pending_cb = None  # 완료 시 참조 해제
        
        if not self.is_running:
            return
        
        self.frame_number += 1
        
        # Qt Signal 발생
        self.frame_signal.emit(self.frame_number)
        
        # 다음 프레임 요청 (핵심: 버퍼 변경 포함)
        if self.is_running:
            self._commit_frame()
    
    def _draw_frame(self):
        """프레임 그리기 - wayland_test.py 방식"""
        if not self.data:
            return
        
        # 매 프레임마다 색상 변경 (VSync 콜백 유지의 핵심!)
        color = (self.frame_number & 0xFF)
        a, r, g, b = 255, color, 0, 0
        pixel = bytes([a, r, g, b])
        
        # 전체 버퍼 업데이트
        self.data[:] = pixel * (self.width * self.height)
    
    def _commit_frame(self):
        """프레임 커밋"""
        if not self.surface or not self.configured:
            return
        
        # 1. VSync 콜백 요청 (wayland_test.py 순서)
        self._request_frame_callback()
        
        # 2. 버퍼 내용 변경 (중요!)
        self._draw_frame()
        
        # 3. 버퍼 첨부 및 커밋
        self.surface.attach(self.buffer, 0, 0)
        self.surface.damage(0, 0, self.width, self.height)
        self.surface.commit()
        
        # 4. 즉시 플러시
        self.display.flush()
    
    def add_frame_callback(self, callback):
        """프레임 신호 콜백 등록"""
        self.frame_signal.connect(callback)
    
    def start(self):
        """VSync 동기화 시작"""
        if self.is_running:
            return
        
        self.is_running = True
        self.frame_number = 0
        
        # configure된 경우에만 첫 프레임 커밋
        if self.configured:
            self._commit_frame()
        
        
        # Wayland 이벤트 처리 스레드
        def wayland_loop():
            while self.is_running:
                try:
                    self.display.dispatch(block=True)
                except Exception:
                    break
        
        self.wayland_thread = threading.Thread(target=wayland_loop, daemon=True)
        self.wayland_thread.start()
    
    def stop(self):
        """VSync 동기화 중지"""
        self.is_running = False
        
        # 리소스 정리
        try:
            if self.data:
                self.data.close()
            if self.pool:
                self.pool.destroy()
            if self.fd:
                self.fd.close()
            if self.display:
                self.display.disconnect()
        except:
            pass

    def get_hardware_refresh_rate(self):
        """하드웨어 주사율 직접 가져오기"""
        from pywayland.protocol.wayland import WlOutput
        
        registry = self.display.get_registry()
        self._output = None
        
        # wl_output 찾기
        registry.dispatcher["global"] = lambda r, id_, interface, version: \
            setattr(self, '_output', r.bind(id_, WlOutput, 3)) if interface == "wl_output" else None
        self.display.roundtrip()
        
        if not self._output:
            raise RuntimeError("wl_output 인터페이스를 찾을 수 없음")
        
        # 현재 모드의 refresh rate 가져오기
        self._refresh = None
        self._output.dispatcher["mode"] = lambda o, flags, w, h, refresh: \
            setattr(self, '_refresh', refresh / 1000.0) if flags & 1 else None
        self.display.roundtrip()
        
        if not self._refresh:
            raise RuntimeError("주사율 정보를 가져올 수 없음")
        
        return self._refresh
    
