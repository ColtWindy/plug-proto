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
                                QGroupBox, QRadioButton, QButtonGroup, QStackedWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from camera.camera_controller import CameraController
from camera.video_file_controller import VideoFileController
from ui.widgets.camera_control_widget import CameraControlWidget
from ui.widgets.video_control_widget import VideoControlWidget


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
        
        # YOLOE 프롬프트 설정 (.pt 파일만)
        if model_list and self._is_yoloe_model(model_list[0][1]) and self._is_pt_file(model_list[0][1]):
            self._setup_yoloe(["car"])
        
        # UI 초기화
        self.init_ui()
        self.init_model_combo()
        self.update_source_ui()
        
        # 카메라 사전 초기화
        self.init_camera_early()
    
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
        
        main_layout.addLayout(video_layout, stretch=3)
        
        # 오른쪽: 컨트롤
        control_panel = self._create_control_panel()
        main_layout.addWidget(control_panel, stretch=1)
        
        central_widget.setLayout(main_layout)
    
    def _create_control_panel(self):
        """컨트롤 패널 생성"""
        panel = QWidget()
        panel.setMaximumWidth(320)
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 제어 버튼 (상단)
        button_group = self._create_button_group()
        layout.addWidget(button_group)
        
        # 소스 선택
        source_group = self._create_source_group()
        layout.addWidget(source_group)
        
        # 비디오 파일 선택 (파일 모드일 때만 표시)
        self.video_file_group = self._create_video_file_group()
        layout.addWidget(self.video_file_group)
        
        # 모델 선택
        model_group = self._create_model_group()
        layout.addWidget(model_group)
        
        # 카메라/비디오 설정 위젯 (동적 교체)
        self.control_stack = QStackedWidget()
        
        # 카메라 위젯
        self.camera_widget = CameraControlWidget()
        self.camera_widget.resolution_changed.connect(self.on_resolution_changed)
        self.camera_widget.fps_changed.connect(self.on_fps_changed)
        self.camera_widget.exposure_changed.connect(self.on_exposure_changed)
        self.camera_widget.gain_changed.connect(self.on_gain_changed)
        self.control_stack.addWidget(self.camera_widget)
        
        # 비디오 위젯 (재생 속도만)
        self.video_widget = VideoControlWidget(self.video_files)
        self.video_widget.fps_changed.connect(self.on_fps_changed)
        self.control_stack.addWidget(self.video_widget)
        
        layout.addWidget(self.control_stack)
        layout.addStretch()
        
        panel.setLayout(layout)
        return panel
    
    def _create_button_group(self):
        """제어 버튼 그룹"""
        group = QGroupBox("제어")
        layout = QHBoxLayout()
        
        self.start_button = QPushButton("▶ 시작")
        self.start_button.clicked.connect(self.start_capture)
        self.start_button.setMinimumHeight(40)
        layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏸ 중지")
        self.stop_button.clicked.connect(self.stop_capture)
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumHeight(40)
        layout.addWidget(self.stop_button)
        
        self.quit_button = QPushButton("✕ 종료")
        self.quit_button.clicked.connect(self.close)
        self.quit_button.setMinimumHeight(40)
        layout.addWidget(self.quit_button)
        
        group.setLayout(layout)
        return group
    
    def _create_source_group(self):
        """소스 선택 그룹"""
        group = QGroupBox("입력 소스")
        layout = QHBoxLayout()
        
        self.source_button_group = QButtonGroup()
        self.camera_radio = QRadioButton("카메라")
        self.file_radio = QRadioButton("파일")
        self.camera_radio.setChecked(True)
        
        self.source_button_group.addButton(self.camera_radio)
        self.source_button_group.addButton(self.file_radio)
        self.camera_radio.toggled.connect(self.on_source_changed)
        
        layout.addWidget(self.camera_radio)
        layout.addWidget(self.file_radio)
        
        group.setLayout(layout)
        return group
    
    def _create_video_file_group(self):
        """비디오 파일 선택 그룹"""
        group = QGroupBox("비디오 파일")
        layout = QVBoxLayout()
        
        self.video_combo = QComboBox()
        for video_path in self.video_files:
            video_name = Path(video_path).name
            self.video_combo.addItem(video_name, video_path)
        layout.addWidget(self.video_combo)
        
        group.setLayout(layout)
        return group
    
    def _create_model_group(self):
        """모델 선택 그룹"""
        group = QGroupBox("YOLO 모델")
        layout = QVBoxLayout()
        
        self.model_combo = QComboBox()
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        layout.addWidget(self.model_combo)
        
        # Task 선택
        task_layout = QHBoxLayout()
        task_layout.addWidget(QLabel("Task:"))
        self.task_combo = QComboBox()
        self.task_combo.addItems(['detect', 'segment', 'classify', 'pose', 'obb'])
        self.task_combo.setCurrentText('detect')
        task_layout.addWidget(self.task_combo)
        layout.addLayout(task_layout)
        
        group.setLayout(layout)
        return group
    
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
    
    def _detect_task_from_name(self, model_path):
        """파일명에서 task 추론"""
        name = Path(model_path).stem.lower()
        
        if 'seg' in name or 'segment' in name:
            return 'segment'
        elif 'cls' in name or 'classify' in name:
            return 'classify'
        elif 'pose' in name:
            return 'pose'
        elif 'obb' in name:
            return 'obb'
        
        return 'detect'  # 기본값
    
    def _is_yoloe_model(self, model_path):
        """YOLOE 모델 감지"""
        return "yoloe" in Path(model_path).stem.lower()
    
    def _is_pt_file(self, model_path):
        """PyTorch 모델 파일인지 확인"""
        return Path(model_path).suffix.lower() == '.pt'
    
    def _setup_yoloe(self, classes):
        """YOLOE 프롬프트 설정"""
        try:
            # YOLO 객체 타입 확인
            if not hasattr(self.model, 'set_classes'):
                print(f"⚠️ 모델에 set_classes 메서드가 없습니다 (타입: {type(self.model)})")
                return
            
            if not hasattr(self.model, 'get_text_pe'):
                print(f"⚠️ 모델에 get_text_pe 메서드가 없습니다 - YOLOE 모델이 아닐 수 있습니다")
                return
                
            text_embeddings = self.model.get_text_pe(classes)
            self.model.set_classes(classes, text_embeddings)
            print(f"✅ YOLOE 프롬프트: {', '.join(classes)}")
        except Exception as e:
            print(f"⚠️ YOLOE 프롬프트 설정 실패: {e}")
            import traceback
            traceback.print_exc()
    
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
        
        # 비디오 파일 선택 표시/숨김
        self.video_file_group.setVisible(not is_camera)
        
        # 위젯 전환 (0: 카메라, 1: 비디오)
        self.control_stack.setCurrentIndex(0 if is_camera else 1)
        
        # 상태 메시지
        if is_camera:
            self.status_label.setText("카메라 모드 - 시작 버튼을 클릭하세요")
        else:
            self.status_label.setText("비디오 파일 모드 - 시작 버튼을 클릭하세요")
    
    def init_camera_early(self):
        """카메라 사전 초기화 (앱 시작 시 1회만)"""
        if self.source_type != 'camera':
            return
        
        try:
            self.camera = CameraController()
            self.camera.initialize()
            self.init_camera_controls()
            print("✅ 카메라 초기화 완료")
        except Exception as e:
            print(f"⚠️ 카메라 초기화 실패: {e}")
            self.status_label.setText(f"카메라를 찾을 수 없습니다 - 파일 모드를 사용하세요")
    
    def init_camera_controls(self):
        """카메라 컨트롤 초기화"""
        if not self.camera or self.source_type != 'camera':
            return
        
        try:
            # 해상도
            resolutions, current_index = self.camera.get_resolutions()
            self.camera_widget.setup_resolution(resolutions, current_index)
            
            # 노출 시간
            target_fps = 30
            max_exposure_ms = int(1000 / target_fps * 0.8)
            current_exposure = max_exposure_ms // 2
            self.camera_widget.setup_exposure(1, max_exposure_ms, current_exposure)
            
            # 수동 노출 설정
            self.camera.set_manual_exposure(current_exposure)
            print(f"✅ 수동 노출: {current_exposure}ms")
            
            # 게인
            gain_min, gain_max = self.camera.get_gain_range()
            current_gain = self.camera.get_current_gain()
            self.camera_widget.setup_gain(gain_min, gain_max, current_gain)
            
        except Exception as e:
            print(f"❌ 컨트롤 초기화 실패: {e}")
            self.status_label.setText(f"컨트롤 초기화 실패: {e}")
    
    def on_model_changed(self, index):
        """모델 변경"""
        if index < 0 or self.is_running:
            return
        
        model_path = self.model_combo.itemData(index)
        if model_path:
            # YOLOE 모델 처리
            if self._is_yoloe_model(model_path):
                self.model = YOLO(model_path)  # task 자동 감지
                
                # .pt 파일만 프롬프트 지원
                if self._is_pt_file(model_path):
                    self._setup_yoloe(["car"])
                    print(f"✅ 모델 변경: {Path(model_path).name} (YOLOE + prompt)")
                else:
                    print(f"✅ 모델 변경: {Path(model_path).name} (YOLOE prompt-free)")
                    print("ℹ️ TensorRT 엔진은 prompt-free 모드로 작동합니다")
            else:
                # 일반 YOLO 모델
                detected_task = self._detect_task_from_name(model_path)
                self.task_combo.setCurrentText(detected_task)
                
                task = self.task_combo.currentText()
                self.model = YOLO(model_path, task=task)
                print(f"✅ 모델 변경: {Path(model_path).name} (task={task})")
    
    def on_resolution_changed(self, resolution):
        """해상도 변경"""
        if self.is_running or not self.camera:
            return
        
        self.camera.set_resolution(resolution)
        self.frame_width = 0
        self.frame_height = 0
    
    def on_fps_changed(self, fps):
        """FPS 변경"""
        # 실행 중이면 타겟 FPS 업데이트
        if self.camera and self.is_running:
            self.camera.target_fps = fps
            # 비디오 모드면 타이머 간격도 업데이트
            if self.source_type == 'file' and hasattr(self.camera, '_update_timer_interval'):
                self.camera._update_timer_interval()
            print(f"🔄 FPS 변경: {fps}")
        
        # 카메라 모드일 때만 최대 노출 시간 업데이트
        if self.source_type == 'camera':
            self.camera_widget.update_max_exposure(fps)
    
    def on_exposure_changed(self, value_ms):
        """노출 시간 변경"""
        if self.camera:
            self.camera.set_exposure(value_ms)
    
    def on_gain_changed(self, value):
        """게인 변경"""
        if self.camera:
            self.camera.set_gain(value)
    
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
        if self.source_type == 'camera':
            target_fps = self.camera_widget.fps_slider.value()
        else:
            target_fps = self.video_widget.fps_slider.value()
        
        self.camera.start_trigger(target_fps)
        
        # UI 상태
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.model_combo.setEnabled(False)
        self.camera_radio.setEnabled(False)
        self.file_radio.setEnabled(False)
        
        status = "실시간 객체 탐지 중..." if self.source_type == 'camera' else "비디오 분석 중..."
        self.status_label.setText(status)
        
        print(f"\n🎬 시작 (타겟 FPS: {target_fps})")
    
    def _init_source(self):
        """소스 초기화 (카메라 또는 비디오)"""
        try:
            if self.source_type == 'camera':
                # 이미 초기화된 카메라가 있으면 재사용
                if self.camera and isinstance(self.camera, CameraController):
                    self.camera.signals.frame_ready.connect(self.on_camera_frame)
                    print("✅ 기존 카메라 사용")
                else:
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
        
        # 1. 프레임 처리 중지
        self.is_running = False
        self.camera.is_running = False
        
        # 2. 시그널 연결 해제 (중요!)
        try:
            self.camera.signals.frame_ready.disconnect(self.on_camera_frame)
        except:
            pass
        
        # 3. 트리거 중지
        self.camera.stop_trigger()
        
        # 4. 비디오 모드만 리소스 정리 (카메라는 유지)
        if self.source_type == 'file':
            self.camera.cleanup()
            self.camera = None
        
        # 5. UI 상태
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.model_combo.setEnabled(True)
        self.camera_radio.setEnabled(True)
        self.file_radio.setEnabled(True)
        self.status_label.setText("중지됨")
        
        print("✅ 중지 완료")
    
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

