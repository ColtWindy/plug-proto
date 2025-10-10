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
                                QSlider, QGroupBox, QGridLayout, QRadioButton, QButtonGroup)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from camera.camera_controller import CameraController
from camera.video_file_controller import VideoFileController


class YOLOCameraWindow(QMainWindow):
    """YOLO 카메라 윈도우"""
    
    def __init__(self, model, model_list):
        super().__init__()
        self.model = model
        self.model_list = model_list
        self.camera = None
        self.source_type = 'camera'
        
        self.setWindowTitle("YOLO Inference")
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
        
        # 비디오 파일 목록
        self.video_files = self._scan_video_files()
        
        # UI 초기화
        self.init_ui()
        self.init_model_combo()
        self.update_source_ui()
    
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
        
        # 소스 선택
        layout.addWidget(QLabel("소스:"), row, 0)
        source_layout = QHBoxLayout()
        
        self.source_button_group = QButtonGroup()
        self.camera_radio = QRadioButton("카메라")
        self.file_radio = QRadioButton("파일")
        self.camera_radio.setChecked(True)
        
        self.source_button_group.addButton(self.camera_radio)
        self.source_button_group.addButton(self.file_radio)
        
        self.camera_radio.toggled.connect(self.on_source_changed)
        
        source_layout.addWidget(self.camera_radio)
        source_layout.addWidget(self.file_radio)
        layout.addLayout(source_layout, row, 1)
        row += 1
        
        # 비디오 파일 선택
        layout.addWidget(QLabel("비디오:"), row, 0)
        self.video_combo = QComboBox()
        for video_path in self.video_files:
            video_name = Path(video_path).name
            self.video_combo.addItem(video_name, video_path)
        layout.addWidget(self.video_combo, row, 1)
        row += 1
        
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
    
    def _scan_video_files(self):
        """비디오 파일 스캔"""
        samples_dir = Path(__file__).parent.parent / "samples"
        if not samples_dir.exists():
            return []
        
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        video_files = []
        for ext in video_extensions:
            video_files.extend(samples_dir.glob(f"*{ext}"))
        
        return sorted([str(f) for f in video_files])
    
    def init_model_combo(self):
        """모델 콤보박스 초기화"""
        for model_name, model_path in self.model_list:
            self.model_combo.addItem(model_name, model_path)
    
    def on_source_changed(self):
        """소스 변경"""
        if self.is_running:
            return
        
        self.source_type = 'camera' if self.camera_radio.isChecked() else 'file'
        self.update_source_ui()
    
    def update_source_ui(self):
        """소스에 따른 UI 업데이트"""
        is_camera = self.source_type == 'camera'
        
        # 비디오 파일 콤보박스
        self.video_combo.setEnabled(not is_camera)
        
        # 상태 메시지
        if is_camera:
            self.status_label.setText("카메라 모드 - 시작 버튼을 클릭하세요")
        else:
            self.status_label.setText("비디오 파일 모드 - 시작 버튼을 클릭하세요")
    
    def init_camera_controls(self):
        """카메라 컨트롤 초기화 (카메라 모드 전용)"""
        if not self.camera or self.source_type != 'camera':
            return
        
        try:
            # 해상도
            self.resolution_combo.clear()
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
        # 소스 초기화
        if not self._init_source():
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
        
        # 카메라/비디오 시작
        target_fps = self.fps_slider.value()
        self.camera.start_trigger(target_fps)
        
        # UI 상태
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.model_combo.setEnabled(False)
        self.camera_radio.setEnabled(False)
        self.file_radio.setEnabled(False)
        self.video_combo.setEnabled(False)
        self.resolution_combo.setEnabled(False)
        
        status = "실시간 객체 탐지 중..." if self.source_type == 'camera' else "비디오 분석 중..."
        self.status_label.setText(status)
        
        print(f"\n🎬 시작 (타겟 FPS: {target_fps})")
    
    def _init_source(self):
        """소스 초기화 (카메라 또는 비디오)"""
        try:
            if self.source_type == 'camera':
                self.camera = CameraController()
                self.camera.initialize()
                self.camera.signals.frame_ready.connect(self.on_camera_frame)
                self.init_camera_controls()
                print("✅ 카메라 초기화 완료")
            else:
                video_path = self.video_combo.currentData()
                if not video_path:
                    self.status_label.setText("비디오 파일을 선택하세요")
                    return False
                
                self.camera = VideoFileController(video_path)
                self.camera.initialize()
                self.camera.signals.frame_ready.connect(self.on_camera_frame)
                
                # 비디오 모드 컨트롤 설정
                self.fps_slider.setEnabled(True)
                self.resolution_combo.setEnabled(False)
                self.exposure_slider.setEnabled(False)
                self.gain_slider.setEnabled(False)
                
                print(f"✅ 비디오 초기화 완료: {Path(video_path).name}")
            
            return True
            
        except Exception as e:
            source_name = "카메라" if self.source_type == 'camera' else "비디오"
            print(f"❌ {source_name} 초기화 실패: {e}")
            self.status_label.setText(f"{source_name} 초기화 실패: {e}")
            return False
    
    def stop_capture(self):
        """캡처 중지"""
        if not self.camera:
            return
        
        self.is_running = False
        self.camera.is_running = False
        self.camera.stop_trigger()
        self.camera.cleanup()
        self.camera = None
        
        # UI 상태
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.model_combo.setEnabled(True)
        self.camera_radio.setEnabled(True)
        self.file_radio.setEnabled(True)
        self.video_combo.setEnabled(self.source_type == 'file')
        self.resolution_combo.setEnabled(False)
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
        
        if self.camera:
            self.camera.cleanup()
        
        event.accept()

