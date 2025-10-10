#coding=utf-8
"""
카메라 제어 모듈
MindVision 카메라 초기화, 설정, 트리거 제어
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
    """카메라 제어 클래스"""
    
    def __init__(self):
        self.hCamera = None
        self.pFrameBuffer = None
        self.capability = None
        self.is_running = False
        
        # 트리거 제어
        self.trigger_thread = None
        self.trigger_running = False
        self.target_fps = 30
        
        # 시그널
        self.signals = CameraSignals()
        
        # 콜백
        self._camera_callback = None
    
    def initialize(self):
        """카메라 초기화"""
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
            
            # 기본 설정
            mvsdk.CameraSetWbMode(self.hCamera, True)
            
            # 프레임 버퍼 할당
            buffer_size = (self.capability.sResolutionRange.iWidthMax * 
                          self.capability.sResolutionRange.iHeightMax * 3)
            self.pFrameBuffer = mvsdk.CameraAlignMalloc(buffer_size, 16)
            
            # 수동 트리거 모드
            mvsdk.CameraSetTriggerMode(self.hCamera, 1)
            
            # 콜백 등록
            self._camera_callback = mvsdk.CAMERA_SNAP_PROC(self._on_frame_callback)
            mvsdk.CameraSetCallbackFunction(self.hCamera, self._camera_callback, 0)
            
            # 재생 시작
            mvsdk.CameraPlay(self.hCamera)
            print("✅ 콜백 모드 + 수동 트리거")
            
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
    
    def get_exposure_range(self):
        """노출 시간 범위 (μs)"""
        if not self.capability:
            return 0, 0
        
        exp_range = self.capability.sExposeDesc
        return exp_range.uiExposeTimeMin, exp_range.uiExposeTimeMax
    
    def get_gain_range(self):
        """게인 범위"""
        if not self.capability:
            return 0, 0
        
        gain_range = self.capability.sRgbGainRange
        return gain_range.iRGainMin, gain_range.iRGainMax
    
    def get_current_gain(self):
        """현재 게인 값"""
        if not self.hCamera:
            return 0
        
        r_gain, _, _ = mvsdk.CameraGetGain(self.hCamera)
        return r_gain
    
    def set_resolution(self, resolution_desc):
        """해상도 변경"""
        if not self.hCamera or self.is_running:
            return
        
        mvsdk.CameraStop(self.hCamera)
        mvsdk.CameraSetImageResolution(self.hCamera, resolution_desc)
        mvsdk.CameraPlay(self.hCamera)
        print(f"✅ 해상도: {resolution_desc.iWidth}x{resolution_desc.iHeight}")
    
    def set_exposure(self, exposure_ms):
        """노출 시간 설정 (ms → μs)"""
        if not self.hCamera:
            return
        
        exposure_us = exposure_ms * 1000
        mvsdk.CameraSetExposureTime(self.hCamera, float(exposure_us))
    
    def set_gain(self, gain):
        """게인 설정"""
        if not self.hCamera:
            return
        
        mvsdk.CameraSetGain(self.hCamera, gain, gain, gain)
    
    def set_manual_exposure(self, exposure_ms):
        """수동 노출 모드 설정"""
        if not self.hCamera:
            return
        
        mvsdk.CameraSetAeState(self.hCamera, False)
        self.set_exposure(exposure_ms)
    
    def start_trigger(self, target_fps):
        """트리거 시작"""
        self.target_fps = target_fps
        self.trigger_running = True
        self.trigger_thread = threading.Thread(target=self._trigger_loop, daemon=True)
        self.trigger_thread.start()
    
    def stop_trigger(self):
        """트리거 중지"""
        self.trigger_running = False
        if self.trigger_thread and self.trigger_thread.is_alive():
            self.trigger_thread.join(timeout=2.0)
            if self.trigger_thread.is_alive():
                print("⚠️ 트리거 스레드가 2초 내에 종료되지 않았습니다")
            self.trigger_thread = None
    
    def _trigger_loop(self):
        """트리거 루프 (FPS 제어)"""
        next_trigger_time = time.perf_counter()
        
        while self.trigger_running and self.hCamera:
            try:
                current_time = time.perf_counter()
                trigger_interval = 1.0 / self.target_fps
                
                if current_time >= next_trigger_time:
                    mvsdk.CameraSoftTrigger(self.hCamera)
                    next_trigger_time = current_time + trigger_interval
                
                time.sleep(0.0001)
                
            except Exception as e:
                print(f"⚠️ 트리거 오류: {e}")
                break
    
    def _on_frame_callback(self, hCamera, pRawData, pFrameHead, pContext):
        """프레임 콜백 (SDK 스레드)"""
        if not self.is_running:
            return
        
        try:
            # 이미지 변환
            mvsdk.CameraImageProcess(hCamera, pRawData, self.pFrameBuffer, pFrameHead.contents)
            
            # numpy 배열로 변환
            frame_head = pFrameHead.contents
            frame_data = (mvsdk.c_ubyte * frame_head.uBytes).from_address(self.pFrameBuffer)
            frame = np.frombuffer(frame_data, dtype=np.uint8).copy()
            frame = frame.reshape((frame_head.iHeight, frame_head.iWidth, 3))
            
            # BGR로 변환 후 시그널 발생
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self.signals.frame_ready.emit(frame_bgr)
            
        except Exception as e:
            print(f"⚠️ 콜백 오류: {e}")
    
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

