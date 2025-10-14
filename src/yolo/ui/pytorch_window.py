#coding=utf-8
"""
PyTorch 전용 윈도우
모델 정보 + 클래스 목록 표시 + 카메라/비디오 제어
"""
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QWidget, 
                                QPushButton, QHBoxLayout, QSizePolicy, QComboBox, 
                                QGroupBox, QRadioButton, QButtonGroup, 
                                QTextEdit, QScrollArea)
from PySide6.QtCore import Qt
from camera.camera_controller import CameraController
from camera.video_file_controller import VideoFileController
from ui.widgets.camera_control_widget import CameraControlWidget
from ui.widgets.video_control_widget import VideoControlWidget
from ui.widgets.inference_config_widget import InferenceConfigWidget
from inference.engine import InferenceEngine
from inference.worker import InferenceWorker
from inference.config import PTConfig


class PyTorchWindow(QMainWindow):
    """PyTorch 전용 윈도우"""
    
    def __init__(self, model_manager):
        super().__init__()
        
        self.model_manager = model_manager
        self.inference_config = PTConfig()
        self.inference_engine = InferenceEngine(
            model_manager.current_model,
            model_manager.model_list[0][1] if model_manager.model_list else None,
            self.inference_config
        )
        
        self.inference_worker = InferenceWorker(self.inference_engine)
        self.inference_worker.result_ready.connect(self._on_inference_result)
        
        self.source = None
        self.source_type = 'camera'
        self.is_running = False
        self.is_paused = False
        self.video_files = self._scan_video_files()
        self._pixmap_cache = None
        
        self.setWindowTitle("YOLO PyTorch Model")
        self.setGeometry(100, 100, 1400, 720)
        self._init_ui()
        self._update_source_ui()
        self._init_camera_early()
    
    def _init_ui(self):
        """UI 초기화"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        
        # 왼쪽: 비디오 디스플레이
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
        
        # 오른쪽: 컨트롤 패널
        control_panel = self._create_control_panel()
        main_layout.addWidget(control_panel, stretch=1)
        
        central_widget.setLayout(main_layout)
    
    def _create_control_panel(self):
        """컨트롤 패널"""
        panel = QWidget()
        panel.setMaximumWidth(350)
        layout = QVBoxLayout()
        
        # 모델 정보
        layout.addWidget(self._create_model_info())
        
        # 소스 선택
        layout.addWidget(self._create_source_selector())
        
        # 비디오 파일 선택
        self.video_file_group = self._create_video_file_selector()
        layout.addWidget(self.video_file_group)
        
        # 모델 선택
        layout.addWidget(self._create_model_selector())
        
        # 추론 설정
        self.inference_config_widget = InferenceConfigWidget(self.inference_config)
        self.inference_config_widget.config_changed.connect(self._on_inference_config_changed)
        layout.addWidget(self.inference_config_widget)
        
        # 카메라 제어
        self.camera_widget = CameraControlWidget()
        self.camera_widget.start_camera.connect(self._on_start_camera)
        self.camera_widget.stop_camera.connect(self._on_stop_camera)
        layout.addWidget(self.camera_widget)
        
        # 비디오 제어
        self.video_widget = VideoControlWidget(self.video_files)
        self.video_widget.play_pause.connect(self._on_video_play_pause)
        self.video_widget.stop.connect(self._on_video_stop)
        self.video_widget.step_frame.connect(self._on_step_frame)
        self.video_widget.seek_requested.connect(self._on_seek_frame)
        self.video_widget.fps_changed.connect(self._on_fps_changed)
        self.video_widget.loop_changed.connect(self._on_loop_changed)
        layout.addWidget(self.video_widget)
        
        # 초기 상태 설정
        self._update_control_visibility()
        layout.addStretch()
        
        panel.setLayout(layout)
        return panel
    
    def _create_model_info(self):
        """모델 정보 위젯"""
        group = QGroupBox("PyTorch 모델 정보")
        layout = QVBoxLayout()
        
        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(300)
        
        info_widget = QWidget()
        info_layout = QVBoxLayout()
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        
        # 모델 정보 표시
        model = self.model_manager.current_model
        model_path = self.model_manager.model_list[0][1]
        
        info_text = self._get_model_info(model, model_path)
        self.info_text.setText(info_text)
        
        info_layout.addWidget(self.info_text)
        info_widget.setLayout(info_layout)
        scroll.setWidget(info_widget)
        
        layout.addWidget(scroll)
        group.setLayout(layout)
        return group
    
    def _get_model_info(self, model, model_path):
        """모델 상세 정보 생성"""
        info = []
        
        # 기본 정보
        info.append(f"📄 파일: {Path(model_path).name}")
        file_size_mb = Path(model_path).stat().st_size / (1024 * 1024)
        info.append(f"💾 크기: {file_size_mb:.1f} MB")
        
        if hasattr(model, 'task'):
            info.append(f"🎯 Task: {model.task}")
        
        # 파라미터 수
        if hasattr(model, 'model'):
            try:
                total_params = sum(p.numel() for p in model.model.parameters())
                info.append(f"⚙️ 파라미터: {total_params:,}")
            except:
                pass
        
        # 클래스 목록 전체 표시
        if hasattr(model, 'names'):
            info.append(f"\n📋 클래스 ({len(model.names)}개):")
            for idx, name in model.names.items():
                info.append(f"  {idx}: {name}")
        
        return '\n'.join(info)
    
    def _create_control_buttons(self):
        """제어 버튼"""
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
        """소스 선택"""
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
        group = QGroupBox("모델 선택")
        layout = QVBoxLayout()
        
        # Task 선택 (먼저 생성)
        task_layout = QHBoxLayout()
        task_layout.addWidget(QLabel("Task:"))
        self.task_combo = QComboBox()
        self.task_combo.addItems(['detect', 'segment', 'classify', 'pose', 'obb'])
        self.task_combo.setCurrentText('detect')
        task_layout.addWidget(self.task_combo)
        layout.addLayout(task_layout)
        
        # 모델 콤보박스 (나중에 생성)
        self.model_combo = QComboBox()
        
        for model_name, model_path in self.model_manager.model_list:
            self.model_combo.addItem(model_name, model_path)
        
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        layout.addWidget(self.model_combo)
        
        group.setLayout(layout)
        return group
    
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
        """카메라 사전 초기화"""
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
            resolutions, current_index = self.source.get_resolutions()
            self.camera_widget.setup_resolution(resolutions, current_index)
            print("✅ 카메라 컨트롤 초기화 완료")
        except Exception as e:
            print(f"❌ 컨트롤 초기화 실패: {e}")
            self.status_label.setText(f"컨트롤 초기화 실패: {e}")
    
    def _on_source_changed(self):
        """소스 변경"""
        if self.is_running or self.is_paused:
            return
        
        self.source_type = 'camera' if self.camera_radio.isChecked() else 'file'
        self._update_source_ui()
        self._update_control_visibility()
    
    def _update_source_ui(self):
        """소스에 따른 UI 업데이트"""
        is_camera = self.source_type == 'camera'
        self.video_file_group.setVisible(not is_camera)
        
        mode = "카메라" if is_camera else "비디오 파일"
        self.status_label.setText(f"{mode} 모드")
    
    def _update_control_visibility(self):
        """소스에 따른 컨트롤 가시성"""
        is_camera = self.source_type == 'camera'
        self.camera_widget.setVisible(is_camera)
        self.video_widget.setVisible(not is_camera)
    
    def _on_model_changed(self, index):
        """모델 변경"""
        if index < 0 or self.is_running:
            return
        
        model_path = self.model_combo.itemData(index)
        if not model_path:
            return
        
        # 모델 전환
        task = self.task_combo.currentText()
        new_model = self.model_manager.switch_model(model_path, task)
        
        # 추론 엔진 업데이트
        self.inference_engine.model = new_model
        self.inference_engine.model_path = model_path
        self.inference_engine.is_engine = False
        
        # 정보 업데이트
        self._update_model_info(new_model, model_path)
        
        print(f"✅ 모델 변경: {Path(model_path).name}")
    
    def _update_model_info(self, model, model_path):
        """모델 정보 업데이트"""
        info_text = self._get_model_info(model, model_path)
        self.info_text.setText(info_text)
    
    def _on_start_camera(self):
        """카메라 시작"""
        if not self._init_source():
            self.camera_widget._on_stop()
            return
        
        self.is_running = True
        self.is_paused = False
        self.source.is_running = True
        self.inference_engine.reset_stats()
        self._pixmap_cache = None
        
        if not self.inference_worker.isRunning():
            self.inference_worker.start()
        
        self.source.start_trigger()
        self.status_label.setText("실행 중...")
        print("\n🎬 카메라 시작")
    
    def _on_stop_camera(self):
        """카메라 중지"""
        self._on_stop()
    
    def _on_video_play_pause(self):
        """비디오 재생/일시정지"""
        if self.is_paused:
            self._on_resume()
        elif self.is_running:
            self._on_pause()
        else:
            self._on_start()
    
    def _on_video_stop(self):
        """비디오 중지"""
        self._on_stop()
    
    def _on_step_frame(self, delta):
        """프레임 단위 이동 (일시정지 중에만)"""
        if not self.is_paused or not self.source or self.source_type != 'file':
            return
        
        frame = self.source.step_frame(delta)
        if frame is not None:
            self._process_single_frame(frame)
    
    def _on_seek_frame(self, frame_number):
        """특정 프레임으로 이동"""
        if not self.source or self.source_type != 'file':
            return
        
        # 재생 중이면 일시적으로 멈추고 탐색
        was_running = self.is_running
        if was_running:
            self.source.stop_trigger()
        
        self.source.seek_frame(frame_number)
        
        # 일시정지 중이면 프레임 표시
        if self.is_paused:
            frame = self.source.step_frame(0)
            if frame is not None:
                self._process_single_frame(frame)
        
        # 재생 중이었으면 다시 시작
        if was_running:
            target_fps = self.video_widget.fps_slider.value()
            self.source.start_trigger(target_fps)
    
    def _on_loop_changed(self, loop):
        """루프 설정 변경"""
        if self.source and self.source_type == 'file':
            self.source.loop = loop
            print(f"✅ 루프 재생: {loop}")
    
    def _on_progress_updated(self, current_frame, total_frames, time_sec):
        """진행률 업데이트"""
        self.video_widget.update_progress(current_frame, total_frames, time_sec)
    
    def _reprocess_current_frame(self):
        """현재 프레임 재추론 (일시정지 중)"""
        if not self.source or self.source_type != 'file':
            return
        
        frame = self.source.get_current_frame()
        if frame is not None:
            self._process_single_frame(frame)
    
    def _process_single_frame(self, frame):
        """단일 프레임 추론 (일시정지용)"""
        q_image, stats = self.inference_engine.process_frame(frame)
        self._display_frame(q_image)
        self._update_status_label(stats)
    
    def _on_fps_changed(self, fps):
        """FPS 변경"""
        if not self.source or not self.is_running or self.source_type != 'file':
            return
        
        self.source.target_fps = fps
        if hasattr(self.source, '_update_timer_interval'):
            self.source._update_timer_interval()
    
    def _on_inference_config_changed(self, config):
        """추론 설정 변경 (재생/일시정지 중 모두 적용)"""
        self.inference_config = config
        self.inference_engine.config = config
        print(f"✅ 추론 설정: conf={config.conf:.2f}, iou={config.iou:.2f}, "
              f"imgsz={config.imgsz}, max_det={config.max_det}, augment={config.augment}")
        
        # 일시정지 중이면 현재 프레임 재추론 (재생 중에는 자동 적용)
        if hasattr(self, 'is_paused') and self.is_paused and self.source and self.source_type == 'file':
            if hasattr(self, '_reprocess_current_frame'):
                self._reprocess_current_frame()
    
    def _on_frame_ready(self, frame_bgr):
        """프레임 콜백"""
        if not self.is_running or self.inference_worker.processing:
            return
        
        self.inference_worker.submit_frame(frame_bgr)
    
    def _on_inference_result(self, q_image, stats):
        """추론 결과 콜백"""
        if not self.is_running:
            return
        
        self._display_frame(q_image)
        self._update_status_label(stats)
    
    def _display_frame(self, q_image):
        """프레임 디스플레이"""
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
        self.status_label.setText(text)
    
    def _on_start(self):
        """비디오 시작"""
        if not self._init_source():
            return
        
        self.is_running = True
        self.is_paused = False
        self.source.is_running = True
        self.inference_engine.reset_stats()
        self._pixmap_cache = None
        
        if not self.inference_worker.isRunning():
            self.inference_worker.start()
        
        target_fps = self.video_widget.fps_slider.value()
        self.source.start_trigger(target_fps)
        
        self.video_widget.set_playing(True)
        self.video_widget.set_controls_enabled(False)
        self.status_label.setText("실행 중...")
        print(f"\n🎬 비디오 시작 (FPS: {target_fps})")
    
    def _on_pause(self):
        """일시정지 (비디오만)"""
        if not self.is_running:
            return
        
        self.is_paused = True
        self.is_running = False
        self.source.is_running = False
        self.source.stop_trigger()
        
        self.video_widget.set_playing(False)
        self.video_widget.set_controls_enabled(True)
        self.status_label.setText("일시정지")
        print("⏸ 일시정지")
    
    def _on_resume(self):
        """재개 (일시정지 해제)"""
        if not self.is_paused:
            return
        
        self.is_paused = False
        self.is_running = True
        self.source.is_running = True
        
        target_fps = self.video_widget.fps_slider.value()
        self.source.start_trigger(target_fps)
        
        self.video_widget.set_playing(True)
        self.video_widget.set_controls_enabled(False)
        self.status_label.setText("실행 중...")
        print("▶ 재개")
    
    def _init_source(self):
        """소스 초기화"""
        try:
            if self.source_type == 'camera':
                if self.source and isinstance(self.source, CameraController):
                    self.source.signals.frame_ready.connect(self._on_frame_ready)
                else:
                    self.source = CameraController()
                    self.source.initialize()
                    self.source.signals.frame_ready.connect(self._on_frame_ready)
                    self._setup_camera_controls()
            else:
                video_path = self.video_combo.currentData()
                if not video_path:
                    self.status_label.setText("비디오 파일을 선택하세요")
                    return False
                
                self.source = VideoFileController(video_path)
                self.source.initialize()
                self.source.signals.frame_ready.connect(self._on_frame_ready)
                self.source.signals.progress_updated.connect(self._on_progress_updated)
                # 비디오 정보 전달
                self.video_widget.set_video_info(self.source.total_frames, self.source.video_fps)
            
            return True
        except Exception as e:
            print(f"❌ 소스 초기화 실패: {e}")
            self.status_label.setText(f"초기화 실패: {e}")
            return False
    
    def _on_stop(self):
        """중지 (완전 정지, 소스 해제)"""
        if not self.source:
            return
        
        self.is_running = False
        self.is_paused = False
        self.source.is_running = False
        
        try:
            self.source.signals.frame_ready.disconnect(self._on_frame_ready)
        except:
            pass
        
        try:
            if self.source_type == 'file':
                self.source.signals.progress_updated.disconnect(self._on_progress_updated)
        except:
            pass
        
        self.source.stop_trigger()
        
        if self.source_type == 'camera':
            # 카메라는 cleanup하지 않음
            pass
        else:
            self.source.cleanup()
            self.source = None
            self.video_widget.set_playing(False)
            self.video_widget.set_controls_enabled(False)
        
        self.video_label.clear()
        self.status_label.setText("중지됨")
        print("⏹ 중지")
    
    
    def resizeEvent(self, event):
        """윈도우 크기 변경"""
        super().resizeEvent(event)
        self._pixmap_cache = None
    
    def closeEvent(self, event):
        """윈도우 종료"""
        if self.is_running:
            self._on_stop()
        
        if self.inference_worker.isRunning():
            self.inference_worker.stop()
        
        if self.source:
            self.source.cleanup()
        
        event.accept()

