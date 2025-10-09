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
                                QTextEdit, QGroupBox, QGridLayout, QProgressBar, QListWidget)
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
    """변환 작업 워커 (여러 작업 순차 실행)"""
    progress = Signal(str)
    finished = Signal(bool, str)
    task_completed = Signal(int, bool)  # (작업 인덱스, 성공 여부)
    
    def __init__(self, tasks):
        super().__init__()
        self.tasks = tasks  # [(model_path, config), ...]
    
    def run(self):
        """여러 작업 순차 실행"""
        total = len(self.tasks)
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for idx, (model_path, config) in enumerate(self.tasks):
            try:
                self.progress.emit("")
                self.progress.emit(f"{'='*50}")
                self.progress.emit(f"작업 {idx+1}/{total}: {config['name']}")
                self.progress.emit(f"{'='*50}")
                
                # 출력 파일명 결정
                models_dir = Path(model_path).parent
                output_name = f"{Path(model_path).stem}_{config['name']}.engine"
                output_path = models_dir / output_name
                
                # 파일이 이미 존재하는지 확인
                if output_path.exists():
                    self.progress.emit(f"ℹ️ 파일이 이미 존재합니다: {output_name}")
                    self.progress.emit("   변환을 건너뜁니다.")
                    skip_count += 1
                    self.task_completed.emit(idx, True)
                    continue
                
                self.progress.emit(f"🚀 변환 시작")
                self.progress.emit(f"   모델: {Path(model_path).name}")
                self.progress.emit(f"   정밀도: {config['precision']}")
                self.progress.emit(f"   이미지 크기: {config['imgsz']}px")
                self.progress.emit(f"   Workspace: {config['workspace']}GB")
                self.progress.emit("")
                
                # 모델 로드
                model = YOLO(model_path)
                
                # export 파라미터
                export_params = {
                    "format": "engine",
                    "imgsz": config["imgsz"],
                    "half": config["half"],
                    "int8": config["int8"],
                    "workspace": config["workspace"],
                    "simplify": True,
                    "verbose": False,
                }
                
                # INT8 캘리브레이션
                if config["int8"]:
                    export_params["data"] = "coco128.yaml"
                    self.progress.emit("   INT8 캘리브레이션: coco128.yaml")
                
                # 변환 실행
                self.progress.emit("⏳ 변환 중... (수 분 소요)")
                model.export(**export_params)
                
                # 기본 이름으로 생성된 파일을 커스텀 이름으로 변경
                default_name = Path(model_path).stem + ".engine"
                default_path = models_dir / default_name
                
                if default_path.exists() and default_path != output_path:
                    default_path.rename(output_path)
                
                self.progress.emit(f"✅ 완료: {output_name}")
                success_count += 1
                self.task_completed.emit(idx, True)
                
            except Exception as e:
                self.progress.emit(f"❌ 실패: {e}")
                fail_count += 1
                self.task_completed.emit(idx, False)
        
        # 최종 결과
        self.progress.emit("")
        self.progress.emit(f"{'='*50}")
        self.progress.emit(f"📊 변환 완료: 성공 {success_count}, 건너뜀 {skip_count}, 실패 {fail_count}")
        self.progress.emit(f"{'='*50}")
        
        self.finished.emit(fail_count == 0, f"완료: {success_count}/{total}")


class ConvertWindow(QMainWindow):
    """TensorRT 변환 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TensorRT 모델 변환")
        self.setGeometry(100, 100, 900, 700)
        
        self.worker = None
        self.task_queue = []  # [(model_path, config), ...]
        self.init_ui()
        self.load_models()
    
    def init_ui(self):
        """UI 초기화"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        
        # 왼쪽: 설정
        left_layout = QVBoxLayout()
        
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
        left_layout.addWidget(settings_group)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # 추가 버튼
        self.add_btn = QPushButton("➕ 목록에 추가")
        self.add_btn.clicked.connect(self.add_to_queue)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        button_layout.addWidget(self.add_btn)
        
        # 변환 시작 버튼
        self.convert_btn = QPushButton("🚀 변환 시작")
        self.convert_btn.clicked.connect(self.start_convert)
        self.convert_btn.setEnabled(False)  # 초기에는 비활성화
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
        button_layout.addWidget(self.convert_btn)
        
        left_layout.addLayout(button_layout)
        
        # 진행률 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        left_layout.addWidget(self.progress_bar)
        
        # 안내 메시지
        info_text = """
💡 사용 방법:
   1. 설정 조정
   2. "목록에 추가" 클릭
   3. 여러 설정 추가 가능
   4. "변환 시작"으로 일괄 변환

📊 성능 (Jetson Orin Nano Super):
   FP16 640: ~112ms ⭐ 권장
   INT8 640: ~62ms (최고 속도)
        """
        info_label = QLabel(info_text)
        info_label.setStyleSheet("background-color: #ecf0f1; padding: 8px; border-radius: 5px; font-size: 11px;")
        left_layout.addWidget(info_label)
        
        main_layout.addLayout(left_layout, stretch=1)
        
        # 오른쪽: 작업 목록
        right_layout = QVBoxLayout()
        
        queue_label = QLabel("변환 작업 목록:")
        right_layout.addWidget(queue_label)
        
        self.task_list = QListWidget()
        right_layout.addWidget(self.task_list)
        
        # 목록 제어 버튼
        list_btn_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("전체 삭제")
        self.clear_btn.clicked.connect(self.clear_queue)
        list_btn_layout.addWidget(self.clear_btn)
        
        self.remove_btn = QPushButton("선택 삭제")
        self.remove_btn.clicked.connect(self.remove_selected)
        list_btn_layout.addWidget(self.remove_btn)
        
        right_layout.addLayout(list_btn_layout)
        
        # 로그 출력
        log_label = QLabel("변환 로그:")
        right_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        right_layout.addWidget(self.log_text)
        
        main_layout.addLayout(right_layout, stretch=1)
    
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
    
    def add_to_queue(self):
        """현재 설정을 작업 목록에 추가"""
        model_path = self.model_combo.currentData()
        if not model_path:
            self.log("❌ 모델을 선택해주세요")
            return
        
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
        
        model_name = Path(model_path).stem
        output_filename = f"{model_name}_{config['name']}.engine"
        
        # 중복 체크
        for existing_path, existing_config in self.task_queue:
            if existing_path == model_path and existing_config['name'] == config['name']:
                self.log(f"⚠️ 이미 목록에 있습니다: {output_filename}")
                return
        
        # 작업 추가
        self.task_queue.append((model_path, config))
        
        # 목록에 표시
        display_text = f"{output_filename} ({config['precision']}, {imgsz}px, {workspace}GB)"
        self.task_list.addItem(display_text)
        
        self.log(f"➕ 추가됨: {output_filename}")
        
        # 변환 버튼 활성화
        if len(self.task_queue) > 0:
            self.convert_btn.setEnabled(True)
    
    def clear_queue(self):
        """작업 목록 전체 삭제"""
        self.task_queue.clear()
        self.task_list.clear()
        self.log("🗑️ 작업 목록이 초기화되었습니다")
        self.convert_btn.setEnabled(False)
    
    def remove_selected(self):
        """선택된 작업 삭제"""
        current_row = self.task_list.currentRow()
        if current_row >= 0:
            self.task_list.takeItem(current_row)
            del self.task_queue[current_row]
            self.log(f"🗑️ 작업 삭제됨 (인덱스: {current_row})")
            
            if len(self.task_queue) == 0:
                self.convert_btn.setEnabled(False)
    
    def start_convert(self):
        """작업 목록의 모든 변환 시작"""
        if len(self.task_queue) == 0:
            self.log("❌ 작업 목록이 비어있습니다. '목록에 추가'를 먼저 클릭하세요")
            return
        
        # UI 비활성화
        self.convert_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        
        self.log("")
        self.log(f"{'='*50}")
        self.log(f"🚀 일괄 변환 시작: {len(self.task_queue)}개 작업")
        self.log(f"{'='*50}")
        
        # 워커 시작
        self.worker = ConvertWorker(self.task_queue)
        self.worker.progress.connect(self.log)
        self.worker.task_completed.connect(self.on_task_completed)
        self.worker.finished.connect(self.on_convert_finished)
        self.worker.start()
    
    def on_task_completed(self, idx, success):
        """개별 작업 완료 시 목록 업데이트"""
        item = self.task_list.item(idx)
        if item:
            if success:
                item.setForeground(Qt.darkGreen)
            else:
                item.setForeground(Qt.red)
    
    def on_convert_finished(self, success, message):
        """모든 변환 완료"""
        self.log("")
        self.log("✅ 모든 작업이 완료되었습니다!")
        self.log("")
        self.log("📝 다음 단계:")
        self.log("   1. python wayland_detect.py 실행")
        self.log("   2. 모델 드롭다운에서 변환된 .engine 파일 선택")
        self.log("   3. FPS/해상도 조정하며 성능 비교")
        
        # UI 활성화
        self.add_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.remove_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # 작업 목록 초기화 여부
        if success:
            self.log("")
            self.log("🗑️ 작업 목록을 초기화합니다")
            self.clear_queue()
        else:
            self.convert_btn.setEnabled(True)
        
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

