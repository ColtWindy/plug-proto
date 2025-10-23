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

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget, 
                                QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSizePolicy)
from PySide6.QtOpenGL import QOpenGLWindow
from PySide6.QtGui import QSurfaceFormat, QPainter, QFont, QColor, QPen, QPixmap, QImage
from PySide6.QtCore import Qt
from OpenGL import GL

from opengl_example.camera_controller import OpenGLCameraController
from _lib import mvsdk
from _lib.wayland_utils import setup_wayland_environment
from config import CAMERA_IP
from yolo.inference.model_manager import ModelManager
from yolo.inference.engine import InferenceEngine
from yolo.inference.config import EngineConfig
from ps.yolo_renderer import CustomYOLORenderer


# 상수 정의
BUSY_WAIT_THRESHOLD_MS = 0.001
BUSY_WAIT_SLEEP_US = 0.0001


class CameraOpenGLWindow(QOpenGLWindow):
    """카메라 화면을 표시하는 OpenGL 윈도우 (VSync 동기화)"""
    
    def __init__(self, parent_window=None, inference_engine=None, yolo_renderer=None):
        super().__init__()
        self.setTitle("OpenGL Camera - VSync + YOLO")
        
        # 부모 윈도우 및 YOLO
        self.parent_window = parent_window
        self.inference_engine = inference_engine
        self.yolo_renderer = yolo_renderer
        
        # 프레임 데이터
        self.current_pixmap = None
        self.pending_pixmap = None
        self.current_frame_bgr = None
        self._frame = 0
        self.show_black = True
        
        # 캐시
        self._scaled_cache = None
        self._cache_key = None
        
        # UI 스타일
        self._info_font = QFont("Monospace", 8)
        self._info_pen = QPen(QColor(0, 255, 0))
        
        # YOLO 통계
        self.last_infer_time = 0.0
        self.avg_infer_time = 0.0
        self.detected_count = 0
        
        # frameSwapped 시그널 연결
        self.frameSwapped.connect(self.on_frame_swapped, Qt.QueuedConnection)
    
    def initializeGL(self):
        """OpenGL 초기화"""
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glDisable(GL.GL_DEPTH_TEST)
    
    def resizeGL(self, w, h):
        """윈도우 크기 변경 처리"""
        GL.glViewport(0, 0, w, h)

    def paintGL(self):
        """프레임 렌더링 (VSync 동기화)"""
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        
        if self.show_black:
            self._render_black_screen()
        else:
            self._render_camera_screen()
    
    def _render_black_screen(self):
        """검은 화면 렌더링"""
        painter = QPainter(self)
        painter.setFont(self._info_font)
        painter.setPen(self._info_pen)
        
        info_text = f"Frame: {self._frame} | 검은화면"
        painter.drawText(10, 15, info_text)
        painter.end()
    
    def _render_camera_screen(self):
        """카메라 화면 렌더링 + YOLO 추론"""
        # 대기 중인 프레임 처리
        self._update_pending_frame()
        
        # YOLO 추론 수행
        display_pixmap = self._perform_yolo_inference()
        
        # 화면 그리기
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        
        if display_pixmap and not display_pixmap.isNull():
            self._draw_scaled_pixmap(painter, display_pixmap)
        
        # 정보 텍스트 표시
        painter.setFont(self._info_font)
        painter.setPen(self._info_pen)
        
        info_text = f"Frame: {self._frame}"
        painter.drawText(10, 15, info_text)
        
        if self.inference_engine:
            yolo_text = f"추론: {self.last_infer_time:.1f}ms (평균: {self.avg_infer_time:.1f}ms) | 탐지: {self.detected_count}"
            painter.drawText(10, 30, yolo_text)
        
        painter.end()
    
    def _update_pending_frame(self):
        """대기 중인 프레임 업데이트"""
        if self.pending_pixmap is not None:
            self.current_pixmap = self.pending_pixmap
            self.pending_pixmap = None
            self._cache_key = None
    
    def _perform_yolo_inference(self):
        """YOLO 추론 수행"""
        if not (self.current_frame_bgr is not None and self.inference_engine and self.yolo_renderer):
            return self.current_pixmap
        
        try:
            start_time = time.time()
            
            # 추론 실행
            if self.inference_engine.config:
                results = self.inference_engine.model(
                    self.current_frame_bgr, 
                    **self.inference_engine.config.to_dict()
                )
            else:
                results = self.inference_engine.model(self.current_frame_bgr, verbose=False)
            
            infer_time = (time.time() - start_time) * 1000
            
            # 결과 처리
            result = self._extract_result(results)
            
            # 커스텀 렌더링
            q_image = self.yolo_renderer.render(self.current_frame_bgr, result)
            
            # 통계 업데이트
            self._update_yolo_stats(infer_time, result)
            
            return QPixmap.fromImage(q_image)
        except Exception as e:
            print(f"❌ YOLO 추론 실패: {e}")
            return self.current_pixmap
    
    def _extract_result(self, results):
        """추론 결과 추출"""
        if self.inference_engine.is_engine:
            return results if not isinstance(results, list) else results[0]
        return results[0] if isinstance(results, list) else results
    
    def _update_yolo_stats(self, infer_time, result):
        """YOLO 통계 업데이트"""
        self.last_infer_time = infer_time
        self.inference_engine._update_infer_stats(infer_time)
        self.avg_infer_time = self.inference_engine.avg_infer_time
        self.detected_count = len(result.boxes) if hasattr(result, 'boxes') else 0
    
    def _draw_scaled_pixmap(self, painter, pixmap):
        """스케일된 이미지 그리기"""
        w, h = self.width(), self.height()
        key = (pixmap.cacheKey(), w, h)
        
        if key != self._cache_key:
            self._scaled_cache = pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.FastTransformation)
            self._cache_key = key
        
        x = (w - self._scaled_cache.width()) // 2
        y = (h - self._scaled_cache.height()) // 2
        painter.drawPixmap(x, y, self._scaled_cache)

    def update_camera_frame(self, q_image, frame_bgr=None):
        """카메라 프레임 업데이트"""
        if q_image is None or q_image.isNull():
            self.pending_pixmap = None
            self.current_frame_bgr = None
        else:
            self.pending_pixmap = QPixmap.fromImage(q_image)
            self.current_frame_bgr = frame_bgr
    
    def on_frame_swapped(self):
        """frameSwapped 시그널 처리"""
        self._frame += 1
        
        # VSync 프레임 신호 전달 (검은 화면일 때)
        if self.parent_window and self.show_black:
            self.parent_window.on_vsync_frame()
        
        self.show_black = not self.show_black
        self.update()
    
    def keyPressEvent(self, event):
        """ESC/Q 키로 종료"""
        if event.key() in (Qt.Key_Escape, Qt.Key_Q):
            self.close()


class MainWindow(QMainWindow):
    """OpenGL 카메라 메인 윈도우"""
    
    # 기본값
    DEFAULT_EXPOSURE_MS = 9
    DEFAULT_VSYNC_DELAY_MS = 17
    DEFAULT_WINDOW_SIZE = (1024, 768)
    CONTROL_PANEL_HEIGHT = 100
    BUTTON_WIDTH = 150
    
    def __init__(self):
        super().__init__()
        self.camera_ip = CAMERA_IP
        self.camera = None
        self.exposure_time_ms = self.DEFAULT_EXPOSURE_MS
        self.vsync_delay_ms = self.DEFAULT_VSYNC_DELAY_MS
        
        self.setWindowTitle("OpenGL Camera - YOLO")
        
        # YOLO 초기화
        self.inference_engine, self.yolo_renderer = self._init_yolo_model()
        
        # OpenGL 윈도우 생성
        self.opengl_window = CameraOpenGLWindow(
            parent_window=self,
            inference_engine=self.inference_engine,
            yolo_renderer=self.yolo_renderer
        )
        
        # UI 설정
        self._setup_ui()
        self.resize(*self.DEFAULT_WINDOW_SIZE)
        
        # 카메라 초기화
        self.setup_camera()
    
    def _setup_ui(self):
        """UI 레이아웃 설정"""
        container = QWidget.createWindowContainer(self.opengl_window, self)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(container, stretch=1)
        
        self._setup_controls(main_layout)
    
    def _init_yolo_model(self):
        """YOLO 모델 및 렌더러 초기화"""
        try:
            models_dir = Path(__file__).parent.parent / "yolo" / "models"
            if not models_dir.exists():
                print("⚠️ YOLO 모델 디렉토리 없음 - YOLO 비활성화")
                return None, None
            
            engine_files = sorted(models_dir.glob("*.engine"))
            if not engine_files:
                print("⚠️ .engine 파일 없음 - YOLO 비활성화")
                return None, None
            
            model_manager = ModelManager(models_dir)
            model_manager.model_list = [(f.name, str(f)) for f in engine_files]
            model_manager.current_model = model_manager._load_single_model(str(engine_files[0]))
            
            inference_engine = InferenceEngine(
                model_manager.current_model,
                str(engine_files[0]),
                EngineConfig()
            )
            
            yolo_renderer = CustomYOLORenderer(model_manager.current_model)
            
            print(f"✅ YOLO 모델 로드: {engine_files[0].name}")
            return inference_engine, yolo_renderer
        except Exception as e:
            print(f"⚠️ YOLO 초기화 실패: {e} - YOLO 비활성화")
            return None, None

    def _setup_controls(self, parent_layout):
        """컨트롤 패널 설정"""
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls.setMaximumHeight(self.CONTROL_PANEL_HEIGHT)
        
        # 토글 버튼
        self._create_toggle_buttons(controls_layout)
        
        # 슬라이더
        self._create_slider(controls_layout, "Gain:", 0, 100, 0, self.on_gain_change)
        self._create_slider(controls_layout, "노출시간:", 1, 30, self.exposure_time_ms, 
                           self.on_exposure_change, "ms")
        self._create_slider(controls_layout, "셔터 딜레이:", 0, 50, self.vsync_delay_ms, 
                           self.on_delay_change, "ms")
        
        parent_layout.addWidget(controls)
    
    def _create_toggle_buttons(self, layout):
        """토글 버튼 생성"""
        button_layout = QHBoxLayout()
        
        self.bbox_btn = QPushButton("바운딩 박스: ON")
        self.bbox_btn.clicked.connect(self.on_bbox_toggle)
        self.bbox_btn.setFixedWidth(self.BUTTON_WIDTH)
        button_layout.addWidget(self.bbox_btn)
        
        self.camera_feed_btn = QPushButton("촬영화면: ON")
        self.camera_feed_btn.clicked.connect(self.on_camera_feed_toggle)
        self.camera_feed_btn.setFixedWidth(self.BUTTON_WIDTH)
        button_layout.addWidget(self.camera_feed_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
    
    def _create_slider(self, layout, label_text, min_val, max_val, init_val, callback, unit=""):
        """슬라이더 생성 (공통 로직)"""
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel(label_text))
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(init_val)
        slider.valueChanged.connect(callback)
        slider_layout.addWidget(slider)
        
        label = QLabel(f"{init_val}{unit}")
        slider_layout.addWidget(label)
        
        # 인스턴스 변수로 저장
        attr_name = label_text.replace(":", "").replace(" ", "_").lower()
        setattr(self, f"{attr_name}_slider", slider)
        setattr(self, f"{attr_name}_label", label)
        
        layout.addLayout(slider_layout)

    def setup_camera(self):
        """카메라 설정"""
        self.camera = OpenGLCameraController(self.camera_ip)
        success, message = self.camera.setup_camera()
        
        if not success:
            print(f"❌ 카메라 초기화 실패: {message}")
            return
        
        self.camera.set_frame_callback(self.on_new_camera_frame)
        
        # 초기 설정
        gain_value = self.camera.get_gain()
        self.gain_slider.setValue(int(gain_value))
        self.gain_label.setText(str(int(gain_value)))
        
        self.camera.set_exposure_time(self.exposure_time_ms * 1000)
        
        # 트리거 모드
        if self.camera.hCamera:
            mvsdk.CameraSetTriggerMode(self.camera.hCamera, 1)
            mvsdk.CameraSoftTrigger(self.camera.hCamera)
        
        print(f"✅ 카메라 연결 성공: {self.camera.camera_info['name']}")
        print(f"🎬 초기 셔터 트리거 발생")

    def on_new_camera_frame(self, q_image):
        """카메라 프레임 콜백"""
        if q_image and not q_image.isNull():
            frame_bgr = self._qimage_to_bgr(q_image)
            self.opengl_window.update_camera_frame(q_image, frame_bgr)
    
    def _qimage_to_bgr(self, q_image):
        """QImage를 BGR로 변환"""
        try:
            width, height = q_image.width(), q_image.height()
            arr = np.array(q_image.bits()).reshape(height, width, 3)
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"⚠️ QImage to BGR 변환 실패: {e}")
            return None

    def on_bbox_toggle(self):
        """바운딩 박스 토글"""
        if self.yolo_renderer:
            self.yolo_renderer.draw_boxes = not self.yolo_renderer.draw_boxes
            status = "ON" if self.yolo_renderer.draw_boxes else "OFF"
            self.bbox_btn.setText(f"바운딩 박스: {status}")
            self.opengl_window._cache_key = None
            print(f"{'✅' if self.yolo_renderer.draw_boxes else '❌'} 바운딩 박스")
    
    def on_camera_feed_toggle(self):
        """촬영화면 토글"""
        if self.yolo_renderer:
            self.yolo_renderer.draw_camera_feed = not self.yolo_renderer.draw_camera_feed
            status = "ON" if self.yolo_renderer.draw_camera_feed else "OFF"
            self.camera_feed_btn.setText(f"촬영화면: {status}")
            self.opengl_window._cache_key = None
            print(f"{'✅' if self.yolo_renderer.draw_camera_feed else '❌'} 촬영화면")
    
    def on_gain_change(self, value):
        """게인 변경"""
        if self.camera:
            self.camera.set_gain(value)
        self.gain_label.setText(str(int(value)))

    def on_exposure_change(self, value):
        """노출시간 변경"""
        self.exposure_time_ms = value
        if self.camera:
            self.camera.set_exposure_time(value * 1000)
        self.노출시간_label.setText(f"{value}ms")
    
    def on_delay_change(self, value):
        """셔터 딜레이 변경"""
        self.vsync_delay_ms = value
        self.셔터_딜레이_label.setText(f"{value}ms")
    
    def on_vsync_frame(self):
        """VSync 프레임 신호 처리"""
        if self.camera and self.camera.hCamera:
            threading.Thread(
                target=self._precise_delay_trigger,
                args=(self.vsync_delay_ms,),
                daemon=True
            ).start()
    
    def _precise_delay_trigger(self, delay_ms):
        """고정밀 딜레이 후 카메라 트리거"""
        if delay_ms > 0:
            start_time = time.perf_counter()
            target_time = start_time + (delay_ms / 1000.0)
            
            # busy-wait: 1ms 전까지는 sleep
            while time.perf_counter() < target_time - BUSY_WAIT_THRESHOLD_MS:
                time.sleep(BUSY_WAIT_SLEEP_US)
            
            # 마지막 1ms는 busy-wait
            while time.perf_counter() < target_time:
                pass
        
        if self.camera and self.camera.hCamera:
            mvsdk.CameraSoftTrigger(self.camera.hCamera)

    def keyPressEvent(self, event):
        """ESC/Q 키로 종료"""
        if event.key() in (Qt.Key_Escape, Qt.Key_Q):
            self.close()

    def closeEvent(self, event):
        """윈도우 종료 시 정리"""
        if self.camera:
            self.camera.cleanup()
        event.accept()


def setup_opengl_format():
    """OpenGL 포맷 설정"""
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.OpenGLES)
    fmt.setVersion(3, 2)
    fmt.setSwapInterval(1)
    fmt.setSwapBehavior(QSurfaceFormat.DoubleBuffer)
    fmt.setDepthBufferSize(0)
    QSurfaceFormat.setDefaultFormat(fmt)


def main():
    """애플리케이션 진입점"""
    # Wayland 환경 설정
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
    
    # Wayland EGL 플랫폼 설정
    os.environ['QT_QPA_PLATFORM'] = 'wayland-egl'
    
    # OpenGL 설정
    setup_opengl_format()
    
    print(f"🎨 OpenGL ES 3.2 + EGL + Wayland + VSync 설정 완료")
    print(f"📌 QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM')}")
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.opengl_window.update()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
