#coding=utf-8
"""
YOLO TensorRT 엔진 테스트
.engine 파일만 로드
"""
import sys
import os
from pathlib import Path
from _lib.wayland_utils import setup_wayland_environment
from PySide6.QtWidgets import QApplication
from ui.tensorrt_window import TensorRTWindow
from ui.model_manager import ModelManager


def main():
    """TensorRT 엔진 테스트"""
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
    
    # .engine 파일만 검색
    models_dir = Path(__file__).parent / "models"
    engine_files = sorted(models_dir.glob("*.engine"))
    
    if not engine_files:
        print("❌ .engine 파일이 없습니다")
        sys.exit(1)
    
    print(f"📦 TensorRT 엔진: {len(engine_files)}개")
    
    # 모델 관리자 설정
    model_manager = ModelManager(models_dir)
    model_manager.model_list = [(f.name, str(f)) for f in engine_files]
    model_manager.current_model = model_manager._load_single_model(str(engine_files[0]))
    
    # TensorRT 전용 윈도우 실행
    window = TensorRTWindow(model_manager)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


