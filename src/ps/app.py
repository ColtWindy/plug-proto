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
import json
from pathlib import Path

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget, 
                                QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSizePolicy, QComboBox)
from PySide6.QtOpenGL import QOpenGLWindow
from PySide6.QtGui import QSurfaceFormat, QPainter, QFont, QColor, QPen, QPixmap, QImage
from PySide6.QtCore import Qt
from OpenGL import GL

from opengl_example.camera_controller import OpenGLCameraController
from _lib import mvsdk
from _lib.wayland_utils import setup_wayland_environment
from yolo.inference.model_manager import YOLOEModelManager
from yolo.inference.engine import InferenceEngine
from ps.yolo_renderer import CustomYOLORenderer


# ==================== 전용 Config ====================
# 카메라 설정
CAMERA_IP = "192.168.0.100"

# YOLO 프롬프트 (탐지할 객체)
YOLO_PROMPTS = [
    "cup", "square", "bottle", "white paper cup", "paper bottle with text", 
    "white paper cup with text", "transparent plastic bottle", "carton box", "square box",
    "plastic bag", "paper bag", "plastic bottle", "paper bottle", "plastic cup", "paper cup",
    ]

# YOLO 추론 설정 (ID 일관성 우선)
YOLO_CONF = 0.15        # 낮은 신뢰도로 지속 탐지
YOLO_IOU = 0.5          # 겹침 허용도
YOLO_MAX_DET = 50      # 최대 탐지 수
YOLO_IMGSZ = 640        # 입력 이미지 크기

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
        self.original_frame_bgr = None  # 호모그래피 적용 전 원본
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
        
        # 호모그래피 핸들 (4개 모서리)
        self.homography_enabled = True
        self.show_handles = True  # 핸들 표시 여부
        self.homography_handles = None  # 초기화는 첫 프레임에서
        self.dragging_handle = None
        self.handle_radius = 10
        
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
        
        # 호모그래피 핸들 그리기 (항상 표시)
        if self.show_handles and self.homography_handles is not None:
            self._draw_homography_handles(painter)
        
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
        
        # 호모그래피 핸들 그리기
        if self.show_handles and self.homography_handles is not None:
            self._draw_homography_handles(painter)
        
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
        """YOLO 추론 수행 (ByteTrack 추적)"""
        if not (self.current_frame_bgr is not None and self.inference_engine and self.yolo_renderer):
            return self.current_pixmap
        
        try:
            start_time = time.time()
            
            # 추론 실행 (설정 + ByteTrack)
            results = self.inference_engine.model.track(
                self.current_frame_bgr,
                persist=True,
                **self.inference_engine.config.to_dict()
            )
            
            infer_time = (time.time() - start_time) * 1000
            
            # 결과 처리
            result = self._extract_result(results)
            
            # 렌더링
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
            self.original_frame_bgr = None
        else:
            # 원본 프레임 저장
            self.original_frame_bgr = frame_bgr
            
            # 호모그래피 핸들 초기화 (첫 프레임)
            if self.homography_handles is None and frame_bgr is not None:
                self._init_homography_handles(frame_bgr.shape[1], frame_bgr.shape[0])
            
            # 호모그래피 변환 적용
            if self.homography_enabled and frame_bgr is not None:
                transformed_bgr = self._apply_homography(frame_bgr)
                transformed_q_image = self._bgr_to_qimage(transformed_bgr)
                self.pending_pixmap = QPixmap.fromImage(transformed_q_image)
                self.current_frame_bgr = transformed_bgr
            else:
                self.pending_pixmap = QPixmap.fromImage(q_image)
                self.current_frame_bgr = frame_bgr
    
    def _init_homography_handles(self, width, height):
        """호모그래피 핸들 초기화 (이미지 크기 기준)"""
        # 저장된 핸들 위치가 있으면 로드
        settings_file = Path(__file__).parent / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    data = json.load(f)
                    homography = data.get('homography', {})
                    if homography.get('width') == width and homography.get('height') == height:
                        self.homography_handles = np.float32(homography['handles'])
                        self.show_handles = homography.get('show_handles', True)
                        print(f"✅ 호모그래피 핸들 로드: {width}x{height}")
                        return
            except Exception as e:
                print(f"⚠️ 설정 로드 실패: {e}")
        
        # 기본값으로 초기화
        margin = 50
        self.homography_handles = np.float32([
            [margin, margin],                    # 좌상단
            [width - margin, margin],            # 우상단
            [width - margin, height - margin],   # 우하단
            [margin, height - margin]            # 좌하단
        ])
        print(f"✅ 호모그래피 핸들 초기화: {width}x{height}")
    
    def _apply_homography(self, frame_bgr):
        """호모그래피 변환 적용"""
        if self.homography_handles is None:
            return frame_bgr
        
        h, w = frame_bgr.shape[:2]
        
        # 소스 포인트 (핸들 위치)
        src_points = self.homography_handles
        
        # 목적지 포인트 (전체 이미지)
        dst_points = np.float32([
            [0, 0],
            [w, 0],
            [w, h],
            [0, h]
        ])
        
        # 호모그래피 행렬 계산
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # 변환 적용
        warped = cv2.warpPerspective(frame_bgr, matrix, (w, h))
        return warped
    
    def _bgr_to_qimage(self, frame_bgr):
        """BGR 프레임을 QImage로 변환"""
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        return QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
    
    def _draw_homography_handles(self, painter):
        """호모그래피 핸들 그리기"""
        if self.homography_handles is None:
            return
        
        # 이미지 좌표를 화면 좌표로 변환
        screen_handles = self._image_to_screen_coords(self.homography_handles)
        
        # 핸들 연결선 그리기
        painter.setPen(QPen(QColor(255, 255, 0), 2))
        for i in range(4):
            start = screen_handles[i]
            end = screen_handles[(i + 1) % 4]
            painter.drawLine(int(start[0]), int(start[1]), int(end[0]), int(end[1]))
        
        # 핸들 원 그리기
        for i, handle in enumerate(screen_handles):
            if self.dragging_handle == i:
                painter.setBrush(QColor(255, 0, 0, 180))
            else:
                painter.setBrush(QColor(255, 255, 0, 180))
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawEllipse(int(handle[0] - self.handle_radius), 
                              int(handle[1] - self.handle_radius),
                              self.handle_radius * 2, 
                              self.handle_radius * 2)
    
    def _image_to_screen_coords(self, image_points):
        """이미지 좌표를 화면 좌표로 변환"""
        if self.original_frame_bgr is None:
            return image_points
        
        img_h, img_w = self.original_frame_bgr.shape[:2]
        screen_w, screen_h = self.width(), self.height()
        
        # 종횡비 유지하며 스케일 계산
        scale = min(screen_w / img_w, screen_h / img_h)
        scaled_w = int(img_w * scale)
        scaled_h = int(img_h * scale)
        
        # 센터링 오프셋
        offset_x = (screen_w - scaled_w) // 2
        offset_y = (screen_h - scaled_h) // 2
        
        # 변환
        screen_points = []
        for pt in image_points:
            x = pt[0] * scale + offset_x
            y = pt[1] * scale + offset_y
            screen_points.append([x, y])
        
        return np.array(screen_points, dtype=np.float32)
    
    def _screen_to_image_coords(self, screen_x, screen_y):
        """화면 좌표를 이미지 좌표로 변환"""
        if self.original_frame_bgr is None:
            return screen_x, screen_y
        
        img_h, img_w = self.original_frame_bgr.shape[:2]
        screen_w, screen_h = self.width(), self.height()
        
        # 종횡비 유지하며 스케일 계산
        scale = min(screen_w / img_w, screen_h / img_h)
        scaled_w = int(img_w * scale)
        scaled_h = int(img_h * scale)
        
        # 센터링 오프셋
        offset_x = (screen_w - scaled_w) // 2
        offset_y = (screen_h - scaled_h) // 2
        
        # 역변환
        img_x = (screen_x - offset_x) / scale
        img_y = (screen_y - offset_y) / scale
        
        return img_x, img_y
    
    def _find_handle_at_pos(self, x, y):
        """주어진 화면 좌표에 있는 핸들 찾기"""
        if self.homography_handles is None:
            return None
        
        screen_handles = self._image_to_screen_coords(self.homography_handles)
        
        for i, handle in enumerate(screen_handles):
            dist = np.sqrt((handle[0] - x)**2 + (handle[1] - y)**2)
            if dist <= self.handle_radius:
                return i
        
        return None
    
    def mousePressEvent(self, event):
        """마우스 클릭 이벤트"""
        if event.button() == Qt.LeftButton and self.show_handles:
            x, y = event.position().x(), event.position().y()
            self.dragging_handle = self._find_handle_at_pos(x, y)
            if self.dragging_handle is not None:
                event.accept()
                return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트"""
        if self.dragging_handle is not None and self.homography_enabled:
            x, y = event.position().x(), event.position().y()
            img_x, img_y = self._screen_to_image_coords(x, y)
            
            # 핸들 위치 업데이트
            self.homography_handles[self.dragging_handle] = [img_x, img_y]
            
            # 원본 프레임으로 다시 변환
            if self.original_frame_bgr is not None:
                transformed_bgr = self._apply_homography(self.original_frame_bgr)
                self.current_frame_bgr = transformed_bgr
                transformed_q_image = self._bgr_to_qimage(transformed_bgr)
                self.current_pixmap = QPixmap.fromImage(transformed_q_image)
                self._cache_key = None
            
            event.accept()
            return
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """마우스 릴리즈 이벤트"""
        if event.button() == Qt.LeftButton and self.dragging_handle is not None:
            self.dragging_handle = None
            self.save_settings()  # 변경 시 자동 저장
            event.accept()
            return
        super().mouseReleaseEvent(event)
    
    def on_frame_swapped(self):
        """frameSwapped 시그널 처리"""
        self._frame += 1
        
        # VSync 프레임 신호 전달 (검은 화면일 때)
        if self.parent_window and self.show_black:
            self.parent_window.on_vsync_frame()
        
        self.show_black = not self.show_black
        self.update()
    
    def save_settings(self):
        """설정 자동 저장"""
        if self.homography_handles is None or self.original_frame_bgr is None:
            return
        
        h, w = self.original_frame_bgr.shape[:2]
        settings_file = Path(__file__).parent / "settings.json"
        
        try:
            # 기존 설정 읽기 (있으면)
            data = {}
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    data = json.load(f)
            
            # 호모그래피 설정 업데이트
            data['homography'] = {
                'width': w,
                'height': h,
                'handles': self.homography_handles.tolist(),
                'show_handles': self.show_handles
            }
            
            # 저장
            with open(settings_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"❌ 설정 저장 실패: {e}")
    
    def keyPressEvent(self, event):
        """키보드 이벤트"""
        # ESC/Q: 종료
        if event.key() in (Qt.Key_Escape, Qt.Key_Q):
            self.close()
        # R: 호모그래피 핸들 리셋
        elif event.key() == Qt.Key_R:
            if self.original_frame_bgr is not None:
                h, w = self.original_frame_bgr.shape[:2]
                margin = 50
                self.homography_handles = np.float32([
                    [margin, margin],
                    [w - margin, margin],
                    [w - margin, h - margin],
                    [margin, h - margin]
                ])
                self.save_settings()  # 자동 저장
                print("✅ 호모그래피 핸들 리셋")
            event.accept()


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
        
        self.setWindowTitle("OpenGL Camera - YOLOE")
        
        # YOLO 초기화
        self.model_manager, self.inference_engine, self.yolo_renderer = self._init_yolo_model()
        
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
        
        # 버튼 상태 동기화 (저장된 설정 반영)
        self._sync_button_states()
    
    def _sync_button_states(self):
        """저장된 설정에 맞게 버튼 상태 동기화"""
        if hasattr(self, 'handle_btn'):
            status = "ON" if self.opengl_window.show_handles else "OFF"
            self.handle_btn.setText(f"핸들: {status}")
    
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
        """YOLOE 모델 및 렌더러 초기화"""
        try:
            models_dir = Path(__file__).parent.parent / "yolo" / "models"
            if not models_dir.exists():
                print("⚠️ YOLO 모델 디렉토리 없음 - YOLO 비활성화")
                return None, None, None
            
            # YOLOE 모델 관리자
            model_manager = YOLOEModelManager(models_dir)
            model, model_list = model_manager.load_models()
            
            if model is None:
                print("⚠️ YOLOE .pt 파일 없음 - YOLO 비활성화")
                return None, None, None
            
            # 프롬프트 설정
            model_manager.update_prompt(YOLO_PROMPTS)
            
            # 추론 설정 객체 생성 (간단한 클래스)
            class YOLOConfig:
                def to_dict(self):
                    return {
                        'conf': YOLO_CONF,
                        'iou': YOLO_IOU,
                        'max_det': YOLO_MAX_DET,
                        'imgsz': YOLO_IMGSZ,
                        'verbose': False
                    }
            
            # 추론 엔진
            inference_engine = InferenceEngine(
                model,
                model_list[0][1] if model_list else None,
                YOLOConfig()
            )
            
            # 렌더러
            yolo_renderer = CustomYOLORenderer(model)
            
            print(f"✅ YOLOE 모델 로드: {Path(model_list[0][1]).name}")
            print(f"✅ 프롬프트: {', '.join(YOLO_PROMPTS)}")
            print(f"✅ ByteTrack (conf={YOLO_CONF}, iou={YOLO_IOU}, ID 일관성 우선)")
            return model_manager, inference_engine, yolo_renderer
        except Exception as e:
            print(f"⚠️ YOLOE 초기화 실패: {e} - YOLO 비활성화")
            return None, None, None

    def _setup_controls(self, parent_layout):
        """컨트롤 패널 설정"""
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls.setMaximumHeight(self.CONTROL_PANEL_HEIGHT)
        
        # 모델 선택 드롭다운
        if self.model_manager:
            self._create_model_selector(controls_layout)
        
        # 토글 버튼
        self._create_toggle_buttons(controls_layout)
        
        # 슬라이더
        self._create_slider(controls_layout, "Gain:", 0, 100, 0, self.on_gain_change)
        self._create_slider(controls_layout, "노출시간:", 1, 30, self.exposure_time_ms, 
                           self.on_exposure_change, "ms")
        self._create_slider(controls_layout, "셔터 딜레이:", 0, 50, self.vsync_delay_ms, 
                           self.on_delay_change, "ms")
        
        parent_layout.addWidget(controls)
    
    def _create_model_selector(self, layout):
        """모델 선택 드롭다운 생성"""
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("모델:"))
        
        self.model_combo = QComboBox()
        for model_name, model_path in self.model_manager.model_list:
            self.model_combo.addItem(model_name, model_path)
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        model_layout.addWidget(self.model_combo)
        
        layout.addLayout(model_layout)
    
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
        
        self.handle_btn = QPushButton("핸들: ON")
        self.handle_btn.clicked.connect(self.on_handle_toggle)
        self.handle_btn.setFixedWidth(self.BUTTON_WIDTH)
        button_layout.addWidget(self.handle_btn)
        
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
    
    def on_handle_toggle(self):
        """핸들 표시/숨김 토글"""
        self.opengl_window.show_handles = not self.opengl_window.show_handles
        status = "ON" if self.opengl_window.show_handles else "OFF"
        self.handle_btn.setText(f"핸들: {status}")
        self.opengl_window.save_settings()  # 자동 저장
        print(f"{'✅' if self.opengl_window.show_handles else '❌'} 핸들 표시")
    
    def on_model_changed(self, index):
        """모델 변경"""
        if index < 0 or not self.model_manager:
            return
        
        model_path = self.model_combo.itemData(index)
        if not model_path:
            return
        
        # 모델 전환
        new_model = self.model_manager.switch_model(model_path)
        
        # 프롬프트 재설정
        self.model_manager.update_prompt(YOLO_PROMPTS)
        
        # 추론 엔진 업데이트
        self.inference_engine.model = new_model
        self.inference_engine.model_path = model_path
        self.inference_engine.is_engine = False
        
        # 렌더러 업데이트
        self.yolo_renderer.model = new_model
        
        # 캐시 초기화
        self.opengl_window._cache_key = None
        
        print(f"✅ 모델 변경: {Path(model_path).name}")
        print(f"✅ 프롬프트: {', '.join(YOLO_PROMPTS)}")
    
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
