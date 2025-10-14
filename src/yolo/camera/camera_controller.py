#coding=utf-8
"""
카메라 제어 모듈
MindVision 카메라 초기화, 설정, 폴링 방식 프레임 획득
"""
import time
import threading
import numpy as np
import cv2
from _lib import mvsdk
from PySide6.QtCore import QObject, Signal


class CameraSignals(QObject):
    """카메라 시그널"""
    frame_ready = Signal(np.ndarray)  # BGR 프레임


class CameraController:
    """카메라 제어 클래스 - 폴링 방식"""
    
    def __init__(self):
        self.hCamera = None
        self.pFrameBuffer = None
        self.capability = None
        self.is_running = False
        
        # 폴링 스레드
        self.polling_thread = None
        
        # 시그널
        self.signals = CameraSignals()
    
    def initialize(self):
        """카메라 초기화 - 자동 노출 및 연속 획득 모드"""
        try:
            mvsdk.CameraSdkInit(1)
            camera_list = mvsdk.CameraEnumerateDevice()
            
            if len(camera_list) == 0:
                raise Exception("카메라를 찾을 수 없습니다.")
            
            target_camera = camera_list[0]
            self.hCamera = mvsdk.CameraInit(target_camera, -1, -1)
            print(f"✅ 카메라: {target_camera.GetFriendlyName()}")
            
            # 카메라 정보
            self.capability = mvsdk.CameraGetCapability(self.hCamera)
            
            # 자동 설정 활성화
            mvsdk.CameraSetWbMode(self.hCamera, True)  # 자동 화이트밸런스
            mvsdk.CameraSetAeState(self.hCamera, True)  # 자동 노출
            
            # 프레임 버퍼 할당
            buffer_size = (self.capability.sResolutionRange.iWidthMax * 
                          self.capability.sResolutionRange.iHeightMax * 3)
            self.pFrameBuffer = mvsdk.CameraAlignMalloc(buffer_size, 16)
            
            # 연속 획득 모드 (트리거 없음)
            mvsdk.CameraSetTriggerMode(self.hCamera, 0)
            
            # 재생 시작
            mvsdk.CameraPlay(self.hCamera)
            print("✅ 자동 노출 + 연속 획득 모드")
            
            return True
            
        except Exception as e:
            print(f"❌ 카메라 초기화 실패: {e}")
            raise
    
    def get_resolutions(self):
        """사용 가능한 해상도 목록"""
        if not self.capability:
            return []
        
        resolutions = []
        current_res = mvsdk.CameraGetImageResolution(self.hCamera)
        current_index = 0
        
        for i in range(self.capability.iImageSizeDesc):
            desc = self.capability.pImageSizeDesc[i]
            resolutions.append({
                'index': i,
                'desc': desc,
                'text': f"{desc.GetDescription()} ({desc.iWidth}x{desc.iHeight})"
            })
            if desc.iWidth == current_res.iWidth and desc.iHeight == current_res.iHeight:
                current_index = i
        
        return resolutions, current_index
    
    
    def set_resolution(self, resolution_desc):
        """해상도 변경"""
        if not self.hCamera or self.is_running:
            return
        
        mvsdk.CameraStop(self.hCamera)
        mvsdk.CameraSetImageResolution(self.hCamera, resolution_desc)
        mvsdk.CameraPlay(self.hCamera)
        print(f"✅ 해상도: {resolution_desc.iWidth}x{resolution_desc.iHeight}")
    
    def start_trigger(self, target_fps=None):
        """폴링 시작 (최대 속도)"""
        self.is_running = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
    
    def stop_trigger(self):
        """폴링 중지"""
        self.is_running = False
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=2.0)
            if self.polling_thread.is_alive():
                print("⚠️ 폴링 스레드가 2초 내에 종료되지 않았습니다")
            self.polling_thread = None
    
    def _polling_loop(self):
        """폴링 루프 (최대 속도)"""
        while self.is_running and self.hCamera:
            try:
                # 프레임 획득 대기 (타임아웃 1초)
                pRawData, pFrameHead = mvsdk.CameraGetImageBuffer(self.hCamera, 1000)
                
                # 이미지 변환
                mvsdk.CameraImageProcess(self.hCamera, pRawData, 
                                        self.pFrameBuffer, pFrameHead)
                
                # numpy 배열로 변환
                frame_data = (mvsdk.c_ubyte * pFrameHead.uBytes).from_address(self.pFrameBuffer)
                frame = np.frombuffer(frame_data, dtype=np.uint8).copy()
                frame = frame.reshape((pFrameHead.iHeight, pFrameHead.iWidth, 3))
                
                # 버퍼 해제
                mvsdk.CameraReleaseImageBuffer(self.hCamera, pRawData)
                
                # BGR로 변환 후 시그널 발생
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                self.signals.frame_ready.emit(frame_bgr)
                
            except mvsdk.CameraException as e:
                if self.is_running:
                    print(f"⚠️ 프레임 획득 실패: {e}")
                    time.sleep(0.1)
            except Exception as e:
                print(f"⚠️ 폴링 오류: {e}")
                break
    
    def cleanup(self):
        """리소스 정리"""
        self.is_running = False
        self.stop_trigger()
        
        if self.hCamera:
            try:
                # 카메라 정지
                mvsdk.CameraStop(self.hCamera)
            except:
                pass
            
            try:
                if self.pFrameBuffer:
                    mvsdk.CameraAlignFree(self.pFrameBuffer)
                    self.pFrameBuffer = None
            except Exception as e:
                print(f"⚠️ 버퍼 해제 실패: {e}")
            
            try:
                mvsdk.CameraUnInit(self.hCamera)
            except Exception as e:
                print(f"⚠️ 카메라 해제 실패: {e}")
            
            self.hCamera = None

