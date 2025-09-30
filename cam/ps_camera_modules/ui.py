#coding=utf-8
"""UI 구성"""
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, 
                              QWidget, QLabel, QSlider, QPushButton)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter

class FastCameraWidget(QWidget):
    """비동기 카메라 표시 위젯 - 최적화된 QPainter 기반"""
    def __init__(self):
        super().__init__()
        self.current_pixmap = None
        self.next_pixmap = None  # 비동기 버퍼
        self.is_updating = False
        self.setFixedSize(640, 480) # 확대 축소 되지 않는 사이즈 조정
        
        # 더블 버퍼링과 비동기 렌더링 최적화
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WA_PaintOnScreen, False)  # 더블 버퍼링 강제
        
        # 비동기 업데이트 타이머 (프레임 드롭 방지)
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._apply_next_frame)
    
    def paintEvent(self, event):
        """비동기 페인트 이벤트 - 최적화된 렌더링"""
        painter = QPainter(self)
        
        # 렌더링 힌트 비활성화로 성능 향상
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.TextAntialiasing, False)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        
        if self.current_pixmap and not self.current_pixmap.isNull():
            # 직접 픽셀맵 복사 (스케일링 없음)
            painter.drawPixmap(0, 0, self.current_pixmap)
        else:
            # 검은 화면 - 빠른 채우기
            painter.fillRect(self.rect(), Qt.black)
    
    def update_frame(self, q_image):
        """비동기 프레임 업데이트 - VSync와 연동"""
        if self.is_updating:
            # 이전 업데이트가 진행 중이면 스킵 (프레임 드롭 방지)
            return
            
        self.is_updating = True
        
        if q_image is None or q_image.isNull():
            self.next_pixmap = None
        else:
            # 백그라운드에서 픽셀맵 생성 (메인 스레드 블로킹 방지)
            self.next_pixmap = QPixmap.fromImage(q_image)
        
        # 비동기 업데이트 스케줄링 (1ms 후 적용)
        if not self.update_timer.isActive():
            self.update_timer.start(1)
    
    def _apply_next_frame(self):
        """다음 프레임을 안전하게 적용"""
        self.current_pixmap = self.next_pixmap
        self.next_pixmap = None
        self.is_updating = False
        
        # 실제 화면 업데이트 (VSync와 동기화됨)
        self.update()

class PSCameraUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.show_info_panel = True
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("PS Camera")
        self.setFixedSize(660, 600)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 카메라 화면 (빠른 위젯)
        self.camera_widget = FastCameraWidget()
        layout.addWidget(self.camera_widget)
        
        # 정보 패널
        self.info_widget = QWidget()
        info_layout = QVBoxLayout(self.info_widget)
        info_layout.setContentsMargins(5, 5, 5, 5)
        info_layout.setSpacing(2)
        
        self.info_labels = [QLabel() for _ in range(4)]
        for label in self.info_labels:
            label.setStyleSheet("color: white; font-size: 11px;")
            info_layout.addWidget(label)
        
        self.info_widget.setStyleSheet("background: rgba(40,40,40,200);")
        self.info_widget.setFixedSize(640, 80)
        layout.addWidget(self.info_widget)
        
        # 컨트롤
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        
        # 토글 버튼
        self.info_button = QPushButton("Hide Info")
        controls_layout.addWidget(self.info_button)
        
        # 게인
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("Gain:"))
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setRange(0, 100)
        gain_layout.addWidget(self.gain_slider)
        self.gain_label = QLabel()
        gain_layout.addWidget(self.gain_label)
        controls_layout.addLayout(gain_layout)
        
        # 노출시간
        exposure_layout = QHBoxLayout()
        exposure_layout.addWidget(QLabel("노출시간:"))
        self.exposure_slider = QSlider(Qt.Horizontal)
        self.exposure_slider.setRange(1, 30)
        exposure_layout.addWidget(self.exposure_slider)
        self.exposure_label = QLabel()
        exposure_layout.addWidget(self.exposure_label)
        controls_layout.addLayout(exposure_layout)
        
        # VSync 딜레이
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("VSync 딜레이:"))
        self.delay_slider = QSlider(Qt.Horizontal)
        self.delay_slider.setRange(-50, 50)
        delay_layout.addWidget(self.delay_slider)
        self.delay_label = QLabel()
        delay_layout.addWidget(self.delay_label)
        controls_layout.addLayout(delay_layout)
        
        layout.addWidget(controls)
        
    
    def update_camera_frame(self, q_image):
        """카메라 프레임 업데이트"""
        self.camera_widget.update_frame(q_image)
    
    def update_info_panel(self, camera_info):
        """정보 패널 업데이트"""
        if not self.show_info_panel:
            return
            
        texts = [
            f"Camera: {camera_info.get('name', 'N/A')}",
            f"IP: {camera_info.get('ip', 'N/A')}  FPS: {camera_info.get('fps', 0):.1f}Hz (2프레임주기)",
            f"Resolution: {camera_info.get('width', 0)}x{camera_info.get('height', 0)}",
            f"Exposure: {camera_info.get('exposure', 0)}ms (Auto)  Gain: {camera_info.get('gain', 0)}"
        ]
        
        for i, text in enumerate(texts):
            self.info_labels[i].setText(text)
    
    def toggle_info(self):
        """정보 패널 토글"""
        self.show_info_panel = not self.show_info_panel
        self.info_widget.setVisible(self.show_info_panel)
        self.info_button.setText("Show Info" if not self.show_info_panel else "Hide Info")
    
    
    
    def update_gain_display(self, gain_value):
        """게인 표시 업데이트"""
        self.gain_label.setText(str(int(gain_value)))
        
    def update_exposure_display(self, value):
        """노출시간 표시 업데이트"""
        self.exposure_label.setText(f"{value}ms")
        
    def update_delay_display(self, value):
        """딜레이 표시 업데이트"""
        self.delay_label.setText(f"{value}ms")
    
    def set_slider_values(self, gain_value, exposure_value, delay_value):
        """슬라이더 값 설정 (시그널 방지)"""
        self.gain_slider.blockSignals(True)
        self.exposure_slider.blockSignals(True)
        self.delay_slider.blockSignals(True)
        
        self.gain_slider.setValue(int(gain_value))
        self.exposure_slider.setValue(int(exposure_value))
        self.delay_slider.setValue(int(delay_value))
        
        self.gain_slider.blockSignals(False)
        self.exposure_slider.blockSignals(False)
        self.delay_slider.blockSignals(False)
    
    def show_error(self, message):
        """오류 메시지 표시"""
        # 비동기 위젯에 검은 화면 표시
        self.camera_widget.update_frame(None)
        print(f"❌ 오류: {message}")
