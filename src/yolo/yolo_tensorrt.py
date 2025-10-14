#coding=utf-8
"""
YOLO TensorRT 엔진 테스트
.engine 파일만 로드하고 엔진 정보 표시
"""
import sys
import os
from pathlib import Path
from _lib.wayland_utils import setup_wayland_environment
from PySide6.QtWidgets import QApplication
from ui.main_window import YOLOCameraWindow
from ui.model_manager import ModelManager


def show_engine_info(model, model_path):
    """TensorRT 엔진 정보 표시"""
    print("\n" + "=" * 60)
    print("📊 TensorRT 엔진 정보")
    print("=" * 60)
    
    # 파일 크기
    file_size_mb = Path(model_path).stat().st_size / (1024 * 1024)
    print(f"파일 크기: {file_size_mb:.1f} MB")
    
    # 모델 속성
    if hasattr(model, 'task'):
        print(f"Task: {model.task}")
    
    if hasattr(model, 'names'):
        print(f"클래스 개수: {len(model.names)}")
        print(f"클래스 목록: {list(model.names.values())[:10]}..." if len(model.names) > 10 else f"클래스 목록: {list(model.names.values())}")
    
    # 엔진 입력 정보
    if hasattr(model, 'predictor') and hasattr(model.predictor, 'model'):
        try:
            import torch
            engine_model = model.predictor.model
            if hasattr(engine_model, 'bindings'):
                print(f"\n입력 바인딩:")
                for name in engine_model.bindings:
                    shape = engine_model.bindings[name]['shape']
                    dtype = engine_model.bindings[name]['dtype']
                    print(f"  {name}: {shape} ({dtype})")
        except:
            pass
    
    print("=" * 60 + "\n")


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
    
    # 모델 디렉토리에서 .engine 파일만 검색
    models_dir = Path(__file__).parent / "models"
    engine_files = sorted(models_dir.glob("*.engine"))
    
    if not engine_files:
        print("❌ .engine 파일이 없습니다")
        sys.exit(1)
    
    print(f"📦 TensorRT 엔진: {len(engine_files)}개")
    for i, f in enumerate(engine_files, 1):
        print(f"  {i}. {f.name}")
    
    # 모델 관리자 설정
    model_manager = ModelManager(models_dir)
    model_manager.model_list = [(f.name, str(f)) for f in engine_files]
    
    first_model_path = str(engine_files[0])
    model_manager.current_model = model_manager._load_single_model(first_model_path)
    
    # 엔진 정보 표시
    show_engine_info(model_manager.current_model, first_model_path)
    
    # 메인 윈도우 실행
    window = YOLOCameraWindow(model_manager)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

