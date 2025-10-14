#coding=utf-8
"""
비디오 파일 제어 위젯
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QGroupBox, QPushButton, QCheckBox, QSpinBox)
from PySide6.QtCore import Qt, Signal
from ui.widgets.click_slider import ClickSlider


class VideoControlWidget(QGroupBox):
    """비디오 파일 전용 제어 위젯"""
    
    # 시그널
    play_pause = Signal()  # 재생/일시정지 토글
    stop = Signal()  # 중지
    step_frame = Signal(int)  # delta (-1 또는 +1)
    seek_requested = Signal(int)  # frame_number
    fps_changed = Signal(int)
    loop_changed = Signal(bool)
    
    def __init__(self, video_files=None, parent=None):
        super().__init__("동영상 제어", parent)
        self.total_frames = 0
        self.video_fps = 30.0
        self.is_playing = False
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 제어 버튼
        btn_layout = QHBoxLayout()
        self.play_pause_btn = QPushButton("▶ 재생")
        self.play_pause_btn.setMinimumHeight(35)
        self.play_pause_btn.clicked.connect(self._on_play_pause)
        btn_layout.addWidget(self.play_pause_btn)
        
        self.stop_btn = QPushButton("⏹ 중지")
        self.stop_btn.setMinimumHeight(35)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop.emit)
        btn_layout.addWidget(self.stop_btn)
        layout.addLayout(btn_layout)
        
        # 프레임 정보 및 진행률
        info_layout = QHBoxLayout()
        self.frame_label = QLabel("프레임: 0 / 0")
        info_layout.addWidget(self.frame_label)
        info_layout.addStretch()
        self.time_label = QLabel("00:00.000")
        info_layout.addWidget(self.time_label)
        layout.addLayout(info_layout)
        
        # 진행률 바 (클릭 즉시 이동)
        self.progress_slider = ClickSlider(Qt.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)
        self.progress_slider.setValue(0)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.slider_dragging = False
        layout.addWidget(self.progress_slider)
        
        # 프레임 이동 + 속도
        control_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setMaximumWidth(40)
        self.prev_btn.clicked.connect(lambda: self.step_frame.emit(-1))
        control_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("▶")
        self.next_btn.setMaximumWidth(40)
        self.next_btn.clicked.connect(lambda: self.step_frame.emit(1))
        control_layout.addWidget(self.next_btn)
        
        control_layout.addWidget(QLabel("속도:"))
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setMinimum(1)
        self.fps_spinbox.setMaximum(120)
        self.fps_spinbox.setValue(30)
        self.fps_spinbox.setSuffix(" FPS")
        self.fps_spinbox.valueChanged.connect(self.fps_changed.emit)
        control_layout.addWidget(self.fps_spinbox)
        
        self.loop_checkbox = QCheckBox("루프")
        self.loop_checkbox.setChecked(True)
        self.loop_checkbox.toggled.connect(self.loop_changed.emit)
        control_layout.addWidget(self.loop_checkbox)
        
        layout.addLayout(control_layout)
        self.setLayout(layout)
    
    def _on_play_pause(self):
        """재생/일시정지 토글"""
        self.play_pause.emit()
    
    def _on_slider_pressed(self):
        """슬라이더 드래그 시작"""
        self.slider_dragging = True
    
    def _on_slider_moved(self, value):
        """슬라이더 이동 중 - 프레임 미리보기"""
        if self.total_frames > 0:
            frame_number = int(value * self.total_frames / 1000)
            self._update_display(frame_number, self.total_frames)
    
    def _on_slider_released(self):
        """슬라이더 릴리즈 - 해당 위치로 탐색"""
        self.slider_dragging = False
        if self.total_frames > 0:
            frame_number = int(self.progress_slider.value() * self.total_frames / 1000)
            self.seek_requested.emit(frame_number)
    
    def update_progress(self, current_frame, total_frames, time_sec):
        """진행률 업데이트"""
        self.total_frames = total_frames
        
        # 슬라이더 드래그 중이 아닐 때만 업데이트
        if not self.slider_dragging and total_frames > 0:
            progress = int(current_frame * 1000 / total_frames)
            self.progress_slider.setValue(progress)
        
        self._update_display(current_frame, total_frames, time_sec)
    
    def _update_display(self, current_frame, total_frames, time_sec=None):
        """프레임 및 시간 표시 업데이트"""
        # 프레임 표시
        self.frame_label.setText(f"프레임: {current_frame} / {total_frames}")
        
        # 시간 표시 (밀리초 단위)
        if time_sec is None:
            time_sec = current_frame / self.video_fps if self.video_fps > 0 else 0
        
        ms = int((time_sec % 1) * 1000)
        secs = int(time_sec % 60)
        mins = int(time_sec // 60)
        self.time_label.setText(f"{mins:02d}:{secs:02d}.{ms:03d}")
    
    def set_controls_enabled(self, paused):
        """일시정지 중 컨트롤 활성화"""
        self.prev_btn.setEnabled(paused)
        self.next_btn.setEnabled(paused)
    
    def set_playing(self, playing):
        """재생 상태 업데이트"""
        self.is_playing = playing
        self.play_pause_btn.setText("⏸ 일시정지" if playing else "▶ 재생")
        self.stop_btn.setEnabled(playing or not playing)  # 항상 활성화
    
    def set_video_info(self, total_frames, video_fps):
        """비디오 정보 설정"""
        self.total_frames = total_frames
        self.video_fps = video_fps
        self._update_display(0, total_frames, 0)
    
    @property
    def fps_slider(self):
        """하위 호환성 - fps_spinbox 반환"""
        return self.fps_spinbox

