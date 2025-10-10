#coding=utf-8
"""
YOLO 카메라 메인 윈도우
UI 레이아웃, 디스플레이
"""
import time
from pathlib import Path
import cv2
from ultralytics import YOLO
from PySide6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QWidget, 
                                QPushButton, QHBoxLayout, QSizePolicy, QComboBox, 
                                QSlider, QGroupBox, QGridLayout)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap


class YOLOCameraWindow(QMainWindow):
    """YOLO 카메라 윈도우"""
    
    def __init__(self, camera_controller, model, model_list):
        super().__init__()
        self.camera = camera_controller
        self.model = model
        self.model_list = model_list
        
        self.setWindowTitle("YOLO Inference - MindVision Camera")
        self.setGeometry(100, 100, 1280, 720)
        
        # 상태
        self.is_running = False
        self.frame_width = 0
        self.frame_height = 0
        
        # FPS 계산
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self.current_fps = 0.0
        
        # 추론 통계
        self.last_infer_time = 0.0
        self.infer_times = []
        self.avg_infer_time = 0.0
        
        # 스케일 캐시
        self._scaled_cache = None
        self._cache_key = None
        
        # UI 초기화
        self.init_ui()
        
        # 초기화
        self.init_model_combo()
        self.init_camera_controls()
        
        # 카메라 시그널 연결
        self.camera.signals.frame_ready.connect(self.on_camera_frame)
    
    def init_ui(self):
        """UI 초기화"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        
        # 왼쪽: 비디오
        video_layout = QVBoxLayout()
        
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        video_layout.addWidget(self.video_label, stretch=1)
        
        self.status_label = QLabel("초기화 중...")
        self.status_label.setAlignment(Qt.AlignCenter)
        video_layout.addWidget(self.status_label)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("시작")
        self.start_button.clicked.connect(self.start_capture)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("중지")
        self.stop_button.clicked.connect(self.stop_capture)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        self.quit_button = QPushButton("종료")
        self.quit_button.clicked.connect(self.close)
        button_layout.addWidget(self.quit_button)
        
        video_layout.addLayout(button_layout)
        main_layout.addLayout(video_layout, stretch=3)
        
        # 오른쪽: 컨트롤
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, stretch=1)
        
        central_widget.setLayout(main_layout)
    
    def create_control_panel(self):
        """컨트롤 패널 생성"""
        control_group = QGroupBox("설정")
        layout = QGridLayout()
        
        row = 0
        
        # 모델 선택
        layout.addWidget(QLabel("모델:"), row, 0)
        self.model_combo = QComboBox()
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        layout.addWidget(self.model_combo, row, 1)
        row += 1
        
        # 해상도
        layout.addWidget(QLabel("카메라 해상도:"), row, 0)
        self.resolution_combo = QComboBox()
        self.resolution_combo.currentIndexChanged.connect(self.on_resolution_changed)
        self.resolution_combo.setEnabled(False)
        layout.addWidget(self.resolution_combo, row, 1)
        row += 1
        
        # FPS
        layout.addWidget(QLabel("타겟 FPS:"), row, 0)
        self.fps_slider = QSlider(Qt.Horizontal)
        self.fps_slider.setMinimum(15)
        self.fps_slider.setMaximum(60)
        self.fps_slider.setValue(30)
        self.fps_slider.valueChanged.connect(self.on_fps_changed)
        self.fps_slider.setEnabled(False)
        layout.addWidget(self.fps_slider, row, 1)
        row += 1
        
        self.fps_label = QLabel("30 FPS")
        self.fps_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.fps_label, row, 0, 1, 2)
        row += 1
        
        # 노출 시간
        layout.addWidget(QLabel("노출 시간 (ms):"), row, 0)
        self.exposure_slider = QSlider(Qt.Horizontal)
        self.exposure_slider.valueChanged.connect(self.on_exposure_changed)
        self.exposure_slider.setEnabled(False)
        layout.addWidget(self.exposure_slider, row, 1)
        row += 1
        
        self.exposure_label = QLabel("0 ms")
        self.exposure_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.exposure_label, row, 0, 1, 2)
        row += 1
        
        # 게인
        layout.addWidget(QLabel("게인:"), row, 0)
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.valueChanged.connect(self.on_gain_changed)
        self.gain_slider.setEnabled(False)
        layout.addWidget(self.gain_slider, row, 1)
        row += 1
        
        self.gain_label = QLabel("0")
        self.gain_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.gain_label, row, 0, 1, 2)
        row += 1
        
        layout.setRowStretch(row, 1)
        control_group.setLayout(layout)
        control_group.setMaximumWidth(300)
        
        return control_group
    
    def init_model_combo(self):
        """모델 콤보박스 초기화"""
        for model_name, model_path in self.model_list:
            self.model_combo.addItem(model_name, model_path)
    
    def init_camera_controls(self):
        """카메라 컨트롤 초기화"""
        try:
            # 해상도
            resolutions, current_index = self.camera.get_resolutions()
            for res in resolutions:
                self.resolution_combo.addItem(res['text'], res['desc'])
            self.resolution_combo.setCurrentIndex(current_index)
            self.resolution_combo.setEnabled(True)
            
            # 노출 시간
            target_fps = self.fps_slider.value()
            max_exposure_ms = int(1000 / target_fps * 0.8)
            
            self.exposure_slider.setMinimum(1)
            self.exposure_slider.setMaximum(max_exposure_ms)
            self.exposure_slider.setValue(max_exposure_ms // 2)
            self.exposure_label.setText(f"{max_exposure_ms // 2} ms")
            
            # 수동 노출 설정
            self.camera.set_manual_exposure(max_exposure_ms // 2)
            print(f"✅ 수동 노출: {max_exposure_ms // 2}ms")
            
            # 게인
            gain_min, gain_max = self.camera.get_gain_range()
            current_gain = self.camera.get_current_gain()
            
            self.gain_slider.setMinimum(gain_min)
            self.gain_slider.setMaximum(gain_max)
            self.gain_slider.setValue(current_gain)
            self.gain_label.setText(f"{current_gain}")
            
            # 컨트롤 활성화
            self.fps_slider.setEnabled(True)
            self.exposure_slider.setEnabled(True)
            self.gain_slider.setEnabled(True)
            
            self.status_label.setText("카메라 준비 완료 - 시작 버튼을 클릭하세요")
            
        except Exception as e:
            print(f"❌ 컨트롤 초기화 실패: {e}")
            self.status_label.setText(f"컨트롤 초기화 실패: {e}")
    
    def on_model_changed(self, index):
        """모델 변경"""
        if index < 0 or self.is_running:
            return
        
        model_path = self.model_combo.itemData(index)
        if model_path:
            self.model = YOLO(model_path)
            print(f"✅ 모델 변경: {Path(model_path).name}")
    
    def on_resolution_changed(self, index):
        """해상도 변경"""
        if self.is_running:
            return
        
        resolution = self.resolution_combo.itemData(index)
        if resolution:
            self.camera.set_resolution(resolution)
            self.frame_width = 0
            self.frame_height = 0
    
    def on_fps_changed(self, fps):
        """FPS 변경"""
        self.fps_label.setText(f"{fps} FPS")
        self.camera.target_fps = fps
        
        # 최대 노출 재계산
        max_exposure_ms = int(1000 / fps * 0.8)
        self.exposure_slider.setMaximum(max_exposure_ms)
        
        if self.exposure_slider.value() > max_exposure_ms:
            self.exposure_slider.setValue(max_exposure_ms)
    
    def on_exposure_changed(self, value_ms):
        """노출 시간 변경"""
        fps_interval_ms = 1000 / self.camera.target_fps
        
        if value_ms > fps_interval_ms * 0.8:
            self.exposure_label.setText(f"{value_ms} ms ⚠️")
            self.exposure_label.setStyleSheet("color: red;")
        else:
            self.exposure_label.setText(f"{value_ms} ms")
            self.exposure_label.setStyleSheet("")
        
        self.camera.set_exposure(value_ms)
    
    def on_gain_changed(self, value):
        """게인 변경"""
        self.camera.set_gain(value)
        self.gain_label.setText(f"{value}")
    
    def on_camera_frame(self, frame_bgr):
        """카메라 프레임 콜백 + 추론 + 디스플레이"""
        if not self.is_running:
            return
        
        # 프레임 크기
        if self.frame_width == 0 or self.frame_height == 0:
            self.frame_height, self.frame_width = frame_bgr.shape[:2]
        
        # FPS 계산
        self.fps_frame_count += 1
        elapsed_time = time.time() - self.fps_start_time
        if elapsed_time >= 1.0:
            self.current_fps = self.fps_frame_count / elapsed_time
            self.fps_start_time = time.time()
            self.fps_frame_count = 0
        
        # YOLO 추론
        start_time = time.time()
        results = self.model(frame_bgr, verbose=False)
        infer_time = (time.time() - start_time) * 1000
        
        # 결과 렌더링
        annotated_frame = results[0].plot()
        detected_count = len(results[0].boxes)
        
        self.last_infer_time = infer_time
        
        # 평균 추론 시간
        self.infer_times.append(infer_time)
        if len(self.infer_times) > 30:
            self.infer_times.pop(0)
        self.avg_infer_time = sum(self.infer_times) / len(self.infer_times)
        
        # BGR → RGB
        annotated_frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        
        # QImage 변환
        height, width, channel = annotated_frame_rgb.shape
        bytes_per_line = 3 * width
        q_image = QImage(annotated_frame_rgb.data, width, height, 
                        bytes_per_line, QImage.Format_RGB888).copy()
        
        # QPixmap 스케일링 (캐시 사용)
        pixmap = QPixmap.fromImage(q_image)
        label_size = self.video_label.size()
        cache_key = (label_size.width(), label_size.height(), pixmap.cacheKey())
        
        if cache_key != self._cache_key:
            self._scaled_cache = pixmap.scaled(label_size, Qt.KeepAspectRatio, 
                                              Qt.FastTransformation)
            self._cache_key = cache_key
        
        self.video_label.setPixmap(self._scaled_cache)
        
        # 상태 표시
        status_text = (f"FPS: {self.current_fps:.1f} | "
                      f"추론: {self.last_infer_time:.1f}ms "
                      f"(평균: {self.avg_infer_time:.1f}ms) | "
                      f"탐지: {detected_count}")
        
        if self.frame_width > 0 and self.frame_height > 0:
            status_text += f" | 해상도: {self.frame_width}x{self.frame_height}"
        
        self.status_label.setText(status_text)
    
    def start_capture(self):
        """캡처 시작"""
        if not self.camera.hCamera or not self.model:
            self.status_label.setText("카메라 또는 모델이 초기화되지 않았습니다")
            return
        
        # 상태 초기화
        self.is_running = True
        self.camera.is_running = True
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self._scaled_cache = None
        self.frame_width = 0
        self.frame_height = 0
        self.infer_times = []
        self.avg_infer_time = 0.0
        
        # 카메라 트리거 시작
        self.camera.start_trigger(self.camera.target_fps)
        
        # UI 상태
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.model_combo.setEnabled(False)
        self.resolution_combo.setEnabled(False)
        self.status_label.setText("실시간 객체 탐지 중...")
        
        print(f"\n🎬 시작 (타겟 FPS: {self.camera.target_fps})")
    
    def stop_capture(self):
        """캡처 중지"""
        self.is_running = False
        self.camera.is_running = False
        self.camera.stop_trigger()
        
        # UI 상태
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.model_combo.setEnabled(True)
        self.resolution_combo.setEnabled(True)
        self.status_label.setText("중지됨")
    
    def resizeEvent(self, event):
        """윈도우 크기 변경"""
        super().resizeEvent(event)
        self._scaled_cache = None
        self._cache_key = None
    
    def closeEvent(self, event):
        """윈도우 종료"""
        if self.is_running:
            self.stop_capture()
        
        self.camera.cleanup()
        event.accept()

