#coding=utf-8
"""
YOLO 카메라 메인 윈도우
UI 레이아웃 및 이벤트 처리만 담당
"""
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QWidget, 
                                QPushButton, QHBoxLayout, QSizePolicy, QComboBox, 
                                QGroupBox, QRadioButton, QButtonGroup, QStackedWidget)
from PySide6.QtCore import Qt
from camera.camera_controller import CameraController
from camera.video_file_controller import VideoFileController
from ui.widgets.camera_control_widget import CameraControlWidget
from ui.widgets.video_control_widget import VideoControlWidget
from ui.model_manager import ModelManager
from ui.inference_engine import InferenceEngine
from ui.inference_worker import InferenceWorker


class YOLOCameraWindow(QMainWindow):
    """YOLO 카메라 윈도우 - UI 및 이벤트 처리"""
    
    def __init__(self, model_manager):
        """
        Args:
            model_manager: ModelManager 인스턴스
        """
        super().__init__()
        
        # 모델 관리
        self.model_manager = model_manager
        self.inference_engine = InferenceEngine(model_manager.current_model)
        
        # 추론 워커 (백그라운드 스레드)
        self.inference_worker = InferenceWorker(self.inference_engine)
        self.inference_worker.result_ready.connect(self._on_inference_result)
        
        # 소스 관리
        self.source = None
        self.source_type = 'camera'
        self.is_running = False
        
        # 프레임 통계
        self.skipped_frames = 0
        self.processed_frames = 0
        
        # 비디오 파일 목록
        self.video_files = self._scan_video_files()
        
        # 디스플레이 캐시
        self._pixmap_cache = None
        
        # UI 초기화
        self.setWindowTitle("YOLO Inference")
        self.setGeometry(100, 100, 1280, 720)
        self._init_ui()
        self._init_model_combo()
        self._update_source_ui()
        
        # 카메라 사전 초기화
        self._init_camera_early()
    
    def _init_ui(self):
        """UI 초기화"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        
        # 왼쪽: 비디오 디스플레이
        video_layout = self._create_video_layout()
        main_layout.addLayout(video_layout, stretch=3)
        
        # 오른쪽: 컨트롤 패널
        control_panel = self._create_control_panel()
        main_layout.addWidget(control_panel, stretch=1)
        
        central_widget.setLayout(main_layout)
    
    def _create_video_layout(self):
        """비디오 디스플레이 레이아웃"""
        layout = QVBoxLayout()
        
        # 비디오 라벨
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.video_label, stretch=1)
        
        # 상태 라벨
        self.status_label = QLabel("초기화 중...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        return layout
    
    def _create_control_panel(self):
        """컨트롤 패널"""
        panel = QWidget()
        panel.setMaximumWidth(320)
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 제어 버튼
        layout.addWidget(self._create_control_buttons())
        
        # 소스 선택 (카메라/파일)
        layout.addWidget(self._create_source_selector())
        
        # 비디오 파일 선택 (파일 모드에서만 표시)
        self.video_file_group = self._create_video_file_selector()
        layout.addWidget(self.video_file_group)
        
        # 모델 선택
        layout.addWidget(self._create_model_selector())
        
        # 카메라/비디오 설정 위젯 (동적 교체)
        layout.addWidget(self._create_settings_stack())
        
        layout.addStretch()
        panel.setLayout(layout)
        return panel
    
    def _create_control_buttons(self):
        """제어 버튼 그룹"""
        group = QGroupBox("제어")
        layout = QHBoxLayout()
        
        self.start_button = QPushButton("▶ 시작")
        self.start_button.clicked.connect(self._on_start)
        self.start_button.setMinimumHeight(40)
        layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏸ 중지")
        self.stop_button.clicked.connect(self._on_stop)
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumHeight(40)
        layout.addWidget(self.stop_button)
        
        self.quit_button = QPushButton("✕ 종료")
        self.quit_button.clicked.connect(self.close)
        self.quit_button.setMinimumHeight(40)
        layout.addWidget(self.quit_button)
        
        group.setLayout(layout)
        return group
    
    def _create_source_selector(self):
        """입력 소스 선택"""
        group = QGroupBox("입력 소스")
        layout = QHBoxLayout()
        
        self.source_button_group = QButtonGroup()
        self.camera_radio = QRadioButton("카메라")
        self.file_radio = QRadioButton("파일")
        self.camera_radio.setChecked(True)
        
        self.source_button_group.addButton(self.camera_radio)
        self.source_button_group.addButton(self.file_radio)
        self.camera_radio.toggled.connect(self._on_source_changed)
        
        layout.addWidget(self.camera_radio)
        layout.addWidget(self.file_radio)
        group.setLayout(layout)
        return group
    
    def _create_video_file_selector(self):
        """비디오 파일 선택"""
        group = QGroupBox("비디오 파일")
        layout = QVBoxLayout()
        
        self.video_combo = QComboBox()
        for video_path in self.video_files:
            video_name = Path(video_path).name
            self.video_combo.addItem(video_name, video_path)
        layout.addWidget(self.video_combo)
        
        group.setLayout(layout)
        return group
    
    def _create_model_selector(self):
        """모델 선택"""
        group = QGroupBox("YOLO 모델")
        layout = QVBoxLayout()
        
        self.model_combo = QComboBox()
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
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
    
    def _create_settings_stack(self):
        """설정 위젯 스택 (카메라/비디오 전환)"""
        self.control_stack = QStackedWidget()
        
        # 카메라 위젯
        self.camera_widget = CameraControlWidget()
        self.camera_widget.resolution_changed.connect(self._on_resolution_changed)
        self.camera_widget.fps_changed.connect(self._on_fps_changed)
        self.camera_widget.exposure_changed.connect(self._on_exposure_changed)
        self.camera_widget.gain_changed.connect(self._on_gain_changed)
        self.control_stack.addWidget(self.camera_widget)
        
        # 비디오 위젯
        self.video_widget = VideoControlWidget(self.video_files)
        self.video_widget.fps_changed.connect(self._on_fps_changed)
        self.control_stack.addWidget(self.video_widget)
        
        return self.control_stack
    
    def _init_model_combo(self):
        """모델 콤보박스 초기화"""
        for model_name, model_path in self.model_manager.model_list:
            self.model_combo.addItem(model_name, model_path)
    
    def _scan_video_files(self):
        """비디오 파일 스캔"""
        samples_dir = Path(__file__).parent.parent / "samples"
        if not samples_dir.exists():
            return []
        
        extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        video_files = []
        for ext in extensions:
            video_files.extend(samples_dir.glob(f"*{ext}"))
        
        return sorted([str(f) for f in video_files])
    
    def _init_camera_early(self):
        """카메라 사전 초기화 (앱 시작 시)"""
        if self.source_type != 'camera':
            return
        
        try:
            self.source = CameraController()
            self.source.initialize()
            self._setup_camera_controls()
            print("✅ 카메라 초기화 완료")
        except Exception as e:
            print(f"⚠️ 카메라 초기화 실패: {e}")
            self.status_label.setText("카메라를 찾을 수 없습니다 - 파일 모드를 사용하세요")
    
    def _setup_camera_controls(self):
        """카메라 컨트롤 초기화"""
        if not self.source or self.source_type != 'camera':
            return
        
        try:
            # 해상도
            resolutions, current_index = self.source.get_resolutions()
            self.camera_widget.setup_resolution(resolutions, current_index)
            
            # 노출 시간
            target_fps = 30
            max_exposure_ms = int(1000 / target_fps * 0.8)
            current_exposure = max_exposure_ms // 2
            self.camera_widget.setup_exposure(1, max_exposure_ms, current_exposure)
            self.source.set_manual_exposure(current_exposure)
            print(f"✅ 수동 노출: {current_exposure}ms")
            
            # 게인
            gain_min, gain_max = self.source.get_gain_range()
            current_gain = self.source.get_current_gain()
            self.camera_widget.setup_gain(gain_min, gain_max, current_gain)
            
        except Exception as e:
            print(f"❌ 컨트롤 초기화 실패: {e}")
            self.status_label.setText(f"컨트롤 초기화 실패: {e}")
    
    # ========== 이벤트 핸들러 ==========
    
    def _on_source_changed(self):
        """소스 변경 (카메라 ↔ 파일)"""
        if self.is_running:
            return
        
        self.source_type = 'camera' if self.camera_radio.isChecked() else 'file'
        self._update_source_ui()
    
    def _update_source_ui(self):
        """소스에 따른 UI 업데이트"""
        is_camera = self.source_type == 'camera'
        
        # 비디오 파일 선택 표시/숨김
        self.video_file_group.setVisible(not is_camera)
        
        # 설정 위젯 전환 (0: 카메라, 1: 비디오)
        self.control_stack.setCurrentIndex(0 if is_camera else 1)
        
        # 상태 메시지
        mode = "카메라" if is_camera else "비디오 파일"
        self.status_label.setText(f"{mode} 모드 - 시작 버튼을 클릭하세요")
    
    def _on_model_changed(self, index):
        """모델 변경"""
        if index < 0 or self.is_running:
            return
        
        model_path = self.model_combo.itemData(index)
        if not model_path:
            return
        
        # 모델 전환
        task = self.task_combo.currentText() if not self.model_manager._is_yoloe_model(model_path) else None
        new_model = self.model_manager.switch_model(model_path, task)
        
        # 추론 엔진 업데이트
        self.inference_engine.model = new_model
        
        # Task 콤보박스 업데이트 (일반 YOLO)
        if not self.model_manager._is_yoloe_model(model_path):
            detected_task = self.model_manager._detect_task(model_path)
            self.task_combo.setCurrentText(detected_task)
        
        print(f"✅ 모델 변경: {Path(model_path).name}")
    
    def _on_resolution_changed(self, resolution):
        """해상도 변경"""
        if self.is_running or not self.source:
            return
        
        self.source.set_resolution(resolution)
    
    def _on_fps_changed(self, fps):
        """FPS 변경"""
        if not self.source or not self.is_running:
            return
        
        self.source.target_fps = fps
        
        # 비디오 모드면 타이머 간격도 업데이트
        if self.source_type == 'file' and hasattr(self.source, '_update_timer_interval'):
            self.source._update_timer_interval()
        
        # 카메라 모드면 최대 노출 시간 업데이트
        if self.source_type == 'camera':
            self.camera_widget.update_max_exposure(fps)
        
        print(f"🔄 FPS 변경: {fps}")
    
    def _on_exposure_changed(self, value_ms):
        """노출 시간 변경"""
        if self.source:
            self.source.set_exposure(value_ms)
    
    def _on_gain_changed(self, value):
        """게인 변경"""
        if self.source:
            self.source.set_gain(value)
    
    def _on_frame_ready(self, frame_bgr):
        """
        프레임 콜백 - 워커 스레드에 프레임 전달 (메인 스레드 블로킹 없음)
        
        Note: 워커가 추론 중이면 이전 프레임을 덮어씀 (항상 최신 프레임 유지)
        """
        if not self.is_running:
            return
        
        # 워커가 추론 중이면 프레임 스킵
        if self.inference_worker.processing:
            self.skipped_frames += 1
            return
        
        # 워커에 프레임 제출 (비동기)
        self.processed_frames += 1
        self.inference_worker.submit_frame(frame_bgr)
    
    def _on_inference_result(self, q_image, stats):
        """
        추론 결과 콜백 (워커 스레드에서 발생, 메인 스레드에서 실행)
        
        Args:
            q_image: 시각화된 QImage
            stats: 통계 딕셔너리
        """
        if not self.is_running:
            return
        
        # 프레임 스킵 정보 추가
        stats['skipped_frames'] = self.skipped_frames
        stats['processed_frames'] = self.processed_frames
        
        # 디스플레이
        self._display_frame(q_image)
        
        # 상태 표시
        self._update_status_label(stats)
    
    def _display_frame(self, q_image):
        """프레임 디스플레이 (캐시 사용)"""
        label_size = self.video_label.size()
        scaled_pixmap, cache_key = InferenceEngine.scale_pixmap(
            q_image, label_size, self._pixmap_cache
        )
        
        self._pixmap_cache = (cache_key, scaled_pixmap)
        self.video_label.setPixmap(scaled_pixmap)
    
    def _update_status_label(self, stats):
        """상태 라벨 업데이트"""
        text = (f"FPS: {stats['fps']:.1f} | "
                f"추론: {stats['infer_time']:.1f}ms "
                f"(평균: {stats['avg_infer_time']:.1f}ms) | "
                f"탐지: {stats['detected_count']} | "
                f"해상도: {stats['frame_width']}x{stats['frame_height']}")
        
        # 프레임 스킵 정보 (스킵이 있을 때만 표시)
        if stats.get('skipped_frames', 0) > 0:
            skip_rate = stats['skipped_frames'] / (stats['processed_frames'] + stats['skipped_frames']) * 100
            text += f" | ⚠️ 스킵: {stats['skipped_frames']}개 ({skip_rate:.1f}%)"
        
        self.status_label.setText(text)
    
    def _on_start(self):
        """캡처 시작"""
        # 소스 초기화
        if not self._init_source():
            return
        
        # 상태 초기화
        self.is_running = True
        self.source.is_running = True
        self.skipped_frames = 0
        self.processed_frames = 0
        self.inference_engine.reset_stats()
        self._pixmap_cache = None
        
        # 워커 스레드 시작
        if not self.inference_worker.isRunning():
            self.inference_worker.start()
        
        # FPS 설정
        target_fps = (self.camera_widget.fps_slider.value() if self.source_type == 'camera' 
                      else self.video_widget.fps_slider.value())
        
        # 소스 시작
        self.source.start_trigger(target_fps)
        
        # UI 업데이트
        self._set_ui_running(True)
        
        mode = "실시간 객체 탐지" if self.source_type == 'camera' else "비디오 분석"
        self.status_label.setText(f"{mode} 중...")
        print(f"\n🎬 시작 (타겟 FPS: {target_fps})")
    
    def _init_source(self):
        """소스 초기화 (카메라 또는 비디오)"""
        try:
            if self.source_type == 'camera':
                # 이미 초기화된 카메라 재사용
                if self.source and isinstance(self.source, CameraController):
                    self.source.signals.frame_ready.connect(self._on_frame_ready)
                    print("✅ 기존 카메라 사용")
                else:
                    self.source = CameraController()
                    self.source.initialize()
                    self.source.signals.frame_ready.connect(self._on_frame_ready)
                    self._setup_camera_controls()
                    print("✅ 카메라 초기화 완료")
            else:
                # 비디오 파일
                video_path = self.video_combo.currentData()
                if not video_path:
                    self.status_label.setText("비디오 파일을 선택하세요")
                    return False
                
                self.source = VideoFileController(video_path)
                self.source.initialize()
                self.source.signals.frame_ready.connect(self._on_frame_ready)
                print(f"✅ 비디오 초기화 완료: {Path(video_path).name}")
            
            return True
            
        except Exception as e:
            source_name = "카메라" if self.source_type == 'camera' else "비디오"
            print(f"❌ {source_name} 초기화 실패: {e}")
            self.status_label.setText(f"{source_name} 초기화 실패: {e}")
            return False
    
    def _on_stop(self):
        """캡처 중지"""
        if not self.source:
            return
        
        # 상태 변경
        self.is_running = False
        self.source.is_running = False
        
        # 시그널 연결 해제
        try:
            self.source.signals.frame_ready.disconnect(self._on_frame_ready)
        except:
            pass
        
        # 소스 중지
        self.source.stop_trigger()
        
        # 비디오 모드만 리소스 정리 (카메라는 유지)
        if self.source_type == 'file':
            self.source.cleanup()
            self.source = None
        
        # UI 업데이트
        self._set_ui_running(False)
        self.status_label.setText("중지됨")
        print("✅ 중지 완료")
    
    def _set_ui_running(self, running):
        """UI 실행 상태 설정"""
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.model_combo.setEnabled(not running)
        self.camera_radio.setEnabled(not running)
        self.file_radio.setEnabled(not running)
    
    # ========== Qt 이벤트 ==========
    
    def resizeEvent(self, event):
        """윈도우 크기 변경"""
        super().resizeEvent(event)
        self._pixmap_cache = None
    
    def closeEvent(self, event):
        """윈도우 종료"""
        if self.is_running:
            self._on_stop()
        
        # 워커 스레드 종료
        if self.inference_worker.isRunning():
            self.inference_worker.stop()
        
        if self.source:
            self.source.cleanup()
        
        event.accept()
