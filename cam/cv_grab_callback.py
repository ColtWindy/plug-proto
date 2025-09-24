#coding=utf-8
import cv2
import os
import numpy as np
import mvsdk
import time
import platform

# 젯슨 로컬 디스플레이 환경 설정 (SSH 접속 시)
os.environ['DISPLAY'] = ':0'

class App(object):
	def __init__(self):
		super(App, self).__init__()
		self.pFrameBuffer = 0
		self.quit = False

	def main(self):
		# 카메라 조회
		DevList = mvsdk.CameraEnumerateDevice()
		nDev = len(DevList)
		if nDev < 1:
			print("No camera was found!")
			return

		for i, DevInfo in enumerate(DevList):
			print("{}: {} {}".format(i, DevInfo.GetFriendlyName(), DevInfo.GetPortType()))
		i = 0 if nDev == 1 else int(input("Select camera: "))
		DevInfo = DevList[i]
		print(DevInfo)

		# 카메라 열기
		hCamera = 0
		try:
			hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
		except mvsdk.CameraException as e:
			print("CameraInit Failed({}): {}".format(e.error_code, e.message) )
			return

		# 카메라 특성 설명 가져오기
		cap = mvsdk.CameraGetCapability(hCamera)

		# 흑백 카메라인지 컬러 카메라인지 판단
		monoCamera = (cap.sIspCapacity.bMonoSensor != 0)

		# 흑백 카메라는 ISP가 R=G=B의 24비트 그레이스케일로 확장하지 않고 MONO 데이터를 직접 출력하도록 함
		if monoCamera:
			mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
		else:
			mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

		# 카메라 모드를 연속 촬영으로 전환
		mvsdk.CameraSetTriggerMode(hCamera, 0)

		# 수동 노출, 노출 시간 30ms
		mvsdk.CameraSetAeState(hCamera, 0)
		mvsdk.CameraSetExposureTime(hCamera, 30 * 1000)

		# SDK 내부 이미지 획득 스레드가 작업을 시작하도록 함
		mvsdk.CameraPlay(hCamera)

		# RGB 버퍼에 필요한 크기 계산, 여기서는 카메라의 최대 해상도에 따라 직접 할당
		FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if monoCamera else 3)

		# RGB 버퍼 할당, ISP 출력 이미지를 저장하는 데 사용
		# 참고: 카메라에서 PC로 전송되는 것은 RAW 데이터이며, PC에서 소프트웨어 ISP를 통해 RGB 데이터로 변환됨 (흑백 카메라는 포맷 변환이 필요 없지만, ISP에는 다른 처리가 있으므로 이 버퍼도 할당해야 함)
		self.pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

		# 촬영 콜백 함수 설정
		self.quit = False
		mvsdk.CameraSetCallbackFunction(hCamera, self.GrabCallback, 0)

		# 종료 대기
		while not self.quit:
			time.sleep(0.1)

		# 카메라 닫기
		mvsdk.CameraUnInit(hCamera)

		# 프레임 버퍼 해제
		mvsdk.CameraAlignFree(self.pFrameBuffer)

	@mvsdk.method(mvsdk.CAMERA_SNAP_PROC)
	def GrabCallback(self, hCamera, pRawData, pFrameHead, pContext):
		FrameHead = pFrameHead[0]
		pFrameBuffer = self.pFrameBuffer

		mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
		mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)

		# Windows에서 획득한 이미지 데이터는 상하가 뒤바뀌어 BMP 형식으로 저장됨. OpenCV로 변환할 때는 상하를 뒤집어서 정상으로 만들어야 함
		# Linux에서는 직접 정상으로 출력되므로 상하 뒤집기가 필요 없음
		if platform.system() == "Windows":
			mvsdk.CameraFlipFrameBuffer(pFrameBuffer, FrameHead, 1)
		
		# 이때 이미지가 이미 pFrameBuffer에 저장되어 있음. 컬러 카메라의 경우 pFrameBuffer=RGB 데이터, 흑백 카메라의 경우 pFrameBuffer=8비트 그레이스케일 데이터
		# pFrameBuffer를 OpenCV 이미지 형식으로 변환하여 후속 알고리즘 처리 진행
		frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
		frame = np.frombuffer(frame_data, dtype=np.uint8)
		frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3) )

		frame = cv2.resize(frame, (640,480), interpolation = cv2.INTER_LINEAR)
		cv2.imshow("Press q to end", frame)
		if (cv2.waitKey(1) & 0xFF) == ord('q'):
			self.quit = True

def main():
	try:
		app = App()
		app.main()
	finally:
		cv2.destroyAllWindows()

main()
