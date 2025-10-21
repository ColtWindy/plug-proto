#coding=utf-8
"""
QOpenGLWindow 기반 카메라 애플리케이션
frameSwapped 콜백을 사용하여 프레임 드랍 방지
wp_presentation 프로토콜로 정확한 프레임 표시 추적
"""
import sys
import os
import time
import threading
import cv2
import numpy as np
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSizePolicy
from PySide6.QtOpenGL import QOpenGLWindow
from PySide6.QtGui import QSurfaceFormat, QPainter, QFont, QColor, QPen, QPixmap, QImage
from PySide6.QtCore import Qt, QDateTime
from OpenGL import GL
from opengl_example.camera_controller import OpenGLCameraController
from _lib import mvsdk
from _lib.wayland_utils import setup_wayland_environment
from _native.wayland_presentation import WaylandPresentationMonitor
from config import CAMERA_IP
from yolo.inference.model_manager import ModelManager
from yolo.inference.engine import InferenceEngine
from yolo.inference.config import EngineConfig
from ps.yolo_renderer import CustomYOLORenderer

class PresentationMonitor:
    """C++ wp_presentation 헬퍼 기반 프레임 표시 추적"""
    
    def __init__(self, window):
        self.win = window
        self.frame_count = 0
        
        # C++ 모니터 생성
        self.monitor = WaylandPresentationMonitor()
        
        # 콜백 등록
        self.monitor.set_callback(self._on_feedback)
        
        print("✅ WaylandPresentationMonitor (C++) 초기화 완료")
    
    def _on_feedback(self, feedback):
        """C++에서 전달된 피드백 처리 - 프레임 스킵 시에만 로그"""
        if not feedback.presented:
            # discarded (스킵) 발생 시에만 출력
            self._log("PRESENTATION", f"📊 프레임 폐기 기록됨 (Wayland/GPU 스킵 감지됨)")
    
    def request_feedback(self):
        """정상 프레임 통계 업데이트"""
        self.frame_count += 1
        timestamp_ns = int(time.time() * 1_000_000_000)
        flags = 0x1  # VSYNC
        self.monitor.simulate_presented(timestamp_ns, self.frame_count, flags)
    
    @property
    def presented_count(self):
        return self.monitor.presented_count()
    
    @property
    def discarded_count(self):
        return self.monitor.discarded_count()
    
    @property
    def vsync_synced_count(self):
        return self.monitor.vsync_count()
    
    @property
    def zero_copy_count(self):
        return self.monitor.zero_copy_count()
    
    @property
    def last_seq(self):
        seq = self.monitor.last_sequence()
        return seq if seq > 0 else None
    
    @property
    def last_timestamp_ns(self):
        return self.monitor.last_timestamp_ns()
    
    def _log(self, level, msg):
        ts = QDateTime.currentDateTime().toString("hh:mm:ss.zzz")
        print(f"[{ts}] [{level}] {msg}")


class FrameMonitor:
    """GPU 하드웨어 레벨 프레임 검출"""
    
    def __init__(self, window):
        self.win = window
        self.last_fence = None
        self.gpu_backlog_count = 0
        self.last_backlog_detected = False  # 이번 프레임에 backlog 발생했는지
    
    def begin_frame(self):
        """paintGL 시작 직전 - GPU 백로그 검사"""
        self.last_backlog_detected = False
        
        if self.last_fence:
            status = GL.glClientWaitSync(self.last_fence, 0, 0)
            if status == GL.GL_TIMEOUT_EXPIRED:
                self.gpu_backlog_count += 1
                self.last_backlog_detected = True
                self._log("GPU_BLOCK", "🚨 GPU 블록 - 이전 프레임 미완료 (실제 감지)")
            GL.glDeleteSync(self.last_fence)
            self.last_fence = None
    
    def end_frame(self):
        """paintGL 끝 직후 - GPU fence 설정"""
        self.last_fence = GL.glFenceSync(GL.GL_SYNC_GPU_COMMANDS_COMPLETE, 0)
    
    def _log(self, level, msg):
        ts = QDateTime.currentDateTime().toString("hh:mm:ss.zzz")
        print(f"[{ts}] [{level}] {msg}")


class CameraOpenGLWindow(QOpenGLWindow):
    """카메라 화면을 표시하는 OpenGL 윈도우 (VSync 동기화)"""
    
    def __init__(self, parent_window=None, inference_engine=None, yolo_renderer=None):
        super().__init__()
        self.setTitle("OpenGL Camera - VSync + YOLO")
        self.current_pixmap = None
        self.pending_pixmap = None
        self.current_frame_bgr = None  # YOLO 추론용 원본 프레임
        self._frame = 0
        self.show_black = True  # True: 검은 화면, False: 카메라 화면
        self.parent_window = parent_window
        self.inference_engine = inference_engine
        self.yolo_renderer = yolo_renderer
        
        # 스케일 캐시 (성능 최적화)
        self._scaled_cache = None
        self._cache_key = None  # (pixmap.cacheKey(), w, h)
        
        # 텍스트 렌더링 캐시
        self._info_font = QFont("Monospace", 8)  # 작게 변경
        self._info_pen = QPen(QColor(0, 255, 0))
        
        # 프레임 모니터 (GPU 하드웨어 레벨 검출)
        self.monitor = FrameMonitor(self)
        self.presentation = None  # initializeGL에서 초기화
        
        # YOLO 통계
        self.last_infer_time = 0.0
        self.avg_infer_time = 0.0
        self.detected_count = 0
        
        # Wayland 프레임 스킵 감지
        self._last_swap_time = None
        self._expected_frame_time_ms = 16.67  # 60Hz 기준
        
        # frameSwapped 시그널을 사용하여 vsync 기반 프레임 업데이트
        self.frameSwapped.connect(self.on_frame_swapped, Qt.QueuedConnection)

    def _init_presentation(self):
        """Presentation 모니터 초기화 (한 번만 실행)"""
        if self.presentation is None:
            self.presentation = PresentationMonitor(self)
    
    def initializeGL(self):
        """OpenGL 초기화"""
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glDisable(GL.GL_DEPTH_TEST)  # 깊이 테스트 비활성화
        
        # Wayland presentation 모니터 초기화
        self._init_presentation()
    
    def resizeGL(self, w, h):
        """윈도우 크기 변경 처리"""
        GL.glViewport(0, 0, w, h)

    def paintGL(self):
        """
        프레임 렌더링
        frameSwapped 시그널에 의해 vsync와 동기화되어 호출됨
        검은 화면과 카메라 화면을 교대로 표시
        """
        # Presentation 초기화 (initializeGL 전에 paintGL이 호출될 수 있음)
        self._init_presentation()
        
        self.monitor.begin_frame()  # 모니터링 시작 (GPU fence 체크)
        
        # 배경 클리어
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        
        w = self.width()
        h = self.height()
        
        if self.show_black:
            # 검은 화면 - 텍스트만 표시 (작게)
            painter = QPainter(self)
            painter.setFont(self._info_font)
            painter.setPen(self._info_pen)
            
            # Presentation 정보
            seq_str = f"{self.presentation.last_seq}" if self.presentation.last_seq is not None else "N/A"
            pres_info = f" | Seq: {seq_str}"
            pres_info += f" | P:{self.presentation.presented_count} D:{self.presentation.discarded_count}"
            pres_info += f" | V:{self.presentation.vsync_synced_count} Z:{self.presentation.zero_copy_count}"
            
            info_text = f"Frame: {self._frame} | 검은화면 | GPU: {self.monitor.gpu_backlog_count}{pres_info}"
            painter.drawText(10, 15, info_text)
            painter.end()
        else:
            # 카메라 화면 - YOLO 추론 수행
            display_pixmap = None
            
            # 대기 중인 픽셀맵이 있으면 교체
            if self.pending_pixmap is not None:
                self.current_pixmap = self.pending_pixmap
                self.pending_pixmap = None
                # 캐시 무효화
                self._cache_key = None
            
            # YOLO 추론 (원본 프레임이 있을 때만)
            if self.current_frame_bgr is not None and self.inference_engine and self.yolo_renderer:
                try:
                    # 추론 수행
                    import time
                    start_time = time.time()
                    
                    if self.inference_engine.config:
                        results = self.inference_engine.model(self.current_frame_bgr, **self.inference_engine.config.to_dict())
                    else:
                        results = self.inference_engine.model(self.current_frame_bgr, verbose=False)
                    
                    infer_time = (time.time() - start_time) * 1000
                    
                    # 결과 처리
                    if self.inference_engine.is_engine:
                        result = results if not isinstance(results, list) else results[0]
                    else:
                        result = results[0] if isinstance(results, list) else results
                    
                    # 커스텀 렌더링
                    q_image = self.yolo_renderer.render(self.current_frame_bgr, result)
                    display_pixmap = QPixmap.fromImage(q_image)
                    
                    # 통계 업데이트
                    self.last_infer_time = infer_time
                    self.inference_engine._update_infer_stats(infer_time)
                    self.avg_infer_time = self.inference_engine.avg_infer_time
                    self.detected_count = len(result.boxes) if hasattr(result, 'boxes') else 0
                except Exception as e:
                    print(f"❌ YOLO 추론 실패: {e}")
                    display_pixmap = self.current_pixmap
            else:
                display_pixmap = self.current_pixmap
            
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
            
            # 이미지 표시
            if display_pixmap and not display_pixmap.isNull():
                # 스케일 캐시: 창 크기나 이미지가 바뀔 때만 스케일
                key = (display_pixmap.cacheKey(), w, h)
                if key != self._cache_key:
                    self._scaled_cache = display_pixmap.scaled(
                        w, h, 
                        Qt.KeepAspectRatio, 
                        Qt.FastTransformation  # 빠른 변환
                    )
                    self._cache_key = key
                
                # 캐시된 스케일 이미지 사용
                x = (w - self._scaled_cache.width()) // 2
                y = (h - self._scaled_cache.height()) // 2
                painter.drawPixmap(x, y, self._scaled_cache)
            
            # 프레임 정보 표시 (작게, 상단)
            painter.setFont(self._info_font)
            painter.setPen(self._info_pen)
            
            # Presentation 정보
            seq_str = f"{self.presentation.last_seq}" if self.presentation.last_seq is not None else "N/A"
            pres_info = f" | Seq: {seq_str}"
            pres_info += f" | P:{self.presentation.presented_count} D:{self.presentation.discarded_count}"
            pres_info += f" | V:{self.presentation.vsync_synced_count} Z:{self.presentation.zero_copy_count}"
            
            info_text = f"Frame: {self._frame} | GPU: {self.monitor.gpu_backlog_count}{pres_info}"
            painter.drawText(10, 15, info_text)
            
            # YOLO 추론 정보 표시 (두 번째 줄)
            if self.inference_engine:
                yolo_text = f"추론: {self.last_infer_time:.1f}ms (평균: {self.avg_infer_time:.1f}ms) | 탐지: {self.detected_count}"
                painter.drawText(10, 30, yolo_text)
            
            painter.end()
        
        self.monitor.end_frame()  # 모니터링 종료 (GPU fence 설정)
        
        # Presentation 통계 업데이트 (정상 프레임만 카운트)
        # 실제 스킵은 GPU fence와 frameSwapped 간격으로 감지됨
        if not self.monitor.last_backlog_detected:
            self.presentation.request_feedback()

    def update_camera_frame(self, q_image, frame_bgr=None):
        """카메라 프레임 업데이트 (메인 스레드에서 안전)"""
        if q_image is None or q_image.isNull():
            self.pending_pixmap = None
            self.current_frame_bgr = None
        else:
            self.pending_pixmap = QPixmap.fromImage(q_image)
            self.current_frame_bgr = frame_bgr  # YOLO 추론용 원본 프레임
    
    def on_frame_swapped(self):
        """frameSwapped 시그널 처리 - VSync 타이밍에서 카메라 트리거"""
        # 프레임 번호 증가 (vsync 호출될 때마다 증가)
        self._frame += 1
        
        # Wayland 프레임 스킵 감지 (실제 swap 간격 체크)
        current_time = time.perf_counter() * 1000  # ms
        if self._last_swap_time is not None:
            swap_interval = current_time - self._last_swap_time
            # 예상 시간의 1.5배 이상이면 프레임 스킵 발생
            if swap_interval > self._expected_frame_time_ms * 1.5:
                skipped_frames = int(swap_interval / self._expected_frame_time_ms) - 1
                self._log("WAYLAND_SKIP", 
                         f"🚨 Wayland 프레임 스킵 감지 - {skipped_frames}프레임, 간격: {swap_interval:.2f}ms (실제 감지)")
                # Presentation에 기록
                if self.presentation:
                    self.presentation.monitor.simulate_discarded()
        
        self._last_swap_time = current_time
        
        # 메인 윈도우에 VSync 프레임 신호 전달 (검은 화면일 때 트리거)
        if self.parent_window and self.show_black:
            self.parent_window.on_vsync_frame()
        
        # 다음 프레임은 반대 상태로 스위칭
        self.show_black = not self.show_black
        
        # 다음 프레임 업데이트
        self.update()
    
    def _log(self, level, msg):
        """로그 출력"""
        ts = QDateTime.currentDateTime().toString("hh:mm:ss.zzz")
        print(f"[{ts}] [{level}] {msg}")
    
    def keyPressEvent(self, event):
        """ESC 키로 종료"""
        if event.key() == Qt.Key_Escape or event.key() == Qt.Key_Q:
            self.close()


class MainWindow(QMainWindow):
    """OpenGL 카메라 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.camera_ip = CAMERA_IP
        self.camera = None
        self.exposure_time_ms = 9
        self.vsync_delay_ms = 17  # VSync 딜레이 (셔터 타이밍 조정)
        
        self.setWindowTitle("OpenGL Camera - YOLO")
        
        # YOLO 모델 초기화
        self.inference_engine, self.yolo_renderer = self._init_yolo_model()
        
        # OpenGL 윈도우 생성
        self.opengl_window = CameraOpenGLWindow(
            parent_window=self, 
            inference_engine=self.inference_engine,
            yolo_renderer=self.yolo_renderer
        )
        
        # QOpenGLWindow를 QWidget 컨테이너로 변환
        container = QWidget.createWindowContainer(self.opengl_window, self)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 메인 레이아웃
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(container, stretch=1)  # stretch로 공간 채우기
        
        # 컨트롤 패널
        self.setup_controls(main_layout)
        
        # 윈도우 크기 설정 (리사이즈 가능)
        self.resize(1024, 768)
        
        # 카메라 초기화
        self.setup_camera()
    
    def _init_yolo_model(self):
        """YOLO 모델 및 렌더러 초기화"""
        try:
            models_dir = Path(__file__).parent.parent / "yolo" / "models"
            if not models_dir.exists():
                print("⚠️ YOLO 모델 디렉토리 없음 - YOLO 비활성화")
                return None, None
            
            model_manager = ModelManager(models_dir)
            
            # .engine 파일만 검색
            engine_files = sorted(models_dir.glob("*.engine"))
            if not engine_files:
                print("⚠️ .engine 파일 없음 - YOLO 비활성화")
                return None, None
            
            model_manager.model_list = [(f.name, str(f)) for f in engine_files]
            model_manager.current_model = model_manager._load_single_model(str(engine_files[0]))
            
            # InferenceEngine 생성
            inference_config = EngineConfig()
            inference_engine = InferenceEngine(
                model_manager.current_model,
                str(engine_files[0]),
                inference_config
            )
            
            # CustomRenderer 생성
            yolo_renderer = CustomYOLORenderer(model_manager.current_model)
            
            print(f"✅ YOLO 모델 로드: {engine_files[0].name}")
            return inference_engine, yolo_renderer
        except Exception as e:
            print(f"⚠️ YOLO 초기화 실패: {e} - YOLO 비활성화")
            return None, None

    def setup_controls(self, parent_layout):
        """컨트롤 패널 설정"""
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls.setMaximumHeight(80)
        
        # 게인 슬라이더
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("Gain:"))
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setRange(0, 100)
        self.gain_slider.valueChanged.connect(self.on_gain_change)
        gain_layout.addWidget(self.gain_slider)
        self.gain_label = QLabel("0")
        gain_layout.addWidget(self.gain_label)
        controls_layout.addLayout(gain_layout)
        
        # 노출시간 슬라이더
        exposure_layout = QHBoxLayout()
        exposure_layout.addWidget(QLabel("노출시간:"))
        self.exposure_slider = QSlider(Qt.Horizontal)
        self.exposure_slider.setRange(1, 30)
        self.exposure_slider.setValue(self.exposure_time_ms)
        self.exposure_slider.valueChanged.connect(self.on_exposure_change)
        exposure_layout.addWidget(self.exposure_slider)
        self.exposure_label = QLabel(f"{self.exposure_time_ms}ms")
        exposure_layout.addWidget(self.exposure_label)
        controls_layout.addLayout(exposure_layout)
        
        # VSync 딜레이 슬라이더 (셔터 타이밍 조정)
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("셔터 딜레이:"))
        self.delay_slider = QSlider(Qt.Horizontal)
        self.delay_slider.setRange(0, 50)
        self.delay_slider.setValue(self.vsync_delay_ms)
        self.delay_slider.valueChanged.connect(self.on_delay_change)
        delay_layout.addWidget(self.delay_slider)
        self.delay_label = QLabel(f"{self.vsync_delay_ms}ms")
        delay_layout.addWidget(self.delay_label)
        controls_layout.addLayout(delay_layout)
        
        parent_layout.addWidget(controls)

    def setup_camera(self):
        """카메라 설정"""
        self.camera = OpenGLCameraController(self.camera_ip)
        success, message = self.camera.setup_camera()
        
        if not success:
            print(f"❌ 카메라 초기화 실패: {message}")
            return
        
        # 카메라 프레임 콜백 등록
        self.camera.set_frame_callback(self.on_new_camera_frame)
        
        # 초기 설정
        gain_value = self.camera.get_gain()
        self.gain_slider.setValue(int(gain_value))
        self.gain_label.setText(str(int(gain_value)))
        
        # 노출시간 설정
        exposure_us = self.exposure_time_ms * 1000
        self.camera.set_exposure_time(exposure_us)
        
        # 트리거 모드 설정
        if self.camera.hCamera:
            mvsdk.CameraSetTriggerMode(self.camera.hCamera, 1)  # 수동 트리거 모드
            # 초기 트리거 발생 (첫 프레임 캡처 시작)
            mvsdk.CameraSoftTrigger(self.camera.hCamera)
        
        print(f"✅ 카메라 연결 성공: {self.camera.camera_info['name']}")
        print(f"🎬 초기 셔터 트리거 발생")

    def on_new_camera_frame(self, q_image):
        """카메라에서 새 프레임이 도착했을 때"""
        if q_image and not q_image.isNull():
            # QImage를 BGR 프레임으로 변환 (YOLO 추론용)
            frame_bgr = self._qimage_to_bgr(q_image)
            # OpenGL 윈도우에 프레임 전달
            self.opengl_window.update_camera_frame(q_image, frame_bgr)
    
    def _qimage_to_bgr(self, q_image):
        """QImage를 BGR numpy 배열로 변환"""
        try:
            width = q_image.width()
            height = q_image.height()
            ptr = q_image.bits()
            
            # QImage는 RGB888 포맷
            arr = np.array(ptr).reshape(height, width, 3)
            # RGB → BGR 변환
            frame_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            return frame_bgr
        except Exception as e:
            print(f"⚠️ QImage to BGR 변환 실패: {e}")
            return None

    def on_gain_change(self, value):
        """게인 슬라이더 변경"""
        if self.camera:
            self.camera.set_gain(value)
        self.gain_label.setText(str(int(value)))

    def on_exposure_change(self, value):
        """노출시간 슬라이더 변경"""
        self.exposure_time_ms = value
        if self.camera:
            exposure_us = self.exposure_time_ms * 1000
            self.camera.set_exposure_time(exposure_us)
        self.exposure_label.setText(f"{value}ms")
    
    def on_delay_change(self, value):
        """VSync 딜레이 슬라이더 변경"""
        self.vsync_delay_ms = value
        self.delay_label.setText(f"{value}ms")
    
    def on_vsync_frame(self):
        """VSync 프레임 신호 처리 - 검은 화면일 때 카메라 트리거"""
        if not self.camera or not self.camera.hCamera:
            return
        
        # 검은 화면 표시 시점에 카메라 트리거
        threading.Thread(
            target=self._precise_delay_trigger,
            args=(self.vsync_delay_ms,),
            daemon=True
        ).start()
    
    def _precise_delay_trigger(self, delay_ms):
        """
        고정밀 딜레이 후 카메라 트리거
        busy-wait 방식으로 마이크로초 수준의 정확도 보장
        """
        if delay_ms > 0:
            start_time = time.perf_counter()
            target_time = start_time + (delay_ms / 1000.0)
            
            # busy-wait: 1ms 전까지는 sleep
            while time.perf_counter() < target_time - 0.001:
                time.sleep(0.0001)  # 100 마이크로초 sleep
            
            # 마지막 1ms는 busy-wait으로 정확도 보장
            while time.perf_counter() < target_time:
                pass
        
        # 정확한 시점에 트리거
        if self.camera and self.camera.hCamera:
            mvsdk.CameraSoftTrigger(self.camera.hCamera)

    def keyPressEvent(self, event):
        """ESC 또는 Q 키로 종료"""
        if event.key() == Qt.Key_Escape or event.key() == Qt.Key_Q:
            self.close()

    def closeEvent(self, event):
        """윈도우 종료 시 정리"""
        if self.camera:
            self.camera.cleanup()
        event.accept()


def main():
    """애플리케이션 진입점"""
    # Wayland 환경 설정 (SSH 접속 시)
    wayland_display, xdg_runtime_dir = setup_wayland_environment()
    
    if not wayland_display:
        print("❌ 사용 가능한 Wayland 디스플레이를 찾을 수 없습니다")
        sys.exit(1)
    
    socket_path = os.path.join(xdg_runtime_dir, wayland_display)
    if not os.path.exists(socket_path):
        print(f"❌ Wayland 소켓이 존재하지 않습니다: {socket_path}")
        sys.exit(1)
    
    print(f"✅ Wayland 디스플레이: {wayland_display}")
    print(f"✅ Wayland 소켓: {socket_path}")
    
    # Wayland EGL 플랫폼 설정 (Jetson 공식 지원)
    os.environ['QT_QPA_PLATFORM'] = 'wayland-egl'
    
    # OpenGL ES + VSync 설정 (Wayland + EGL)
    # Jetson은 OpenGL ES 3.2 + EGL + Wayland를 공식 지원
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.OpenGLES)    # EGL 사용 (GLX 대신)
    fmt.setVersion(3, 2)                              # OpenGL ES 3.2
    fmt.setSwapInterval(1)                            # vsync 활성화
    fmt.setSwapBehavior(QSurfaceFormat.DoubleBuffer)  # Double Buffer
    fmt.setDepthBufferSize(0)                         # 깊이 버퍼 비활성화 (성능 최적화)
    QSurfaceFormat.setDefaultFormat(fmt)
    
    print(f"🎨 OpenGL ES 3.2 + EGL + Wayland + VSync 설정 완료")
    print(f"📌 QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM')}")
    
    app = QApplication(sys.argv)
    
    # 카메라 IP는 config.py에서 관리됨
    window = MainWindow()
    window.show()
    
    # 초기 렌더링 트리거
    window.opengl_window.update()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

