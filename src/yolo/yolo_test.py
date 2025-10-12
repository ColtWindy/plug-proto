#coding=utf-8
"""
YOLO 카메라 애플리케이션 메인 진입점
"""
import sys
import os
from pathlib import Path
from _lib.wayland_utils import setup_wayland_environment
from PySide6.QtWidgets import QApplication
from ultralytics import YOLO
from ui.main_window import YOLOCameraWindow


def load_models():
    """YOLO 모델 로드"""
    models_dir = Path(__file__).parent / "models"
    
    # .pt와 .engine 파일 검색 (.pt 우선)
    pt_files = sorted(models_dir.glob("*.pt"))
    engine_files = sorted(models_dir.glob("*.engine"))
    all_models = pt_files + engine_files  # .pt 파일 우선
    
    if not all_models:
        print("❌ 모델 파일(.engine/.pt)을 찾을 수 없습니다")
        return None, []
    
    # 모델 목록 생성
    model_list = [(f.name, str(f)) for f in all_models]
    
    print(f"📦 발견된 모델: {len(all_models)}개")
    print(f"  .pt 파일: {len(pt_files)}개, .engine 파일: {len(engine_files)}개")
    
    # 첫 번째 모델 로드
    first_model_path = str(all_models[0])
    
    # YOLOE 모델 처리
    if _is_yoloe_model(first_model_path):
        model = YOLO(first_model_path)  # task 자동 감지
        
        # .pt 파일만 프롬프트 지원
        if _is_pt_file(first_model_path):
            _setup_yoloe(model, ["car"])
        else:
            print("ℹ️ TensorRT 엔진은 prompt-free 모드로 작동합니다 (고정 vocabulary)")
    else:
        # 일반 YOLO 모델
        task = _detect_task_from_name(first_model_path)
        model = YOLO(first_model_path, task=task)
    
    print(f"✅ 모델: {all_models[0].name}")
    return model, model_list


def _detect_task_from_name(model_path):
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
    
    return 'detect'


def _is_yoloe_model(model_path):
    """YOLOE 모델 감지"""
    return "yoloe" in Path(model_path).stem.lower()


def _is_pt_file(model_path):
    """PyTorch 모델 파일인지 확인"""
    return Path(model_path).suffix.lower() == '.pt'


def _setup_yoloe(model, classes):
    """YOLOE 프롬프트 설정"""
    try:
        # YOLO 객체 타입 확인
        if not hasattr(model, 'set_classes'):
            print(f"⚠️ 모델에 set_classes 메서드가 없습니다 (타입: {type(model)})")
            return
        
        if not hasattr(model, 'get_text_pe'):
            print(f"⚠️ 모델에 get_text_pe 메서드가 없습니다 - YOLOE 모델이 아닐 수 있습니다")
            return
            
        text_embeddings = model.get_text_pe(classes)
        model.set_classes(classes, text_embeddings)
        print(f"✅ YOLOE 프롬프트: {', '.join(classes)}")
    except Exception as e:
        print(f"⚠️ YOLOE 프롬프트 설정 실패: {e}")
        import traceback
        traceback.print_exc()


def main():
    """메인 함수"""
    # Wayland 환경 설정
    wayland_display, xdg_runtime_dir = setup_wayland_environment()
    
    if not wayland_display:
        print("❌ 사용 가능한 Wayland 디스플레이를 찾을 수 없습니다")
        sys.exit(1)
    
    print(f"✅ Wayland 디스플레이: {wayland_display}")
    
    socket_path = os.path.join(xdg_runtime_dir, wayland_display)
    if not os.path.exists(socket_path):
        print(f"❌ Wayland 소켓이 존재하지 않습니다: {socket_path}")
        sys.exit(1)
    
    print(f"✅ Wayland 소켓 확인: {socket_path}")
    
    # Qt 애플리케이션
    app = QApplication(sys.argv)
    print(f"📱 Qt 플랫폼: {app.platformName()}")
    
    # YOLO 모델 로드
    model, model_list = load_models()
    if not model:
        print("❌ YOLO 모델을 로드할 수 없습니다")
        sys.exit(1)
    
    # 메인 윈도우
    window = YOLOCameraWindow(model, model_list)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
