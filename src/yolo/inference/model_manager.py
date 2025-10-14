#coding=utf-8
"""
YOLO 모델 관리자
모델 로딩, YOLOE 설정, 모델 전환을 담당
"""
from pathlib import Path
from ultralytics import YOLO


class ModelManager:
    """YOLO 모델 로딩 및 관리"""
    
    def __init__(self, models_dir):
        """
        Args:
            models_dir: 모델 디렉토리 경로
        """
        self.models_dir = Path(models_dir)
        self.current_model = None
        self.model_list = []
    
    def load_models(self):
        """
        모델 디렉토리에서 사용 가능한 모델 검색 및 첫 번째 모델 로드
        
        Returns:
            (model, model_list): 로드된 모델과 전체 모델 리스트
        """
        # .pt와 .engine 파일 검색 (.pt 우선)
        pt_files = sorted(self.models_dir.glob("*.pt"))
        engine_files = sorted(self.models_dir.glob("*.engine"))
        all_models = pt_files + engine_files
        
        if not all_models:
            print("❌ 모델 파일(.engine/.pt)을 찾을 수 없습니다")
            return None, []
        
        # 모델 목록 생성
        self.model_list = [(f.name, str(f)) for f in all_models]
        
        print(f"📦 발견된 모델: {len(all_models)}개")
        print(f"  .pt 파일: {len(pt_files)}개, .engine 파일: {len(engine_files)}개")
        
        # 첫 번째 모델 로드
        self.current_model = self._load_single_model(str(all_models[0]))
        print(f"✅ 모델: {all_models[0].name}")
        
        return self.current_model, self.model_list
    
    def switch_model(self, model_path, task=None):
        """
        모델 전환
        
        Args:
            model_path: 모델 파일 경로
            task: YOLO task (detect, segment 등). None이면 자동 감지
        
        Returns:
            새로운 모델 객체
        """
        self.current_model = self._load_single_model(model_path, task)
        return self.current_model
    
    def _load_single_model(self, model_path, task=None):
        """
        단일 모델 로드 (YOLOE 자동 처리)
        
        Args:
            model_path: 모델 파일 경로
            task: YOLO task (None이면 자동 감지)
        
        Returns:
            로드된 YOLO 모델
        """
        model_path = str(model_path)
        is_engine = model_path.endswith('.engine')
        
        # YOLOE 모델 처리
        if self._is_yoloe_model(model_path):
            model = YOLO(model_path)  # task 자동 감지
            
            # .pt 파일 중 prompt-free가 아닌 모델만 프롬프트 지원
            if self._is_pt_file(model_path) and not self._is_prompt_free(model_path):
                self._setup_yoloe_prompt(model, ["car"])
                print(f"ℹ️ YOLOE (프롬프트 지원)")
            else:
                mode = "prompt-free" if self._is_prompt_free(model_path) else "TensorRT (고정 vocabulary)"
                print(f"ℹ️ YOLOE ({mode})")
        else:
            # 일반 YOLO 모델
            if task is None:
                task = self._detect_task(model_path)
            
            model = YOLO(model_path, task=task)
            model_type = "TensorRT" if is_engine else "PyTorch"
            print(f"✅ {model_type} 모델 (task={task})")
        
        return model
    
    def _setup_yoloe_prompt(self, model, classes):
        """
        YOLOE 프롬프트 설정
        
        Args:
            model: YOLO 모델 객체
            classes: 탐지할 클래스 리스트
        """
        try:
            if not hasattr(model, 'set_classes') or not hasattr(model, 'get_text_pe'):
                print(f"⚠️ YOLOE 메서드를 찾을 수 없습니다")
                return
            
            text_embeddings = model.get_text_pe(classes)
            model.set_classes(classes, text_embeddings)
            print(f"✅ YOLOE 프롬프트: {', '.join(classes)}")
        except Exception as e:
            print(f"⚠️ YOLOE 프롬프트 설정 실패: {e}")
    
    @staticmethod
    def _is_yoloe_model(model_path):
        """YOLOE 모델인지 확인"""
        return "yoloe" in Path(model_path).stem.lower()
    
    @staticmethod
    def _is_pt_file(model_path):
        """PyTorch 모델 파일인지 확인"""
        return Path(model_path).suffix.lower() == '.pt'
    
    @staticmethod
    def _is_prompt_free(model_path):
        """Prompt-free 모델인지 확인 ('-pf' 포함)"""
        return '-pf' in Path(model_path).stem.lower()
    
    @staticmethod
    def _detect_task(model_path):
        """파일명에서 task 추론"""
        name = Path(model_path).stem.lower()
        
        # .engine 파일은 기본적으로 detect로 가정 (파일명만으로 정확히 알 수 없음)
        if model_path.endswith('.engine'):
            # 파일명에 명확한 키워드가 있는 경우만 감지
            if 'segment' in name or name.endswith('seg'):
                return 'segment'
            elif 'classify' in name or name.endswith('cls'):
                return 'classify'
            elif 'pose' in name:
                return 'pose'
            elif 'obb' in name:
                return 'obb'
            # 기본값: detect
            return 'detect'
        
        # .pt 파일은 좀 더 유연하게 감지
        if 'seg' in name or 'segment' in name:
            return 'segment'
        elif 'cls' in name or 'classify' in name:
            return 'classify'
        elif 'pose' in name:
            return 'pose'
        elif 'obb' in name:
            return 'obb'
        
        return 'detect'

