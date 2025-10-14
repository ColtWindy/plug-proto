#coding=utf-8
"""
YOLO PyTorch 모델 테스트
.pt 파일만 로드
"""
import sys
import os
from pathlib import Path
from _lib.wayland_utils import setup_wayland_environment
from PySide6.QtWidgets import QApplication
from ui.main_window import YOLOCameraWindow
from ui.model_manager import ModelManager


def main():
    """PyTorch 모델 테스트"""
    # Wayland 환경 설정
    wayland_display, xdg_runtime_dir = setup_wayland_environment()
    if not wayland_display:
        print("❌ Wayland 디스플레이를 찾을 수 없습니다")
        sys.exit(1)
    
    socket_path = os.path.join(xdg_runtime_dir, wayland_display)
    if not os.path.exists(socket_path):
        print(f"❌ Wayland 소켓이 없습니다: {socket_path}")
        sys.exit(1)
    
    print(f"✅ Wayland: {wayland_display}")
    
    # Qt 애플리케이션
    app = QApplication(sys.argv)
    print(f"📱 Qt 플랫폼: {app.platformName()}")
    
    # 모델 디렉토리에서 .pt 파일만 검색
    models_dir = Path(__file__).parent / "models"
    pt_files = sorted(models_dir.glob("*.pt"))
    
    if not pt_files:
        print("❌ .pt 파일이 없습니다")
        sys.exit(1)
    
    print(f"📦 PyTorch 모델: {len(pt_files)}개")
    
    # 모델 관리자 설정
    model_manager = ModelManager(models_dir)
    model_manager.model_list = [(f.name, str(f)) for f in pt_files]
    model_manager.current_model = model_manager._load_single_model(str(pt_files[0]))
    
    print(f"✅ 첫 번째 모델: {pt_files[0].name}")
    
    # 메인 윈도우 실행
    window = YOLOCameraWindow(model_manager)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
