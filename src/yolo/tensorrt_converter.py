#coding=utf-8
"""
TensorRT 모델 변환 UI (Qt + Wayland)

옵션 설명:
-----------
1. 정밀도 (Precision):
   - FP32: 기본, 정확도 최고, 속도 보통
   - FP16 ⭐ 권장: 2배 빠름, 정확도 거의 유지 (~99%), 메모리 50% 절약
   - INT8: 최고 속도 (3-4배 빠름), 정확도 약간 감소 (~97%), 메모리 75% 절약

2. 이미지 크기 (imgsz):
   - 320: 매우 빠름, 정확도 낮음
   - 480: 빠름, 정확도 보통
   - 640 ⭐ 권장: 균형 (속도/정확도)
   - 1280: 느림, 정확도 최고 (작은 객체 탐지에 유리)

3. Workspace:
   - 2 GB: 작은 모델용
   - 4 GB ⭐ 권장: 대부분의 경우
   - 8 GB: 큰 이미지(1280) 또는 복잡한 모델용

벤치마크 (Jetson Orin Nano Super):
- PyTorch: ~217ms
- TensorRT FP32: ~112ms (2배 빠름)
- TensorRT FP16: ~112ms (2배 빠름, 메모리↓)
- TensorRT INT8: ~62ms (3.5배 빠름, 정확도 약간↓)

참고: https://docs.ultralytics.com/ko/guides/nvidia-jetson/
"""
import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QLabel, QComboBox, QPushButton, 
                                QTextEdit, QGroupBox, QGridLayout, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from _lib.wayland_utils import setup_wayland_environment
from ultralytics import YOLO

# Wayland 환경 설정
wayland_display, xdg_runtime_dir = setup_wayland_environment()

if not wayland_display:
    print("❌ 사용 가능한 Wayland 디스플레이를 찾을 수 없습니다")
    sys.exit(1)
else:
    print(f"✅ Wayland 디스플레이: {wayland_display}")

socket_path = os.path.join(xdg_runtime_dir, wayland_display)
if not os.path.exists(socket_path):
    print(f"❌ Wayland 소켓이 존재하지 않습니다: {socket_path}")
    sys.exit(1)
else:
    print(f"✅ Wayland 소켓 확인: {socket_path}")


class ConvertWorker(QThread):
    """변환 작업 워커"""
    progress = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, model_path, config):
        super().__init__()
        self.model_path = model_path
        self.config = config
    
    def run(self):
        try:
            # 출력 파일명 결정
            models_dir = Path(self.model_path).parent
            output_name = f"{Path(self.model_path).stem}_{self.config['name']}.engine"
            output_path = models_dir / output_name
            
            # 파일이 이미 존재하는지 확인
            if output_path.exists():
                self.progress.emit(f"ℹ️ 파일이 이미 존재합니다: {output_name}")
                self.progress.emit("   변환을 건너뜁니다.")
                self.finished.emit(True, f"✅ 기존 파일 사용: {output_name}")
                return
            
            self.progress.emit(f"🚀 변환 시작: {self.config['name']}")
            self.progress.emit(f"   모델: {Path(self.model_path).name}")
            self.progress.emit(f"   이미지 크기: {self.config['imgsz']}")
            self.progress.emit(f"   정밀도: {self.config['precision']}")
            self.progress.emit("")
            
            # 모델 로드
            model = YOLO(self.model_path)
            
            # export 파라미터
            export_params = {
                "format": "engine",
                "imgsz": self.config["imgsz"],
                "half": self.config["half"],
                "int8": self.config["int8"],
                "workspace": self.config["workspace"],
                "simplify": True,
                "verbose": False,
            }
            
            # INT8 캘리브레이션
            if self.config["int8"]:
                export_params["data"] = "coco128.yaml"
            
            # 변환 실행
            self.progress.emit("⏳ 변환 중... (수 분 소요)")
            model.export(**export_params)
            
            # 기본 이름으로 생성된 파일을 커스텀 이름으로 변경
            default_name = Path(self.model_path).stem + ".engine"
            default_path = models_dir / default_name
            
            if default_path.exists() and default_path != output_path:
                default_path.rename(output_path)
            
            self.finished.emit(True, f"✅ 변환 완료: {output_name}")
            
        except Exception as e:
            self.finished.emit(False, f"❌ 변환 실패: {e}")


class ConvertWindow(QMainWindow):
    """TensorRT 변환 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TensorRT 모델 변환")
        self.setGeometry(100, 100, 700, 600)
        
        self.worker = None
        self.init_ui()
        self.load_models()
    
    def init_ui(self):
        """UI 초기화"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # 설정 그룹
        settings_group = QGroupBox("변환 설정")
        settings_layout = QGridLayout()
        
        row = 0
        
        # 모델 선택
        settings_layout.addWidget(QLabel("모델 파일:"), row, 0)
        self.model_combo = QComboBox()
        settings_layout.addWidget(self.model_combo, row, 1)
        row += 1
        
        # 정밀도 선택
        settings_layout.addWidget(QLabel("정밀도:"), row, 0)
        self.precision_combo = QComboBox()
        self.precision_combo.addItem("FP32 - 정확도 최고", "fp32")
        self.precision_combo.addItem("FP16 - 2배 빠름, 정확도 유지 ⭐", "fp16")
        self.precision_combo.addItem("INT8 - 최고 속도 3-4배", "int8")
        self.precision_combo.setCurrentIndex(1)  # FP16 기본
        self.precision_combo.currentIndexChanged.connect(self.update_output_filename)
        settings_layout.addWidget(self.precision_combo, row, 1)
        row += 1
        
        # 이미지 크기
        settings_layout.addWidget(QLabel("이미지 크기:"), row, 0)
        self.imgsz_combo = QComboBox()
        self.imgsz_combo.addItem("320px - 매우 빠름", 320)
        self.imgsz_combo.addItem("480px - 빠름", 480)
        self.imgsz_combo.addItem("640px - 균형 ⭐", 640)
        self.imgsz_combo.addItem("1280px - 정확도 우선", 1280)
        self.imgsz_combo.setCurrentIndex(2)  # 640 기본
        self.imgsz_combo.currentIndexChanged.connect(self.update_output_filename)
        settings_layout.addWidget(self.imgsz_combo, row, 1)
        row += 1
        
        # Workspace
        settings_layout.addWidget(QLabel("Workspace:"), row, 0)
        self.workspace_combo = QComboBox()
        self.workspace_combo.addItem("2 GB", 2)
        self.workspace_combo.addItem("4 GB ⭐", 4)
        self.workspace_combo.addItem("8 GB - 큰 이미지용", 8)
        self.workspace_combo.setCurrentIndex(1)  # 4GB 기본
        self.workspace_combo.currentIndexChanged.connect(self.update_output_filename)
        settings_layout.addWidget(self.workspace_combo, row, 1)
        row += 1
        
        # 출력 파일명 표시
        settings_layout.addWidget(QLabel("출력 파일:"), row, 0)
        self.output_filename_label = QLabel("")
        self.output_filename_label.setStyleSheet("color: #2c3e50; font-weight: bold;")
        self.output_filename_label.setWordWrap(True)
        settings_layout.addWidget(self.output_filename_label, row, 1)
        row += 1
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 변환 버튼
        self.convert_btn = QPushButton("🚀 변환 시작")
        self.convert_btn.clicked.connect(self.start_convert)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        layout.addWidget(self.convert_btn)
        
        # 진행률 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress_bar)
        
        # 로그 출력
        log_label = QLabel("변환 로그:")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(250)
        layout.addWidget(self.log_text)
        
        # 안내 메시지
        info_text = """
📋 옵션 직접 선택:
   정밀도: FP32 / FP16 ⭐ / INT8
   이미지 크기: 320 / 480 / 640 ⭐ / 1280
   Workspace: 2GB / 4GB ⭐ / 8GB
   Simplify: True (고정)
   
💡 성능 비교 (Jetson Orin Nano Super):
   FP16 640: ~112ms (메모리 50%↓) ⭐ 권장
   INT8 640: ~62ms (정확도 97%)
   
📂 파일명: 모델_정밀도_크기_워크스페이스.engine
   예: yolo8n_trash_fp16_640_4gb.engine

ℹ️ 동일 파일이 있으면 변환 건너뜀
        """
        info_label = QLabel(info_text)
        info_label.setStyleSheet("background-color: #ecf0f1; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)
    
    def load_models(self):
        """모델 파일 로드"""
        models_dir = Path(__file__).parent / "models"
        pt_files = list(models_dir.glob("*.pt"))
        
        if not pt_files:
            self.log("⚠️ models/ 디렉토리에 .pt 파일이 없습니다")
            self.convert_btn.setEnabled(False)
            return
        
        for pt_file in sorted(pt_files):
            self.model_combo.addItem(pt_file.name, str(pt_file))
        
        self.log(f"✅ {len(pt_files)}개의 모델 파일을 찾았습니다")
        
        # 모델 변경 시에도 파일명 업데이트
        self.model_combo.currentIndexChanged.connect(self.update_output_filename)
        
        # 출력 파일명 초기 업데이트
        self.update_output_filename()
    
    def update_output_filename(self):
        """출력 파일명 미리보기 업데이트"""
        model_path = self.model_combo.currentData()
        if not model_path:
            self.output_filename_label.setText("")
            return
        
        precision = self.precision_combo.currentData()
        imgsz = self.imgsz_combo.currentData()
        workspace = self.workspace_combo.currentData()
        
        model_stem = Path(model_path).stem
        filename = f"{model_stem}_{precision}_{imgsz}_{workspace}gb.engine"
        
        # 파일 존재 여부 확인
        models_dir = Path(model_path).parent
        output_path = models_dir / filename
        
        if output_path.exists():
            self.output_filename_label.setText(f"{filename}\n(✅ 이미 존재)")
            self.output_filename_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        else:
            self.output_filename_label.setText(f"{filename}\n(새로 생성)")
            self.output_filename_label.setStyleSheet("color: #2c3e50; font-weight: bold;")
    
    def log(self, message):
        """로그 추가"""
        self.log_text.append(message)
    
    def start_convert(self):
        """변환 시작"""
        model_path = self.model_combo.currentData()
        if not model_path:
            self.log("❌ 모델을 선택해주세요")
            return
        
        # 설정 준비
        precision = self.precision_combo.currentData()
        imgsz = self.imgsz_combo.currentData()
        workspace = self.workspace_combo.currentData()
        
        config = {
            "name": f"{precision}_{imgsz}_{workspace}gb",
            "imgsz": imgsz,
            "half": precision == "fp16",
            "int8": precision == "int8",
            "workspace": workspace,
            "precision": precision.upper(),
        }
        
        # UI 비활성화
        self.convert_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log("")
        self.log("=" * 50)
        self.log("📋 변환 설정:")
        self.log(f"   모델: {Path(model_path).name}")
        self.log(f"   정밀도: {config['precision']}")
        self.log(f"   이미지 크기: {imgsz}px")
        self.log(f"   Workspace: {workspace}GB")
        self.log(f"   Simplify: True (고정)")
        self.log(f"   출력 파일: {Path(model_path).stem}_{config['name']}.engine")
        self.log("=" * 50)
        
        # 워커 시작
        self.worker = ConvertWorker(model_path, config)
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(self.on_convert_finished)
        self.worker.start()
    
    def on_convert_finished(self, success, message):
        """변환 완료"""
        self.log(message)
        self.log("=" * 50)
        
        if success:
            self.log("")
            if "기존 파일" in message:
                self.log("ℹ️ 동일 설정의 파일이 이미 존재하여 변환을 건너뛰었습니다.")
            else:
                self.log("✅ 변환이 완료되었습니다!")
            
            self.log("")
            self.log("📝 다음 단계:")
            self.log("   1. python wayland_detect.py 실행")
            self.log("   2. 모델 드롭다운에서 변환된 .engine 파일 선택")
            self.log("   3. FPS/해상도 조정하며 성능 비교")
            self.log("")
            self.log("💾 저장 위치: models/ 디렉토리")
            self.log("📂 파일명 형식: 모델명_정밀도_크기.engine")
            self.log("ℹ️ 동일 파일이 있으면 변환하지 않습니다")
        
        self.convert_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.worker = None


def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # Wayland 플랫폼 플러그인 사용
    print(f"📱 Qt 플랫폼: {app.platformName()}")
    
    window = ConvertWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

