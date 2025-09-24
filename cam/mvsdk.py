#coding=utf-8
import platform
from ctypes import *
from threading import local

# 콜백 함수 타입
CALLBACK_FUNC_TYPE = None

# SDK 동적 라이브러리
_sdk = None

def _Init():
	global _sdk
	global CALLBACK_FUNC_TYPE

	is_win = (platform.system() == "Windows")
	is_x86 = (platform.architecture()[0] == '32bit')

	if is_win:
		_sdk = windll.MVCAMSDK if is_x86 else windll.MVCAMSDK_X64
		CALLBACK_FUNC_TYPE = WINFUNCTYPE
	else:
		_sdk = cdll.LoadLibrary("libMVSDK.so")
		CALLBACK_FUNC_TYPE = CFUNCTYPE

_Init()

#-------------------------------------------타입 정의--------------------------------------------------

# 상태 코드 정의
CAMERA_STATUS_SUCCESS = 0   # 작업 성공
CAMERA_STATUS_FAILED = -1   # 작업 실패
CAMERA_STATUS_INTERNAL_ERROR = -2   # 내부 오류
CAMERA_STATUS_UNKNOW = -3   # 알 수 없는 오류
CAMERA_STATUS_NOT_SUPPORTED = -4   # 해당 기능을 지원하지 않음
CAMERA_STATUS_NOT_INITIALIZED = -5   # 초기화가 완료되지 않음
CAMERA_STATUS_PARAMETER_INVALID = -6   # 매개변수가 유효하지 않음
CAMERA_STATUS_PARAMETER_OUT_OF_BOUND = -7   # 매개변수가 범위를 벗어남
CAMERA_STATUS_UNENABLED = -8   # 사용 안 함
CAMERA_STATUS_USER_CANCEL = -9   # 사용자가 수동으로 취소함, 예: ROI 패널에서 취소 클릭 시 반환
CAMERA_STATUS_PATH_NOT_FOUND = -10  # 레지스트리에서 해당 경로를 찾을 수 없음
CAMERA_STATUS_SIZE_DISMATCH = -11  # 획득한 이미지 데이터 길이와 정의된 크기가 일치하지 않음
CAMERA_STATUS_TIME_OUT = -12  # 시간 초과 오류
CAMERA_STATUS_IO_ERROR = -13  # 하드웨어 IO 오류
CAMERA_STATUS_COMM_ERROR = -14  # 통신 오류
CAMERA_STATUS_BUS_ERROR = -15  # 버스 오류
CAMERA_STATUS_NO_DEVICE_FOUND = -16  # 디바이스를 찾을 수 없음
CAMERA_STATUS_NO_LOGIC_DEVICE_FOUND = -17  # 논리 디바이스를 찾을 수 없음
CAMERA_STATUS_DEVICE_IS_OPENED = -18  # 디바이스가 이미 열려있음
CAMERA_STATUS_DEVICE_IS_CLOSED = -19  # 디바이스가 이미 닫혀있음
CAMERA_STATUS_DEVICE_VEDIO_CLOSED = -20  # 디바이스 비디오가 열리지 않음. 녹화 관련 함수를 호출할 때 카메라 비디오가 열리지 않았다면 이 오류를 반환함.
CAMERA_STATUS_NO_MEMORY = -21  # 시스템 메모리 부족
CAMERA_STATUS_FILE_CREATE_FAILED = -22  # 파일 생성 실패
CAMERA_STATUS_FILE_INVALID = -23  # 파일 포맷이 유효하지 않음
CAMERA_STATUS_WRITE_PROTECTED = -24  # 쓰기 보호됨, 쓸 수 없음
CAMERA_STATUS_GRAB_FAILED = -25  # 데이터 촬영 실패
CAMERA_STATUS_LOST_DATA = -26  # 데이터 손실, 불완전
CAMERA_STATUS_EOF_ERROR = -27  # 프레임 종료 문자를 받지 못함
CAMERA_STATUS_BUSY = -28  # 바쁨(이전 작업이 아직 진행 중), 이번 작업을 수행할 수 없음
CAMERA_STATUS_WAIT = -29  # 대기 필요(작업 조건이 성립되지 않음), 다시 시도할 수 있음
CAMERA_STATUS_IN_PROCESS = -30  # 진행 중, 이미 작업됨
CAMERA_STATUS_IIC_ERROR = -31  # IIC 전송 오류
CAMERA_STATUS_SPI_ERROR = -32  # SPI 전송 오류
CAMERA_STATUS_USB_CONTROL_ERROR = -33  # USB 제어 전솨 오류
CAMERA_STATUS_USB_BULK_ERROR = -34  # USB BULK 전송 오류
CAMERA_STATUS_SOCKET_INIT_ERROR = -35  # 네트워크 전송 소켓 초기화 실패
CAMERA_STATUS_GIGE_FILTER_INIT_ERROR = -36  # 네트워크 카메라 커널 필터 드라이버 초기화 실패, 드라이버가 올바르게 설치되었는지 확인하거나 다시 설치하세요.
CAMERA_STATUS_NET_SEND_ERROR = -37  # 네트워크 데이터 전송 오류
CAMERA_STATUS_DEVICE_LOST = -38  # 네트워크 카메라와의 연결 손실, 하트비트 검사 시간 초과
CAMERA_STATUS_DATA_RECV_LESS = -39  # 받은 바이트 수가 요청한 것보다 적음 
CAMERA_STATUS_FUNCTION_LOAD_FAILED = -40  # 파일에서 프로그램 로드 실패
CAMERA_STATUS_CRITICAL_FILE_LOST = -41  # 프로그램 실행에 필수적인 파일이 손실됨.
CAMERA_STATUS_SENSOR_ID_DISMATCH = -42  # 펌웨어와 프로그램이 일치하지 않음, 잘못된 펌웨어를 다운로드했음.
CAMERA_STATUS_OUT_OF_RANGE = -43  # 매개변수가 유효 범위를 벗어남.   
CAMERA_STATUS_REGISTRY_ERROR = -44  # 설치 프로그램 등록 오류. 프로그램을 다시 설치하거나 설치 디렉터리의 Setup/Installer.exe를 실행하세요
CAMERA_STATUS_ACCESS_DENY = -45  # 접근 금지. 지정된 카메라가 이미 다른 프로그램에 의해 사용 중일 때, 해당 카메라에 다시 접근을 요청하면 이 상태를 반환함. (하나의 카메라는 여러 프로그램에서 동시에 접근할 수 없음) 
#AIA 표준 호환 오류 코드
CAMERA_AIA_PACKET_RESEND = 0x0100 #해당 프레임은 재전송이 필요함
CAMERA_AIA_NOT_IMPLEMENTED = 0x8001 #디바이스가 지원하지 않는 명령
CAMERA_AIA_INVALID_PARAMETER = 0x8002 #명령 매개변수가 비정상
CAMERA_AIA_INVALID_ADDRESS = 0x8003 #접근할 수 없는 주소
CAMERA_AIA_WRITE_PROTECT = 0x8004 #접근하는 객체를 쓸 수 없음
CAMERA_AIA_BAD_ALIGNMENT = 0x8005 #접근하는 주소가 요구사항에 따라 정렬되지 않음
CAMERA_AIA_ACCESS_DENIED = 0x8006 #접근 권한이 없음
CAMERA_AIA_BUSY = 0x8007 #명령이 처리 중
CAMERA_AIA_DEPRECATED = 0x8008 #0x8008-0x0800B  0x800F  해당 명령은 이미 폐기됨
CAMERA_AIA_PACKET_UNAVAILABLE = 0x800C #패킷이 유효하지 않음
CAMERA_AIA_DATA_OVERRUN = 0x800D #데이터 오버플로우, 일반적으로 받은 데이터가 필요한 것보다 많음
CAMERA_AIA_INVALID_HEADER = 0x800E #데이터 패킷 헤더의 일부 영역이 프로토콜과 일치하지 않음
CAMERA_AIA_PACKET_NOT_YET_AVAILABLE = 0x8010 #이미지 패킷 데이터가 아직 준비되지 않음, 주로 트리거 모드에서 사용, 애플리케이션 접근 시간 초과
CAMERA_AIA_PACKET_AND_PREV_REMOVED_FROM_MEMORY = 0x8011 #접근해야 할 패킷이 이미 존재하지 않음. 주로 재전송 시 데이터가 이미 버퍼에 없을 때 사용
CAMERA_AIA_PACKET_REMOVED_FROM_MEMORY = 0x8012 #CAMERA_AIA_PACKET_AND_PREV_REMOVED_FROM_MEMORY와 동일
CAMERA_AIA_NO_REF_TIME = 0x0813 #참조 클럭 소스가 없음. 주로 시간 동기화 명령 실행 시 사용
CAMERA_AIA_PACKET_TEMPORARILY_UNAVAILABLE = 0x0814 #채널 대역폭 문제로 인해 현재 패킷을 일시적으로 사용할 수 없음, 나중에 접근해야 함
CAMERA_AIA_OVERFLOW = 0x0815 #디바이스 단의 데이터 오버플로우, 일반적으로 큐가 꽉 찬 상태
CAMERA_AIA_ACTION_LATE = 0x0816 #명령 실행이 이미 유효한 지정 시간을 초과함
CAMERA_AIA_ERROR = 0x8FFF   #오류

# 이미지 포맷 정의
CAMERA_MEDIA_TYPE_MONO = 0x01000000
CAMERA_MEDIA_TYPE_RGB = 0x02000000
CAMERA_MEDIA_TYPE_COLOR = 0x02000000
CAMERA_MEDIA_TYPE_OCCUPY1BIT = 0x00010000
CAMERA_MEDIA_TYPE_OCCUPY2BIT = 0x00020000
CAMERA_MEDIA_TYPE_OCCUPY4BIT = 0x00040000
CAMERA_MEDIA_TYPE_OCCUPY8BIT = 0x00080000
CAMERA_MEDIA_TYPE_OCCUPY10BIT = 0x000A0000
CAMERA_MEDIA_TYPE_OCCUPY12BIT = 0x000C0000
CAMERA_MEDIA_TYPE_OCCUPY16BIT = 0x00100000
CAMERA_MEDIA_TYPE_OCCUPY24BIT = 0x00180000
CAMERA_MEDIA_TYPE_OCCUPY32BIT = 0x00200000
CAMERA_MEDIA_TYPE_OCCUPY36BIT = 0x00240000
CAMERA_MEDIA_TYPE_OCCUPY48BIT = 0x00300000
CAMERA_MEDIA_TYPE_EFFECTIVE_PIXEL_SIZE_MASK = 0x00FF0000
CAMERA_MEDIA_TYPE_EFFECTIVE_PIXEL_SIZE_SHIFT = 16
CAMERA_MEDIA_TYPE_ID_MASK = 0x0000FFFF
CAMERA_MEDIA_TYPE_COUNT = 0x46

#mono
CAMERA_MEDIA_TYPE_MONO1P = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY1BIT | 0x0037)
CAMERA_MEDIA_TYPE_MONO2P = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY2BIT | 0x0038)
CAMERA_MEDIA_TYPE_MONO4P = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY4BIT | 0x0039)
CAMERA_MEDIA_TYPE_MONO8 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY8BIT | 0x0001)
CAMERA_MEDIA_TYPE_MONO8S = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY8BIT | 0x0002)
CAMERA_MEDIA_TYPE_MONO10 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0003)
CAMERA_MEDIA_TYPE_MONO10_PACKED = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x0004)
CAMERA_MEDIA_TYPE_MONO12 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0005)
CAMERA_MEDIA_TYPE_MONO12_PACKED = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x0006)
CAMERA_MEDIA_TYPE_MONO14 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0025)
CAMERA_MEDIA_TYPE_MONO16 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0007)

# Bayer
CAMERA_MEDIA_TYPE_BAYGR8 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY8BIT | 0x0008)
CAMERA_MEDIA_TYPE_BAYRG8 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY8BIT | 0x0009)
CAMERA_MEDIA_TYPE_BAYGB8 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY8BIT | 0x000A)
CAMERA_MEDIA_TYPE_BAYBG8 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY8BIT | 0x000B)

CAMERA_MEDIA_TYPE_BAYGR10_MIPI = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY10BIT | 0x0026)
CAMERA_MEDIA_TYPE_BAYRG10_MIPI = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY10BIT | 0x0027)
CAMERA_MEDIA_TYPE_BAYGB10_MIPI = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY10BIT | 0x0028)
CAMERA_MEDIA_TYPE_BAYBG10_MIPI = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY10BIT | 0x0029)

CAMERA_MEDIA_TYPE_BAYGR10 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x000C)
CAMERA_MEDIA_TYPE_BAYRG10 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x000D)
CAMERA_MEDIA_TYPE_BAYGB10 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x000E)
CAMERA_MEDIA_TYPE_BAYBG10 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x000F)

CAMERA_MEDIA_TYPE_BAYGR12 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0010)
CAMERA_MEDIA_TYPE_BAYRG12 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0011)
CAMERA_MEDIA_TYPE_BAYGB12 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0012)
CAMERA_MEDIA_TYPE_BAYBG12 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0013)

CAMERA_MEDIA_TYPE_BAYGR10_PACKED = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x0026)
CAMERA_MEDIA_TYPE_BAYRG10_PACKED = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x0027)
CAMERA_MEDIA_TYPE_BAYGB10_PACKED = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x0028)
CAMERA_MEDIA_TYPE_BAYBG10_PACKED = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x0029)

CAMERA_MEDIA_TYPE_BAYGR12_PACKED = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x002A)
CAMERA_MEDIA_TYPE_BAYRG12_PACKED = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x002B)
CAMERA_MEDIA_TYPE_BAYGB12_PACKED = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x002C)
CAMERA_MEDIA_TYPE_BAYBG12_PACKED = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x002D)

CAMERA_MEDIA_TYPE_BAYGR16 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x002E)
CAMERA_MEDIA_TYPE_BAYRG16 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x002F)
CAMERA_MEDIA_TYPE_BAYGB16 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0030)
CAMERA_MEDIA_TYPE_BAYBG16 = (CAMERA_MEDIA_TYPE_MONO | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0031)

# RGB
CAMERA_MEDIA_TYPE_RGB8 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY24BIT | 0x0014)
CAMERA_MEDIA_TYPE_BGR8 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY24BIT | 0x0015)
CAMERA_MEDIA_TYPE_RGBA8 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY32BIT | 0x0016)
CAMERA_MEDIA_TYPE_BGRA8 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY32BIT | 0x0017)
CAMERA_MEDIA_TYPE_RGB10 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY48BIT | 0x0018)
CAMERA_MEDIA_TYPE_BGR10 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY48BIT | 0x0019)
CAMERA_MEDIA_TYPE_RGB12 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY48BIT | 0x001A)
CAMERA_MEDIA_TYPE_BGR12 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY48BIT | 0x001B)
CAMERA_MEDIA_TYPE_RGB16 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY48BIT | 0x0033)
CAMERA_MEDIA_TYPE_RGB10V1_PACKED = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY32BIT | 0x001C)
CAMERA_MEDIA_TYPE_RGB10P32 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY32BIT | 0x001D)
CAMERA_MEDIA_TYPE_RGB12V1_PACKED = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY36BIT | 0X0034)
CAMERA_MEDIA_TYPE_RGB565P = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0035)
CAMERA_MEDIA_TYPE_BGR565P = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0X0036)

# YUV and YCbCr
CAMERA_MEDIA_TYPE_YUV411_8_UYYVYY = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x001E)
CAMERA_MEDIA_TYPE_YUV422_8_UYVY = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x001F)
CAMERA_MEDIA_TYPE_YUV422_8 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0032)
CAMERA_MEDIA_TYPE_YUV8_UYV = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY24BIT | 0x0020)
CAMERA_MEDIA_TYPE_YCBCR8_CBYCR = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY24BIT | 0x003A)
#CAMERA_MEDIA_TYPE_YCBCR422_8 : YYYYCbCrCbCr
CAMERA_MEDIA_TYPE_YCBCR422_8 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x003B)
CAMERA_MEDIA_TYPE_YCBCR422_8_CBYCRY = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0043)
CAMERA_MEDIA_TYPE_YCBCR411_8_CBYYCRYY = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x003C)
CAMERA_MEDIA_TYPE_YCBCR601_8_CBYCR = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY24BIT | 0x003D)
CAMERA_MEDIA_TYPE_YCBCR601_422_8 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x003E)
CAMERA_MEDIA_TYPE_YCBCR601_422_8_CBYCRY = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0044)
CAMERA_MEDIA_TYPE_YCBCR601_411_8_CBYYCRYY = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x003F)
CAMERA_MEDIA_TYPE_YCBCR709_8_CBYCR = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY24BIT | 0x0040)
CAMERA_MEDIA_TYPE_YCBCR709_422_8 = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0041)
CAMERA_MEDIA_TYPE_YCBCR709_422_8_CBYCRY = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY16BIT | 0x0045)
CAMERA_MEDIA_TYPE_YCBCR709_411_8_CBYYCRYY = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY12BIT | 0x0042)

# RGB Planar
CAMERA_MEDIA_TYPE_RGB8_PLANAR = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY24BIT | 0x0021)
CAMERA_MEDIA_TYPE_RGB10_PLANAR = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY48BIT | 0x0022)
CAMERA_MEDIA_TYPE_RGB12_PLANAR = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY48BIT | 0x0023)
CAMERA_MEDIA_TYPE_RGB16_PLANAR = (CAMERA_MEDIA_TYPE_COLOR | CAMERA_MEDIA_TYPE_OCCUPY48BIT | 0x0024)

# 저장 포맷
FILE_JPG = 1
FILE_BMP = 2
FILE_RAW = 4
FILE_PNG = 8 
FILE_BMP_8BIT = 16
FILE_PNG_8BIT = 32
FILE_RAW_16BIT = 64

# 트리거 신호
EXT_TRIG_LEADING_EDGE = 0
EXT_TRIG_TRAILING_EDGE = 1
EXT_TRIG_HIGH_LEVEL = 2
EXT_TRIG_LOW_LEVEL = 3
EXT_TRIG_DOUBLE_EDGE = 4

# IO 모드
IOMODE_TRIG_INPUT = 0
IOMODE_STROBE_OUTPUT = 1
IOMODE_GP_INPUT = 2
IOMODE_GP_OUTPUT = 3
IOMODE_PWM_OUTPUT = 4


# 카메라 작업 예외 정보
class CameraException(Exception):
	"""카메라 예외 클래스"""
	def __init__(self, error_code):
		super(CameraException, self).__init__()
		self.error_code = error_code
		self.message = CameraGetErrorString(error_code)

	def __str__(self):
		return 'error_code:{} message:{}'.format(self.error_code, self.message)

class MvStructure(Structure):
	def __str__(self):
		strs = []
		for field in self._fields_:
			name = field[0]
			value = getattr(self, name)
			if isinstance(value, type(b'')):
				value = _string_buffer_to_str(value)
			strs.append("{}:{}".format(name, value))
		return '\n'.join(strs)

	def __repr__(self):
		return self.__str__()

	def clone(self):
		obj = type(self)()
		memmove(byref(obj), byref(self), sizeof(self))
		return obj

# 카메라의 디바이스 정보, 읽기 전용 정보이므로 수정하지 마세요
class tSdkCameraDevInfo(MvStructure):
	_fields_ = [("acProductSeries", c_char * 32), #제품 시리즈
				("acProductName", c_char * 32), #제품명
				("acFriendlyName", c_char * 32), #제품 별명
				("acLinkName", c_char * 32), #커널 심볼 연결명, 내부 사용
				("acDriverVersion", c_char * 32), #드라이버 버전
				("acSensorType", c_char * 32), #센서 타입
				("acPortType", c_char * 32), #인터페이스 타입
				("acSn", c_char * 32), #제품 고유 일련번호
				("uInstance", c_uint)] #해당 모델 카메라의 컴퓨터에서의 인스턴스 인덱스 번호, 동일 모델 다중 카메라 구분용

	def GetProductSeries(self):
		return _string_buffer_to_str(self.acProductSeries)
	def GetProductName(self):
		return _string_buffer_to_str(self.acProductName)
	def GetFriendlyName(self):
		return _string_buffer_to_str(self.acFriendlyName)
	def GetLinkName(self):
		return _string_buffer_to_str(self.acLinkName)
	def GetDriverVersion(self):
		return _string_buffer_to_str(self.acDriverVersion)
	def GetSensorType(self):
		return _string_buffer_to_str(self.acSensorType)
	def GetPortType(self):
		return _string_buffer_to_str(self.acPortType)
	def GetSn(self):
		return _string_buffer_to_str(self.acSn)

# 카메라의 해상도 설정 범위
class tSdkResolutionRange(MvStructure):
	_fields_ = [("iHeightMax", c_int), 	#이미지 최대 높이
				("iHeightMin", c_int), 	#이미지 최소 높이
				("iWidthMax", c_int), 	#이미지 최대 너비
				("iWidthMin", c_int), 	#이미지 최소 너비
				("uSkipModeMask", c_uint), 		#SKIP 모드 마스크, 0이면 SKIP을 지원하지 않음. bit0이 1이면 SKIP 2x2 지원, bit1이 1이면 SKIP 3x3 지원....
				("uBinSumModeMask", c_uint), 	#BIN(합계) 모드 마스크, 0이면 BIN을 지원하지 않음. bit0이 1이면 BIN 2x2 지원, bit1이 1이면 BIN 3x3 지원....
				("uBinAverageModeMask", c_uint),#BIN(평균) 모드 마스크, 0이면 BIN을 지원하지 않음. bit0이 1이면 BIN 2x2 지원, bit1이 1이면 BIN 3x3 지원....
				("uResampleMask", c_uint)] 		#하드웨어 리샘플링의 마스크

#카메라의 해상도 설명
class tSdkImageResolution(MvStructure):
	_fields_ = [
		("iIndex", c_int),                # 인덱스 번호, [0,N]은 미리 설정된 해상도를 나타냄(N은 미리 설정된 해상도의 최대 개수, 일반적으로 20을 초과하지 않음), 0xFF는 사용자 정의 해상도(ROI)를 나타냄
		("acDescription", c_char * 32),   # 해당 해상도의 설명 정보. 미리 설정된 해상도일 때만 이 정보가 유효. 사용자 정의 해상도는 이 정보를 무시할 수 있음
		("uBinSumMode", c_uint),          # BIN(합계) 모드, 범위는 tSdkResolutionRange의 uBinSumModeMask를 초과할 수 없음
		("uBinAverageMode", c_uint),      # BIN(평균) 모드, 범위는 tSdkResolutionRange의 uBinAverageModeMask를 초과할 수 없음
		("uSkipMode", c_uint),            # SKIP 사이즈 여부, 0이면 SKIP 모드 금지, 범위는 tSdkResolutionRange의 uSkipModeMask를 초과할 수 없음
		("uResampleMask", c_uint),        # 하드웨어 리샘플링의 마스크
		("iHOffsetFOV", c_int),        # 촬영 시야의 센서 최대 시야 왼쪽 상단에 대한 수직 오프셋
		("iVOffsetFOV", c_int),        # 촬영 시야의 센서 최대 시야 왼쪽 상단에 대한 수평 오프셋
		("iWidthFOV", c_int),          # 촬영 시야의 너비 
		("iHeightFOV", c_int),         # 촬영 시야의 높이
		("iWidth", c_int),             # 카메라 최종 출력 이미지의 너비
		("iHeight", c_int),            # 카메라 최종 출력 이미지의 높이
		("iWidthZoomHd", c_int),       # 하드웨어 확대/축소의 너비, 이 작업이 필요하지 않은 해상도의 경우 이 변수를 0으로 설정.
		("iHeightZoomHd", c_int),      # 하드웨어 확대/축소의 높이, 이 작업이 필요하지 않은 해상도의 경우 이 변수를 0으로 설정.
		("iWidthZoomSw", c_int),       # 소프트웨어 확대/축소의 너비, 이 작업이 필요하지 않은 해상도의 경우 이 변수를 0으로 설정.
		("iHeightZoomSw", c_int),      # 소프트웨어 확대/축소의 높이, 이 작업이 필요하지 않은 해상도의 경우 이 변수를 0으로 설정.
	]

	def GetDescription(self):
		return _string_buffer_to_str(self.acDescription)

#카메라 화이트밸런스 모드 설명 정보
class tSdkColorTemperatureDes(MvStructure):
	_fields_ = [
		("iIndex", c_int),				# 모드 인덱스 번호
		("acDescription", c_char * 32), # 설명 정보
	]

	def GetDescription(self):
		return _string_buffer_to_str(self.acDescription)

#카메라 프레임레이트 설명 정보
class tSdkFrameSpeed(MvStructure):
	_fields_ = [
		("iIndex", c_int),				# 프레임레이트 인덱스 번호, 일반적으로 0은 저속 모드, 1은 일반 모드, 2는 고속 모드에 해당      
		("acDescription", c_char * 32), # 설명 정보
	]

	def GetDescription(self):
		return _string_buffer_to_str(self.acDescription)

#카메라 노출 기능 범위 정의
class tSdkExpose(MvStructure):
	_fields_ = [
		("uiTargetMin", c_uint),       #자동 노출 밝기 목표 최소값
		("uiTargetMax", c_uint),       #자동 노출 밝기 목표 최대값
		("uiAnalogGainMin", c_uint),   #아날로그 게인의 최소값, 단위는 fAnalogGainStep에서 정의      
		("uiAnalogGainMax", c_uint),   #아날로그 게인의 최대값, 단위는 fAnalogGainStep에서 정의        
		("fAnalogGainStep", c_float),  #아날로그 게인이 1 증가할 때맄다 해당하는 증가 배수. 예: uiAnalogGainMin은 일반적으로 16, fAnalogGainStep은 일반적으로 0.125이므로 최소 배수는 16*0.125 = 2배
		("uiExposeTimeMin", c_uint),   #수동 모드에서 노출 시간의 최소값, 단위: 라인. CameraGetExposureLineTime을 통해 한 라인에 해당하는 시간(마이크로초)을 얻어 전체 프레임의 노출 시간을 구할 수 있음    
		("uiExposeTimeMax", c_uint),   #수동 모드에서 노출 시간의 최대값, 단위: 라인
	]

#트리거 모드 설명
class tSdkTrigger(MvStructure):
	_fields_ = [
		("iIndex", c_int),				# 모드 인덱스 번호      
		("acDescription", c_char * 32), # 설명 정보
	]

	def GetDescription(self):
		return _string_buffer_to_str(self.acDescription)

#전송 패킷 크기 설명(주로 네트워크 카메라에 유효)
class tSdkPackLength(MvStructure):
	_fields_ = [
		("iIndex", c_int),				# 모드 인덱스 번호      
		("acDescription", c_char * 32), # 설명 정보
		("iPackSize", c_uint),
	]

	def GetDescription(self):
		return _string_buffer_to_str(self.acDescription)

#미리 설정된 LUT 테이블 설명
class tSdkPresetLut(MvStructure):
	_fields_ = [
		("iIndex", c_int),				# 번호
		("acDescription", c_char * 32), # 설명 정보
	]

	def GetDescription(self):
		return _string_buffer_to_str(self.acDescription)

#AE 알고리즘 설명
class tSdkAeAlgorithm(MvStructure):
	_fields_ = [
		("iIndex", c_int),				# 번호
		("acDescription", c_char * 32), # 설명 정보
	]

	def GetDescription(self):
		return _string_buffer_to_str(self.acDescription)

#RAW에서 RGB 변환 알고리즘 설명
class tSdkBayerDecodeAlgorithm(MvStructure):
	_fields_ = [
		("iIndex", c_int),				# 번호
		("acDescription", c_char * 32), # 설명 정보
	]

	def GetDescription(self):
		return _string_buffer_to_str(self.acDescription)

#프레임레이트 통계 정보
class tSdkFrameStatistic(MvStructure):
	_fields_ = [
		("iTotal", c_int),        #현재 촬영된 총 프레임 수(오류 프레임 포함)
		("iCapture", c_int),      #현재 촬영된 유효한 프레임의 수량    
		("iLost", c_int),         #현재 손실된 프레임의 수량    
	]

#카메라 출력 이미지 데이터 포맷
class tSdkMediaType(MvStructure):
	_fields_ = [
		("iIndex", c_int),				# 포맷 종류 번호
		("acDescription", c_char * 32), # 설명 정보
		("iMediaType", c_uint),			# 해당 이미지 포맷 코드, 예: CAMERA_MEDIA_TYPE_BAYGR8.
	]

	def GetDescription(self):
		return _string_buffer_to_str(self.acDescription)

#감마의 설정 범위
class tGammaRange(MvStructure):
	_fields_ = [
		("iMin", c_int),       #최소값
		("iMax", c_int),       #최대값
	]

#대비도의 설정 범위
class tContrastRange(MvStructure):
	_fields_ = [
		("iMin", c_int),       #최소값
		("iMax", c_int),       #최대값
	]

#RGB 3채널 디지털 게인의 설정 범위
class tRgbGainRange(MvStructure):
	_fields_ = [
		("iRGainMin", c_int),   #빨간색 게인의 최소값
		("iRGainMax", c_int),   #빨간색 게인의 최대값
		("iGGainMin", c_int),   #녹색 게인의 최소값
		("iGGainMax", c_int),   #녹색 게인의 최대값
		("iBGainMin", c_int),   #파란색 게인의 최소값
		("iBGainMax", c_int),   #파란색 게인의 최대값
	]

#채도 설정의 범위
class tSaturationRange(MvStructure):
	_fields_ = [
		("iMin", c_int),       #최소값
		("iMax", c_int),       #최대값
	]

#선명도의 설정 범위
class tSharpnessRange(MvStructure):
	_fields_ = [
		("iMin", c_int),       #최소값
		("iMax", c_int),       #최대값
	]

#ISP 모듈의 사용 가능 정보
class tSdkIspCapacity(MvStructure):
	_fields_ = [
		("bMonoSensor", c_int),        #해당 모델 카메라가 흑백 카메라인지를 나타냄. 흑백 카메라라면 색상 관련 기능을 모두 조절할 수 없음
		("bWbOnce", c_int),            #해당 모델 카메라가 수동 화이트밸런스 기능을 지원하는지 나타냄  
		("bAutoWb", c_int),            #해당 모델 카메라가 자동 화이트밸런스 기능을 지원하는지 나타냄
		("bAutoExposure", c_int),      #해당 모델 카메라가 자동 노출 기능을 지원하는지 나타냄
		("bManualExposure", c_int),    #해당 모델 카메라가 수동 노출 기능을 지원하는지 나타냄
		("bAntiFlick", c_int),         #해당 모델 카메라가 안티 플리커 기능을 지원하는지 나타냄
		("bDeviceIsp", c_int),         #해당 모델 카메라가 하드웨어 ISP 기능을 지원하는지 나타냄
		("bForceUseDeviceIsp", c_int), #bDeviceIsp와 bForceUseDeviceIsp가 동시에 TRUE일 때, 하드웨어 ISP만 강제 사용하며 취소할 수 없음을 나타냄.
		("bZoomHD", c_int),            #카메라 하드웨어가 이미지 확대/축소 출력을 지원하는지(축소만 가능).
	]

# 통합된 디바이스 설명 정보 정의, 이러한 정보들은 동적 UI 구축에 사용될 수 있음
class tSdkCameraCapbility(MvStructure):
	_fields_ = [
		("pTriggerDesc", POINTER(tSdkTrigger)),
		("iTriggerDesc", c_int),	#트리거 모드의 개수, 즉 pTriggerDesc 배열의 크기
		("pImageSizeDesc", POINTER(tSdkImageResolution)),
		("iImageSizeDesc", c_int),	#미리 설정된 해상도의 개수, 즉 pImageSizeDesc 배열의 크기 
		("pClrTempDesc", POINTER(tSdkColorTemperatureDes)),
		("iClrTempDesc", c_int),	#미리 설정된 색온 개수
		("pMediaTypeDesc", POINTER(tSdkMediaType)),
		("iMediaTypeDesc", c_int),	#카메라 출력 이미지 포맷의 종류 개수, 즉 pMediaTypeDesc 배열의 크기.
		("pFrameSpeedDesc", POINTER(tSdkFrameSpeed)), #조절 가능한 프레임 속도 타입, 인터페이스에서 일반, 고속, 초고속 세 가지 속도 설정에 해당
		("iFrameSpeedDesc", c_int), #조절 가능한 프레임 속도 타입의 개수, 즉 pFrameSpeedDesc 배열의 크기.
		("pPackLenDesc", POINTER(tSdkPackLength)), #전송 패킷 길이, 일반적으로 네트워크 디바이스에 사용
		("iPackLenDesc", c_int), #선택 가능한 전송 패킷 길이의 개수, 즉 pPackLenDesc 배열의 크기. 
		("iOutputIoCounts", c_int),        #프로그래밍 가능한 출력 IO의 개수
		("iInputIoCounts", c_int),         #프로그래밍 가능한 입력 IO의 개수
		("pPresetLutDesc", POINTER(tSdkPresetLut)), #카메라에 미리 설정된 LUT 테이블
		("iPresetLut", c_int),             #카메라에 미리 설정된 LUT 테이블의 개수, 즉 pPresetLutDesc 배열의 크기
		("iUserDataMaxLen", c_int),        #해당 카메라에서 사용자 데이터 영역 저장에 사용되는 최대 길이를 나타냄. 0이면 없음을 의미.
		("bParamInDevice", c_int),         #해당 디바이스가 디바이스에서 매개변수 그룹 읽기/쓰기를 지원하는지 나타냄. 1은 지원, 0은 비지원.
		("pAeAlmSwDesc", POINTER(tSdkAeAlgorithm)),#소프트웨어 자동 노출 알고리즘 설명
		("iAeAlmSwDesc", c_int),           #소프트웨어 자동 노출 알고리즘 개수
		("pAeAlmHdDesc", POINTER(tSdkAeAlgorithm)),#하드웨어 자동 노출 알고리즘 설명, NULL이면 하드웨어 자동 노출을 지원하지 않음을 나타냄
		("iAeAlmHdDesc", c_int),           #하드웨어 자동 노출 알고리즘 개수, 0이면 하드웨어 자동 노출을 지원하지 않음을 나타냄
		("pBayerDecAlmSwDesc", POINTER(tSdkBayerDecodeAlgorithm)),#소프트웨어 Bayer에서 RGB 데이터로 변환하는 알고리즘 설명
		("iBayerDecAlmSwDesc", c_int),     #소프트웨어 Bayer에서 RGB 데이터로 변환하는 알고리즘 개수
		("pBayerDecAlmHdDesc", POINTER(tSdkBayerDecodeAlgorithm)),#하드웨어 Bayer에서 RGB 데이터로 변환하는 알고리즘 설명, NULL이면 지원하지 않음을 나타냄
		("iBayerDecAlmHdDesc", c_int),     #하드웨어 Bayer에서 RGB 데이터로 변환하는 알고리즘 개수, 0이면 지원하지 않음을 나타냄

		# 이미지 매개변수의 조정 범위 정의, 동적 UI 구축에 사용
		("sExposeDesc", tSdkExpose),      #노출의 범위 값
		("sResolutionRange", tSdkResolutionRange), #해상도 범위 설명  
		("sRgbGainRange", tRgbGainRange),    #이미지 디지털 게인 범위 설명  
		("sSaturationRange", tSaturationRange), #채도 범위 설명  
		("sGammaRange", tGammaRange),      #감마 범위 설명  
		("sContrastRange", tContrastRange),   #대비도 범위 설명  
		("sSharpnessRange", tSharpnessRange),  #선명도 범위 설명  
		("sIspCapacity", tSdkIspCapacity),     #ISP 능력 설명
	]

#이미지 프레임 헤더 정보
class tSdkFrameHead(MvStructure):
	_fields_ = [
		("uiMediaType", c_uint),      # 이미지 포맷, Image Format
		("uBytes", c_uint),           # 이미지 데이터 바이트 수, Total bytes
		("iWidth", c_int),            # 너비 Image width
		("iHeight", c_int),           # 높이 Image height
		("iWidthZoomSw", c_int),      # 소프트웨어 확대/축소의 너비, 소프트웨어 자르기가 필요하지 않은 이미지의 경우 이 변수를 0으로 설정.
		("iHeightZoomSw", c_int),     # 소프트웨어 확대/축소의 높이, 소프트웨어 자르기가 필요하지 않은 이미지의 경우 이 변수를 0으로 설정.
		("bIsTrigger", c_int),        # 트리거 프레임인지 여부를 나타냄 is trigger 
		("uiTimeStamp", c_uint),      # 해당 프레임의 촬영 시간, 단위 0.1밀리초 
		("uiExpTime", c_uint),        # 현재 이미지의 노출값, 단위는 마이크로초us
		("fAnalogGain", c_float),     # 현재 이미지의 아날로그 게인 배수
		("iGamma", c_int),            # 해당 프레임 이미지의 감마 설정값, LUT 모드가 동적 매개변수 생성일 때만 유효, 다른 모드에서는 -1
		("iContrast", c_int),         # 해당 프레임 이미지의 대비도 설정값, LUT 모드가 동적 매개변수 생성일 때만 유효, 다른 모드에서는 -1
		("iSaturation", c_int),       # 해당 프레임 이미지의 채도 설정값, 흑백 카메라에는 의미가 없으므로 0
		("fRgain", c_float),          # 해당 프레임 이미지 처리의 빨간색 디지털 게인 배수, 흑백 카메라에는 의미가 없으므로 1
		("fGgain", c_float),          # 해당 프레임 이미지 처리의 녹색 디지털 게인 배수, 흑백 카메라에는 의미가 없으므로 1
		("fBgain", c_float),          # 해당 프레임 이미지 처리의 파란색 디지털 게인 배수, 흑백 카메라에는 의미가 없으므로 1
	]

# Grabber 통계 정보
class tSdkGrabberStat(MvStructure):
	_fields_ = [
		("Width", c_int),           # 프레임 이미지 크기
		("Height", c_int),	        # 프레임 이미지 크기
		("Disp", c_int),			# 디스플레이 프레임 수량
		("Capture", c_int),		    # 촬영된 유효 프레임의 수량
		("Lost", c_int),			# 손실된 프레임의 수량
		("Error", c_int),			# 오류 프레임의 수량
		("DispFps", c_float),		# 디스플레이 프레임레이트
		("CapFps", c_float),		# 캡처 프레임레이트
	]

# 메서드 콜백 보조 클래스
class method(object):
	def __init__(self, FuncType):
		super(method, self).__init__()
		self.FuncType = FuncType
		self.cache = {}

	def __call__(self, cb):
		self.cb = cb
		return self

	def __get__(self, obj, objtype):
		try:
			return self.cache[obj]
		except KeyError as e:
			def cl(*args):
				return self.cb(obj, *args)
			r = self.cache[obj] = self.FuncType(cl)
			return r

# 이미지 캡처 콜백 함수 정의
CAMERA_SNAP_PROC = CALLBACK_FUNC_TYPE(None, c_int, c_void_p, POINTER(tSdkFrameHead), c_void_p)

# 카메라 연결 상태 콜백
CAMERA_CONNECTION_STATUS_CALLBACK = CALLBACK_FUNC_TYPE(None, c_int, c_uint, c_uint, c_void_p)

# 비동기 이미지 캡처 완료 콜백
pfnCameraGrabberSaveImageComplete = CALLBACK_FUNC_TYPE(None, c_void_p, c_void_p, c_int, c_void_p)

# 프레임 모니터링 콜백
pfnCameraGrabberFrameListener = CALLBACK_FUNC_TYPE(c_int, c_void_p, c_int, c_void_p, POINTER(tSdkFrameHead), c_void_p)

# 캡처 장치 이미지 캡처의 콜백
pfnCameraGrabberFrameCallback = CALLBACK_FUNC_TYPE(None, c_void_p, c_void_p, POINTER(tSdkFrameHead), c_void_p)

#-----------------------------------함수 인터페이스------------------------------------------

# 스레드 로컬 저장소
_tls = local()

# 마지막 SDK 호출에서 반환된 오류 코드 저장
def GetLastError():
	try:
		return _tls.last_error
	except AttributeError as e:
		_tls.last_error = 0
		return 0

def SetLastError(err_code):
	_tls.last_error = err_code

def _string_buffer_to_str(buf):
	s = buf if isinstance(buf, type(b'')) else buf.value

	for codec in ('gbk', 'utf-8'):
		try:
			s = s.decode(codec)
			break
		except UnicodeDecodeError as e:
			continue

	if isinstance(s, str):
		return s
	else:
		return s.encode('utf-8')

def _str_to_string_buffer(str):
	if type(str) is type(u''):
		s = str.encode('gbk')
	else:
		s = str.decode('utf-8').encode('gbk')
	return create_string_buffer(s)

def CameraSdkInit(iLanguageSel):
	err_code = _sdk.CameraSdkInit(iLanguageSel)
	SetLastError(err_code)
	return err_code
	
def CameraSetSysOption(optionName, value):
	err_code = _sdk.CameraSetSysOption(_str_to_string_buffer(optionName), _str_to_string_buffer(str(value)))
	SetLastError(err_code)
	return err_code

def CameraEnumerateDevice(MaxCount = 32):
	Nums = c_int(MaxCount)
	pCameraList = (tSdkCameraDevInfo * Nums.value)()
	err_code = _sdk.CameraEnumerateDevice(pCameraList, byref(Nums))
	SetLastError(err_code)
	return pCameraList[0:Nums.value]

def CameraEnumerateDeviceEx():
	return _sdk.CameraEnumerateDeviceEx()

def CameraIsOpened(pCameraInfo):
	pOpened = c_int()
	err_code = _sdk.CameraIsOpened(byref(pCameraInfo), byref(pOpened) )
	SetLastError(err_code)
	return pOpened.value != 0

def CameraInit(pCameraInfo, emParamLoadMode = -1, emTeam = -1):
	pCameraHandle = c_int()
	err_code = _sdk.CameraInit(byref(pCameraInfo), emParamLoadMode, emTeam, byref(pCameraHandle))
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return pCameraHandle.value

def CameraInitEx(iDeviceIndex, emParamLoadMode = -1, emTeam = -1):
	pCameraHandle = c_int()
	err_code = _sdk.CameraInitEx(iDeviceIndex, emParamLoadMode, emTeam, byref(pCameraHandle))
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return pCameraHandle.value

def CameraInitEx2(CameraName):
	pCameraHandle = c_int()
	err_code = _sdk.CameraInitEx2(_str_to_string_buffer(CameraName), byref(pCameraHandle))
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return pCameraHandle.value

def CameraSetCallbackFunction(hCamera, pCallBack, pContext = 0):
	err_code = _sdk.CameraSetCallbackFunction(hCamera, pCallBack, c_void_p(pContext), None)
	SetLastError(err_code)
	return err_code

def CameraUnInit(hCamera):
	err_code = _sdk.CameraUnInit(hCamera)
	SetLastError(err_code)
	return err_code

def CameraGetInformation(hCamera):
	pbuffer = c_char_p()
	err_code = _sdk.CameraGetInformation(hCamera, byref(pbuffer) )
	SetLastError(err_code)
	if err_code == 0 and pbuffer.value is not None:
		return _string_buffer_to_str(pbuffer)
	return ''

def CameraImageProcess(hCamera, pbyIn, pbyOut, pFrInfo):
	err_code = _sdk.CameraImageProcess(hCamera, c_void_p(pbyIn), c_void_p(pbyOut), byref(pFrInfo))
	SetLastError(err_code)
	return err_code

def CameraImageProcessEx(hCamera, pbyIn, pbyOut, pFrInfo, uOutFormat, uReserved):
	err_code = _sdk.CameraImageProcessEx(hCamera, c_void_p(pbyIn), c_void_p(pbyOut), byref(pFrInfo), uOutFormat, uReserved)
	SetLastError(err_code)
	return err_code

def CameraDisplayInit(hCamera, hWndDisplay):
	err_code = _sdk.CameraDisplayInit(hCamera, hWndDisplay)
	SetLastError(err_code)
	return err_code

def CameraDisplayRGB24(hCamera, pFrameBuffer, pFrInfo):
	err_code = _sdk.CameraDisplayRGB24(hCamera, c_void_p(pFrameBuffer), byref(pFrInfo) )
	SetLastError(err_code)
	return err_code

def CameraSetDisplayMode(hCamera, iMode):
	err_code = _sdk.CameraSetDisplayMode(hCamera, iMode)
	SetLastError(err_code)
	return err_code

def CameraSetDisplayOffset(hCamera, iOffsetX, iOffsetY):
	err_code = _sdk.CameraSetDisplayOffset(hCamera, iOffsetX, iOffsetY)
	SetLastError(err_code)
	return err_code

def CameraSetDisplaySize(hCamera, iWidth, iHeight):
	err_code = _sdk.CameraSetDisplaySize(hCamera, iWidth, iHeight)
	SetLastError(err_code)
	return err_code

def CameraGetImageBuffer(hCamera, wTimes):
	pbyBuffer = c_void_p()
	pFrameInfo = tSdkFrameHead()
	err_code = _sdk.CameraGetImageBuffer(hCamera, byref(pFrameInfo), byref(pbyBuffer), wTimes)
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return (pbyBuffer.value, pFrameInfo)

def CameraGetImageBufferEx(hCamera, wTimes):
	_sdk.CameraGetImageBufferEx.restype = c_void_p
	piWidth = c_int()
	piHeight = c_int()
	pFrameBuffer = _sdk.CameraGetImageBufferEx(hCamera, byref(piWidth), byref(piHeight), wTimes)
	err_code = CAMERA_STATUS_SUCCESS if pFrameBuffer else CAMERA_STATUS_TIME_OUT
	SetLastError(err_code)
	if pFrameBuffer:
		return (pFrameBuffer, piWidth.value, piHeight.value)
	else:
		raise CameraException(err_code)

def CameraSnapToBuffer(hCamera, wTimes):
	pbyBuffer = c_void_p()
	pFrameInfo = tSdkFrameHead()
	err_code = _sdk.CameraSnapToBuffer(hCamera, byref(pFrameInfo), byref(pbyBuffer), wTimes)
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return (pbyBuffer.value, pFrameInfo)

def CameraReleaseImageBuffer(hCamera, pbyBuffer):
	err_code = _sdk.CameraReleaseImageBuffer(hCamera, c_void_p(pbyBuffer) )
	SetLastError(err_code)
	return err_code

def CameraPlay(hCamera):
	err_code = _sdk.CameraPlay(hCamera)
	SetLastError(err_code)
	return err_code

def CameraPause(hCamera):
	err_code = _sdk.CameraPause(hCamera)
	SetLastError(err_code)
	return err_code

def CameraStop(hCamera):
	err_code = _sdk.CameraStop(hCamera)
	SetLastError(err_code)
	return err_code

def CameraInitRecord(hCamera, iFormat, pcSavePath, b2GLimit, dwQuality, iFrameRate):
	err_code = _sdk.CameraInitRecord(hCamera, iFormat, _str_to_string_buffer(pcSavePath), b2GLimit, dwQuality, iFrameRate)
	SetLastError(err_code)
	return err_code

def CameraStopRecord(hCamera):
	err_code = _sdk.CameraStopRecord(hCamera)
	SetLastError(err_code)
	return err_code

def CameraPushFrame(hCamera, pbyImageBuffer, pFrInfo):
	err_code = _sdk.CameraPushFrame(hCamera, c_void_p(pbyImageBuffer), byref(pFrInfo) )
	SetLastError(err_code)
	return err_code

def CameraSaveImage(hCamera, lpszFileName, pbyImageBuffer, pFrInfo, byFileType, byQuality):
	err_code = _sdk.CameraSaveImage(hCamera, _str_to_string_buffer(lpszFileName), c_void_p(pbyImageBuffer), byref(pFrInfo), byFileType, byQuality)
	SetLastError(err_code)
	return err_code

def CameraSaveImageEx(hCamera, lpszFileName, pbyImageBuffer, uImageFormat, iWidth, iHeight, byFileType, byQuality):
	err_code = _sdk.CameraSaveImageEx(hCamera, _str_to_string_buffer(lpszFileName), c_void_p(pbyImageBuffer), uImageFormat, iWidth, iHeight, byFileType, byQuality)
	SetLastError(err_code)
	return err_code

def CameraGetImageResolution(hCamera):
	psCurVideoSize = tSdkImageResolution()
	err_code = _sdk.CameraGetImageResolution(hCamera, byref(psCurVideoSize) )
	SetLastError(err_code)
	return psCurVideoSize

def CameraSetImageResolution(hCamera, pImageResolution):
	err_code = _sdk.CameraSetImageResolution(hCamera, byref(pImageResolution) )
	SetLastError(err_code)
	return err_code

def CameraSetImageResolutionEx(hCamera, iIndex, Mode, ModeSize, x, y, width, height, ZoomWidth, ZoomHeight):
	err_code = _sdk.CameraSetImageResolutionEx(hCamera, iIndex, Mode, ModeSize, x, y, width, height, ZoomWidth, ZoomHeight)
	SetLastError(err_code)
	return err_code

def CameraGetMediaType(hCamera):
	piMediaType = c_int()
	err_code = _sdk.CameraGetMediaType(hCamera, byref(piMediaType) )
	SetLastError(err_code)
	return piMediaType.value

def CameraSetMediaType(hCamera, iMediaType):
	err_code = _sdk.CameraSetMediaType(hCamera, iMediaType)
	SetLastError(err_code)
	return err_code

def CameraSetAeState(hCamera, bAeState):
	err_code = _sdk.CameraSetAeState(hCamera, bAeState)
	SetLastError(err_code)
	return err_code

def CameraGetAeState(hCamera):
	pAeState = c_int()
	err_code = _sdk.CameraGetAeState(hCamera, byref(pAeState) )
	SetLastError(err_code)
	return pAeState.value

def CameraSetSharpness(hCamera, iSharpness):
	err_code = _sdk.CameraSetSharpness(hCamera, iSharpness)
	SetLastError(err_code)
	return err_code

def CameraGetSharpness(hCamera):
	piSharpness = c_int()
	err_code = _sdk.CameraGetSharpness(hCamera, byref(piSharpness) )
	SetLastError(err_code)
	return piSharpness.value

def CameraSetLutMode(hCamera, emLutMode):
	err_code = _sdk.CameraSetLutMode(hCamera, emLutMode)
	SetLastError(err_code)
	return err_code

def CameraGetLutMode(hCamera):
	pemLutMode = c_int()
	err_code = _sdk.CameraGetLutMode(hCamera, byref(pemLutMode) )
	SetLastError(err_code)
	return pemLutMode.value

def CameraSelectLutPreset(hCamera, iSel):
	err_code = _sdk.CameraSelectLutPreset(hCamera, iSel)
	SetLastError(err_code)
	return err_code

def CameraGetLutPresetSel(hCamera):
	piSel = c_int()
	err_code = _sdk.CameraGetLutPresetSel(hCamera, byref(piSel) )
	SetLastError(err_code)
	return piSel.value

def CameraSetCustomLut(hCamera, iChannel, pLut):
	pLutNative = (c_ushort * 4096)(*pLut)
	err_code = _sdk.CameraSetCustomLut(hCamera, iChannel, pLutNative)
	SetLastError(err_code)
	return err_code

def CameraGetCustomLut(hCamera, iChannel):
	pLutNative = (c_ushort * 4096)()
	err_code = _sdk.CameraGetCustomLut(hCamera, iChannel, pLutNative)
	SetLastError(err_code)
	return pLutNative[:]

def CameraGetCurrentLut(hCamera, iChannel):
	pLutNative = (c_ushort * 4096)()
	err_code = _sdk.CameraGetCurrentLut(hCamera, iChannel, pLutNative)
	SetLastError(err_code)
	return pLutNative[:]

def CameraSetWbMode(hCamera, bAuto):
	err_code = _sdk.CameraSetWbMode(hCamera, bAuto)
	SetLastError(err_code)
	return err_code

def CameraGetWbMode(hCamera):
	pbAuto = c_int()
	err_code = _sdk.CameraGetWbMode(hCamera, byref(pbAuto) )
	SetLastError(err_code)
	return pbAuto.value

def CameraSetPresetClrTemp(hCamera, iSel):
	err_code = _sdk.CameraSetPresetClrTemp(hCamera, iSel)
	SetLastError(err_code)
	return err_code

def CameraGetPresetClrTemp(hCamera):
	piSel = c_int()
	err_code = _sdk.CameraGetPresetClrTemp(hCamera, byref(piSel) )
	SetLastError(err_code)
	return piSel.value

def CameraSetUserClrTempGain(hCamera, iRgain, iGgain, iBgain):
	err_code = _sdk.CameraSetUserClrTempGain(hCamera, iRgain, iGgain, iBgain)
	SetLastError(err_code)
	return err_code

def CameraGetUserClrTempGain(hCamera):
	piRgain = c_int()
	piGgain = c_int()
	piBgain = c_int()
	err_code = _sdk.CameraGetUserClrTempGain(hCamera, byref(piRgain), byref(piGgain), byref(piBgain) )
	SetLastError(err_code)
	return (piRgain.value, piGgain.value, piBgain.value)

def CameraSetUserClrTempMatrix(hCamera, pMatrix):
	pMatrixNative = (c_float * 9)(*pMatrix)
	err_code = _sdk.CameraSetUserClrTempMatrix(hCamera, pMatrixNative)
	SetLastError(err_code)
	return err_code

def CameraGetUserClrTempMatrix(hCamera):
	pMatrixNative = (c_float * 9)()
	err_code = _sdk.CameraGetUserClrTempMatrix(hCamera, pMatrixNative)
	SetLastError(err_code)
	return pMatrixNative[:]

def CameraSetClrTempMode(hCamera, iMode):
	err_code = _sdk.CameraSetClrTempMode(hCamera, iMode)
	SetLastError(err_code)
	return err_code

def CameraGetClrTempMode(hCamera):
	piMode = c_int()
	err_code = _sdk.CameraGetClrTempMode(hCamera, byref(piMode) )
	SetLastError(err_code)
	return piMode.value

def CameraSetOnceWB(hCamera):
	err_code = _sdk.CameraSetOnceWB(hCamera)
	SetLastError(err_code)
	return err_code

def CameraSetOnceBB(hCamera):
	err_code = _sdk.CameraSetOnceBB(hCamera)
	SetLastError(err_code)
	return err_code

def CameraSetAeTarget(hCamera, iAeTarget):
	err_code = _sdk.CameraSetAeTarget(hCamera, iAeTarget)
	SetLastError(err_code)
	return err_code

def CameraGetAeTarget(hCamera):
	piAeTarget = c_int()
	err_code = _sdk.CameraGetAeTarget(hCamera, byref(piAeTarget) )
	SetLastError(err_code)
	return piAeTarget.value

def CameraSetAeExposureRange(hCamera, fMinExposureTime, fMaxExposureTime):
	err_code = _sdk.CameraSetAeExposureRange(hCamera, c_double(fMinExposureTime), c_double(fMaxExposureTime) )
	SetLastError(err_code)
	return err_code

def CameraGetAeExposureRange(hCamera):
	fMinExposureTime = c_double()
	fMaxExposureTime = c_double()
	err_code = _sdk.CameraGetAeExposureRange(hCamera, byref(fMinExposureTime), byref(fMaxExposureTime) )
	SetLastError(err_code)
	return (fMinExposureTime.value, fMaxExposureTime.value)

def CameraSetAeAnalogGainRange(hCamera, iMinAnalogGain, iMaxAnalogGain):
	err_code = _sdk.CameraSetAeAnalogGainRange(hCamera, iMinAnalogGain, iMaxAnalogGain)
	SetLastError(err_code)
	return err_code

def CameraGetAeAnalogGainRange(hCamera):
	iMinAnalogGain = c_int()
	iMaxAnalogGain = c_int()
	err_code = _sdk.CameraGetAeAnalogGainRange(hCamera, byref(iMinAnalogGain), byref(iMaxAnalogGain) )
	SetLastError(err_code)
	return (iMinAnalogGain.value, iMaxAnalogGain.value)

def CameraSetAeThreshold(hCamera, iThreshold):
	err_code = _sdk.CameraSetAeThreshold(hCamera, iThreshold)
	SetLastError(err_code)
	return err_code

def CameraGetAeThreshold(hCamera):
	iThreshold = c_int()
	err_code = _sdk.CameraGetAeThreshold(hCamera, byref(iThreshold))
	SetLastError(err_code)
	return iThreshold.value

def CameraSetExposureTime(hCamera, fExposureTime):
	err_code = _sdk.CameraSetExposureTime(hCamera, c_double(fExposureTime) )
	SetLastError(err_code)
	return err_code

def CameraGetExposureLineTime(hCamera):
	pfLineTime = c_double()
	err_code = _sdk.CameraGetExposureLineTime(hCamera, byref(pfLineTime))
	SetLastError(err_code)
	return pfLineTime.value

def CameraGetExposureTime(hCamera):
	pfExposureTime = c_double()
	err_code = _sdk.CameraGetExposureTime(hCamera, byref(pfExposureTime))
	SetLastError(err_code)
	return pfExposureTime.value

def CameraGetExposureTimeRange(hCamera):
	pfMin = c_double()
	pfMax = c_double()
	pfStep = c_double()
	err_code = _sdk.CameraGetExposureTimeRange(hCamera, byref(pfMin), byref(pfMax), byref(pfStep))
	SetLastError(err_code)
	return (pfMin.value, pfMax.value, pfStep.value)

def CameraSetAnalogGain(hCamera, iAnalogGain):
	err_code = _sdk.CameraSetAnalogGain(hCamera, iAnalogGain)
	SetLastError(err_code)
	return err_code

def CameraGetAnalogGain(hCamera):
	piAnalogGain = c_int()
	err_code = _sdk.CameraGetAnalogGain(hCamera, byref(piAnalogGain))
	SetLastError(err_code)
	return piAnalogGain.value

def CameraSetGain(hCamera, iRGain, iGGain, iBGain):
	err_code = _sdk.CameraSetGain(hCamera, iRGain, iGGain, iBGain)
	SetLastError(err_code)
	return err_code

def CameraGetGain(hCamera):
	piRGain = c_int()
	piGGain = c_int()
	piBGain = c_int()
	err_code = _sdk.CameraGetGain(hCamera, byref(piRGain), byref(piGGain), byref(piBGain))
	SetLastError(err_code)
	return (piRGain.value, piGGain.value, piBGain.value)

def CameraSetGamma(hCamera, iGamma):
	err_code = _sdk.CameraSetGamma(hCamera, iGamma)
	SetLastError(err_code)
	return err_code

def CameraGetGamma(hCamera):
	piGamma = c_int()
	err_code = _sdk.CameraGetGamma(hCamera, byref(piGamma))
	SetLastError(err_code)
	return piGamma.value

def CameraSetContrast(hCamera, iContrast):
	err_code = _sdk.CameraSetContrast(hCamera, iContrast)
	SetLastError(err_code)
	return err_code

def CameraGetContrast(hCamera):
	piContrast = c_int()
	err_code = _sdk.CameraGetContrast(hCamera, byref(piContrast))
	SetLastError(err_code)
	return piContrast.value

def CameraSetSaturation(hCamera, iSaturation):
	err_code = _sdk.CameraSetSaturation(hCamera, iSaturation)
	SetLastError(err_code)
	return err_code

def CameraGetSaturation(hCamera):
	piSaturation = c_int()
	err_code = _sdk.CameraGetSaturation(hCamera, byref(piSaturation))
	SetLastError(err_code)
	return piSaturation.value

def CameraSetMonochrome(hCamera, bEnable):
	err_code = _sdk.CameraSetMonochrome(hCamera, bEnable)
	SetLastError(err_code)
	return err_code

def CameraGetMonochrome(hCamera):
	pbEnable = c_int()
	err_code = _sdk.CameraGetMonochrome(hCamera, byref(pbEnable))
	SetLastError(err_code)
	return pbEnable.value

def CameraSetInverse(hCamera, bEnable):
	err_code = _sdk.CameraSetInverse(hCamera, bEnable)
	SetLastError(err_code)
	return err_code

def CameraGetInverse(hCamera):
	pbEnable = c_int()
	err_code = _sdk.CameraGetInverse(hCamera, byref(pbEnable))
	SetLastError(err_code)
	return pbEnable.value

def CameraSetAntiFlick(hCamera, bEnable):
	err_code = _sdk.CameraSetAntiFlick(hCamera, bEnable)
	SetLastError(err_code)
	return err_code

def CameraGetAntiFlick(hCamera):
	pbEnable = c_int()
	err_code = _sdk.CameraGetAntiFlick(hCamera, byref(pbEnable))
	SetLastError(err_code)
	return pbEnable.value

def CameraGetLightFrequency(hCamera):
	piFrequencySel = c_int()
	err_code = _sdk.CameraGetLightFrequency(hCamera, byref(piFrequencySel))
	SetLastError(err_code)
	return piFrequencySel.value

def CameraSetLightFrequency(hCamera, iFrequencySel):
	err_code = _sdk.CameraSetLightFrequency(hCamera, iFrequencySel)
	SetLastError(err_code)
	return err_code

def CameraSetFrameSpeed(hCamera, iFrameSpeed):
	err_code = _sdk.CameraSetFrameSpeed(hCamera, iFrameSpeed)
	SetLastError(err_code)
	return err_code

def CameraGetFrameSpeed(hCamera):
	piFrameSpeed = c_int()
	err_code = _sdk.CameraGetFrameSpeed(hCamera, byref(piFrameSpeed))
	SetLastError(err_code)
	return piFrameSpeed.value

def CameraSetParameterMode(hCamera, iMode):
	err_code = _sdk.CameraSetParameterMode(hCamera, iMode)
	SetLastError(err_code)
	return err_code

def CameraGetParameterMode(hCamera):
	piTarget = c_int()
	err_code = _sdk.CameraGetParameterMode(hCamera, byref(piTarget))
	SetLastError(err_code)
	return piTarget.value

def CameraSetParameterMask(hCamera, uMask):
	err_code = _sdk.CameraSetParameterMask(hCamera, uMask)
	SetLastError(err_code)
	return err_code

def CameraSaveParameter(hCamera, iTeam):
	err_code = _sdk.CameraSaveParameter(hCamera, iTeam)
	SetLastError(err_code)
	return err_code

def CameraSaveParameterToFile(hCamera, sFileName):
	err_code = _sdk.CameraSaveParameterToFile(hCamera, _str_to_string_buffer(sFileName))
	SetLastError(err_code)
	return err_code

def CameraReadParameterFromFile(hCamera, sFileName):
	err_code = _sdk.CameraReadParameterFromFile(hCamera, _str_to_string_buffer(sFileName))
	SetLastError(err_code)
	return err_code

def CameraLoadParameter(hCamera, iTeam):
	err_code = _sdk.CameraLoadParameter(hCamera, iTeam)
	SetLastError(err_code)
	return err_code

def CameraGetCurrentParameterGroup(hCamera):
	piTeam = c_int()
	err_code = _sdk.CameraGetCurrentParameterGroup(hCamera, byref(piTeam))
	SetLastError(err_code)
	return piTeam.value

def CameraSetTransPackLen(hCamera, iPackSel):
	err_code = _sdk.CameraSetTransPackLen(hCamera, iPackSel)
	SetLastError(err_code)
	return err_code

def CameraGetTransPackLen(hCamera):
	piPackSel = c_int()
	err_code = _sdk.CameraGetTransPackLen(hCamera, byref(piPackSel))
	SetLastError(err_code)
	return piPackSel.value

def CameraIsAeWinVisible(hCamera):
	pbIsVisible = c_int()
	err_code = _sdk.CameraIsAeWinVisible(hCamera, byref(pbIsVisible))
	SetLastError(err_code)
	return pbIsVisible.value

def CameraSetAeWinVisible(hCamera, bIsVisible):
	err_code = _sdk.CameraSetAeWinVisible(hCamera, bIsVisible)
	SetLastError(err_code)
	return err_code

def CameraGetAeWindow(hCamera):
	piHOff = c_int()
	piVOff = c_int()
	piWidth = c_int()
	piHeight = c_int()
	err_code = _sdk.CameraGetAeWindow(hCamera, byref(piHOff), byref(piVOff), byref(piWidth), byref(piHeight))
	SetLastError(err_code)
	return (piHOff.value, piVOff.value, piWidth.value, piHeight.value)

def CameraSetAeWindow(hCamera, iHOff, iVOff, iWidth, iHeight):
	err_code = _sdk.CameraSetAeWindow(hCamera, iHOff, iVOff, iWidth, iHeight)
	SetLastError(err_code)
	return err_code

def CameraSetMirror(hCamera, iDir, bEnable):
	err_code = _sdk.CameraSetMirror(hCamera, iDir, bEnable)
	SetLastError(err_code)
	return err_code

def CameraGetMirror(hCamera, iDir):
	pbEnable = c_int()
	err_code = _sdk.CameraGetMirror(hCamera, iDir, byref(pbEnable))
	SetLastError(err_code)
	return pbEnable.value

def CameraSetRotate(hCamera, iRot):
	err_code = _sdk.CameraSetRotate(hCamera, iRot)
	SetLastError(err_code)
	return err_code

def CameraGetRotate(hCamera):
	iRot = c_int()
	err_code = _sdk.CameraGetRotate(hCamera, byref(iRot))
	SetLastError(err_code)
	return iRot.value

def CameraGetWbWindow(hCamera):
	PiHOff = c_int()
	PiVOff = c_int()
	PiWidth = c_int()
	PiHeight = c_int()
	err_code = _sdk.CameraGetWbWindow(hCamera, byref(PiHOff), byref(PiVOff), byref(PiWidth), byref(PiHeight))
	SetLastError(err_code)
	return (PiHOff.value, PiVOff.value, PiWidth.value, PiHeight.value)

def CameraSetWbWindow(hCamera, iHOff, iVOff, iWidth, iHeight):
	err_code = _sdk.CameraSetWbWindow(hCamera, iHOff, iVOff, iWidth, iHeight)
	SetLastError(err_code)
	return err_code

def CameraIsWbWinVisible(hCamera):
	pbShow = c_int()
	err_code = _sdk.CameraIsWbWinVisible(hCamera, byref(pbShow))
	SetLastError(err_code)
	return pbShow.value

def CameraSetWbWinVisible(hCamera, bShow):
	err_code = _sdk.CameraSetWbWinVisible(hCamera, bShow)
	SetLastError(err_code)
	return err_code

def CameraImageOverlay(hCamera, pRgbBuffer, pFrInfo):
	err_code = _sdk.CameraImageOverlay(hCamera, c_void_p(pRgbBuffer), byref(pFrInfo))
	SetLastError(err_code)
	return err_code

def CameraSetCrossLine(hCamera, iLine, x, y, uColor, bVisible):
	err_code = _sdk.CameraSetCrossLine(hCamera, iLine, x, y, uColor, bVisible)
	SetLastError(err_code)
	return err_code

def CameraGetCrossLine(hCamera, iLine):
	px = c_int()
	py = c_int()
	pcolor = c_uint()
	pbVisible = c_int()
	err_code = _sdk.CameraGetCrossLine(hCamera, iLine, byref(px), byref(py), byref(pcolor), byref(pbVisible))
	SetLastError(err_code)
	return (px.value, py.value, pcolor.value, pbVisible.value)

def CameraGetCapability(hCamera):
	pCameraInfo = tSdkCameraCapbility()
	err_code = _sdk.CameraGetCapability(hCamera, byref(pCameraInfo))
	SetLastError(err_code)
	return pCameraInfo

def CameraWriteSN(hCamera, pbySN, iLevel):
	err_code = _sdk.CameraWriteSN(hCamera, _str_to_string_buffer(pbySN), iLevel)
	SetLastError(err_code)
	return err_code

def CameraReadSN(hCamera, iLevel):
	pbySN = create_string_buffer(64)
	err_code = _sdk.CameraReadSN(hCamera, pbySN, iLevel)
	SetLastError(err_code)
	return _string_buffer_to_str(pbySN)

def CameraSetTriggerDelayTime(hCamera, uDelayTimeUs):
	err_code = _sdk.CameraSetTriggerDelayTime(hCamera, uDelayTimeUs)
	SetLastError(err_code)
	return err_code

def CameraGetTriggerDelayTime(hCamera):
	puDelayTimeUs = c_uint()
	err_code = _sdk.CameraGetTriggerDelayTime(hCamera, byref(puDelayTimeUs))
	SetLastError(err_code)
	return puDelayTimeUs.value

def CameraSetTriggerCount(hCamera, iCount):
	err_code = _sdk.CameraSetTriggerCount(hCamera, iCount)
	SetLastError(err_code)
	return err_code

def CameraGetTriggerCount(hCamera):
	piCount = c_int()
	err_code = _sdk.CameraGetTriggerCount(hCamera, byref(piCount))
	SetLastError(err_code)
	return piCount.value

def CameraSoftTrigger(hCamera):
	err_code = _sdk.CameraSoftTrigger(hCamera)
	SetLastError(err_code)
	return err_code

def CameraSetTriggerMode(hCamera, iModeSel):
	err_code = _sdk.CameraSetTriggerMode(hCamera, iModeSel)
	SetLastError(err_code)
	return err_code

def CameraGetTriggerMode(hCamera):
	piModeSel = c_int()
	err_code = _sdk.CameraGetTriggerMode(hCamera, byref(piModeSel))
	SetLastError(err_code)
	return piModeSel.value

def CameraSetStrobeMode(hCamera, iMode):
	err_code = _sdk.CameraSetStrobeMode(hCamera, iMode)
	SetLastError(err_code)
	return err_code

def CameraGetStrobeMode(hCamera):
	piMode = c_int()
	err_code = _sdk.CameraGetStrobeMode(hCamera, byref(piMode))
	SetLastError(err_code)
	return piMode.value

def CameraSetStrobeDelayTime(hCamera, uDelayTimeUs):
	err_code = _sdk.CameraSetStrobeDelayTime(hCamera, uDelayTimeUs)
	SetLastError(err_code)
	return err_code

def CameraGetStrobeDelayTime(hCamera):
	upDelayTimeUs = c_uint()
	err_code = _sdk.CameraGetStrobeDelayTime(hCamera, byref(upDelayTimeUs))
	SetLastError(err_code)
	return upDelayTimeUs.value

def CameraSetStrobePulseWidth(hCamera, uTimeUs):
	err_code = _sdk.CameraSetStrobePulseWidth(hCamera, uTimeUs)
	SetLastError(err_code)
	return err_code

def CameraGetStrobePulseWidth(hCamera):
	upTimeUs = c_uint()
	err_code = _sdk.CameraGetStrobePulseWidth(hCamera, byref(upTimeUs))
	SetLastError(err_code)
	return upTimeUs.value

def CameraSetStrobePolarity(hCamera, uPolarity):
	err_code = _sdk.CameraSetStrobePolarity(hCamera, uPolarity)
	SetLastError(err_code)
	return err_code

def CameraGetStrobePolarity(hCamera):
	upPolarity = c_uint()
	err_code = _sdk.CameraGetStrobePolarity(hCamera, byref(upPolarity))
	SetLastError(err_code)
	return upPolarity.value

def CameraSetExtTrigSignalType(hCamera, iType):
	err_code = _sdk.CameraSetExtTrigSignalType(hCamera, iType)
	SetLastError(err_code)
	return err_code

def CameraGetExtTrigSignalType(hCamera):
	ipType = c_int()
	err_code = _sdk.CameraGetExtTrigSignalType(hCamera, byref(ipType))
	SetLastError(err_code)
	return ipType.value

def CameraSetExtTrigShutterType(hCamera, iType):
	err_code = _sdk.CameraSetExtTrigShutterType(hCamera, iType)
	SetLastError(err_code)
	return err_code

def CameraGetExtTrigShutterType(hCamera):
	ipType = c_int()
	err_code = _sdk.CameraGetExtTrigShutterType(hCamera, byref(ipType))
	SetLastError(err_code)
	return ipType.value

def CameraSetExtTrigDelayTime(hCamera, uDelayTimeUs):
	err_code = _sdk.CameraSetExtTrigDelayTime(hCamera, uDelayTimeUs)
	SetLastError(err_code)
	return err_code

def CameraGetExtTrigDelayTime(hCamera):
	upDelayTimeUs = c_uint()
	err_code = _sdk.CameraGetExtTrigDelayTime(hCamera, byref(upDelayTimeUs))
	SetLastError(err_code)
	return upDelayTimeUs.value

def CameraSetExtTrigJitterTime(hCamera, uTimeUs):
	err_code = _sdk.CameraSetExtTrigJitterTime(hCamera, uTimeUs)
	SetLastError(err_code)
	return err_code

def CameraGetExtTrigJitterTime(hCamera):
	upTimeUs = c_uint()
	err_code = _sdk.CameraGetExtTrigJitterTime(hCamera, byref(upTimeUs))
	SetLastError(err_code)
	return upTimeUs.value

def CameraGetExtTrigCapability(hCamera):
	puCapabilityMask = c_uint()
	err_code = _sdk.CameraGetExtTrigCapability(hCamera, byref(puCapabilityMask))
	SetLastError(err_code)
	return puCapabilityMask.value

def CameraPauseLevelTrigger(hCamera):
	err_code = _sdk.CameraPauseLevelTrigger(hCamera)
	SetLastError(err_code)
	return err_code

def CameraGetResolutionForSnap(hCamera):
	pImageResolution = tSdkImageResolution()
	err_code = _sdk.CameraGetResolutionForSnap(hCamera, byref(pImageResolution))
	SetLastError(err_code)
	return pImageResolution

def CameraSetResolutionForSnap(hCamera, pImageResolution):
	err_code = _sdk.CameraSetResolutionForSnap(hCamera, byref(pImageResolution))
	SetLastError(err_code)
	return err_code

def CameraCustomizeResolution(hCamera):
	pImageCustom = tSdkImageResolution()
	err_code = _sdk.CameraCustomizeResolution(hCamera, byref(pImageCustom))
	SetLastError(err_code)
	return pImageCustom

def CameraCustomizeReferWin(hCamera, iWinType, hParent):
	piHOff = c_int()
	piVOff = c_int()
	piWidth = c_int()
	piHeight = c_int()
	err_code = _sdk.CameraCustomizeReferWin(hCamera, iWinType, hParent, byref(piHOff), byref(piVOff), byref(piWidth), byref(piHeight))
	SetLastError(err_code)
	return (piHOff.value, piVOff.value, piWidth.value, piHeight.value)

def CameraShowSettingPage(hCamera, bShow):
	err_code = _sdk.CameraShowSettingPage(hCamera, bShow)
	SetLastError(err_code)
	return err_code

def CameraCreateSettingPage(hCamera, hParent, pWinText, pCallbackFunc = None, pCallbackCtx = 0, uReserved = 0):
	err_code = _sdk.CameraCreateSettingPage(hCamera, hParent, _str_to_string_buffer(pWinText), pCallbackFunc, c_void_p(pCallbackCtx), uReserved)
	SetLastError(err_code)
	return err_code

def CameraCreateSettingPageEx(hCamera):
	err_code = _sdk.CameraCreateSettingPageEx(hCamera)
	SetLastError(err_code)
	return err_code

def CameraSetActiveSettingSubPage(hCamera, index):
	err_code = _sdk.CameraSetActiveSettingSubPage(hCamera, index)
	SetLastError(err_code)
	return err_code

def CameraSetSettingPageParent(hCamera, hParentWnd, Flags):
	err_code = _sdk.CameraSetSettingPageParent(hCamera, hParentWnd, Flags)
	SetLastError(err_code)
	return err_code

def CameraGetSettingPageHWnd(hCamera):
	hWnd = c_void_p()
	err_code = _sdk.CameraGetSettingPageHWnd(hCamera, byref(hWnd))
	SetLastError(err_code)
	return hWnd.value

def CameraSpecialControl(hCamera, dwCtrlCode, dwParam, lpData):
	err_code = _sdk.CameraSpecialControl(hCamera, dwCtrlCode, dwParam, c_void_p(lpData) )
	SetLastError(err_code)
	return err_code

def CameraGetFrameStatistic(hCamera):
	psFrameStatistic = tSdkFrameStatistic()
	err_code = _sdk.CameraGetFrameStatistic(hCamera, byref(psFrameStatistic))
	SetLastError(err_code)
	return psFrameStatistic

def CameraSetNoiseFilter(hCamera, bEnable):
	err_code = _sdk.CameraSetNoiseFilter(hCamera, bEnable)
	SetLastError(err_code)
	return err_code

def CameraGetNoiseFilterState(hCamera):
	pEnable = c_int()
	err_code = _sdk.CameraGetNoiseFilterState(hCamera, byref(pEnable))
	SetLastError(err_code)
	return pEnable.value

def CameraRstTimeStamp(hCamera):
	err_code = _sdk.CameraRstTimeStamp(hCamera)
	SetLastError(err_code)
	return err_code

def CameraSaveUserData(hCamera, uStartAddr, pbData):
	err_code = _sdk.CameraSaveUserData(hCamera, uStartAddr, pbData, len(pbData))
	SetLastError(err_code)
	return err_code

def CameraLoadUserData(hCamera, uStartAddr, ilen):
	pbData = create_string_buffer(ilen)
	err_code = _sdk.CameraLoadUserData(hCamera, uStartAddr, pbData, ilen)
	SetLastError(err_code)
	return pbData[:]

def CameraGetFriendlyName(hCamera):
	pName = create_string_buffer(64)
	err_code = _sdk.CameraGetFriendlyName(hCamera, pName)
	SetLastError(err_code)
	return _string_buffer_to_str(pName)

def CameraSetFriendlyName(hCamera, pName):
	pNameBuf = _str_to_string_buffer(pName)
	resize(pNameBuf, 64)
	err_code = _sdk.CameraSetFriendlyName(hCamera, pNameBuf)
	SetLastError(err_code)
	return err_code

def CameraSdkGetVersionString():
	pVersionString = create_string_buffer(64)
	err_code = _sdk.CameraSdkGetVersionString(pVersionString)
	SetLastError(err_code)
	return _string_buffer_to_str(pVersionString)

def CameraCheckFwUpdate(hCamera):
	pNeedUpdate = c_int()
	err_code = _sdk.CameraCheckFwUpdate(hCamera, byref(pNeedUpdate))
	SetLastError(err_code)
	return pNeedUpdate.value

def CameraGetFirmwareVersion(hCamera):
	pVersion = create_string_buffer(64)
	err_code = _sdk.CameraGetFirmwareVersion(hCamera, pVersion)
	SetLastError(err_code)
	return _string_buffer_to_str(pVersion)

def CameraGetEnumInfo(hCamera):
	pCameraInfo = tSdkCameraDevInfo()
	err_code = _sdk.CameraGetEnumInfo(hCamera, byref(pCameraInfo))
	SetLastError(err_code)
	return pCameraInfo

def CameraGetInerfaceVersion(hCamera):
	pVersion = create_string_buffer(64)
	err_code = _sdk.CameraGetInerfaceVersion(hCamera, pVersion)
	SetLastError(err_code)
	return _string_buffer_to_str(pVersion)

def CameraSetIOState(hCamera, iOutputIOIndex, uState):
	err_code = _sdk.CameraSetIOState(hCamera, iOutputIOIndex, uState)
	SetLastError(err_code)
	return err_code

def CameraSetIOStateEx(hCamera, iOutputIOIndex, uState):
	err_code = _sdk.CameraSetIOStateEx(hCamera, iOutputIOIndex, uState)
	SetLastError(err_code)
	return err_code

def CameraGetOutPutIOState(hCamera, iOutputIOIndex):
	puState = c_int()
	err_code = _sdk.CameraGetOutPutIOState(hCamera, iOutputIOIndex, byref(puState))
	SetLastError(err_code)
	return puState.value

def CameraGetOutPutIOStateEx(hCamera, iOutputIOIndex):
	puState = c_int()
	err_code = _sdk.CameraGetOutPutIOStateEx(hCamera, iOutputIOIndex, byref(puState))
	SetLastError(err_code)
	return puState.value

def CameraGetIOState(hCamera, iInputIOIndex):
	puState = c_int()
	err_code = _sdk.CameraGetIOState(hCamera, iInputIOIndex, byref(puState))
	SetLastError(err_code)
	return puState.value

def CameraGetIOStateEx(hCamera, iInputIOIndex):
	puState = c_int()
	err_code = _sdk.CameraGetIOStateEx(hCamera, iInputIOIndex, byref(puState))
	SetLastError(err_code)
	return puState.value

def CameraSetInPutIOMode(hCamera, iInputIOIndex, iMode):
	err_code = _sdk.CameraSetInPutIOMode(hCamera, iInputIOIndex, iMode)
	SetLastError(err_code)
	return err_code

def CameraSetOutPutIOMode(hCamera, iOutputIOIndex, iMode):
	err_code = _sdk.CameraSetOutPutIOMode(hCamera, iOutputIOIndex, iMode)
	SetLastError(err_code)
	return err_code

def CameraSetOutPutPWM(hCamera, iOutputIOIndex, iCycle, uDuty):
	err_code = _sdk.CameraSetOutPutPWM(hCamera, iOutputIOIndex, iCycle, uDuty)
	SetLastError(err_code)
	return err_code

def CameraSetAeAlgorithm(hCamera, iIspProcessor, iAeAlgorithmSel):
	err_code = _sdk.CameraSetAeAlgorithm(hCamera, iIspProcessor, iAeAlgorithmSel)
	SetLastError(err_code)
	return err_code

def CameraGetAeAlgorithm(hCamera, iIspProcessor):
	piAlgorithmSel = c_int()
	err_code = _sdk.CameraGetAeAlgorithm(hCamera, iIspProcessor, byref(piAlgorithmSel))
	SetLastError(err_code)
	return piAlgorithmSel.value

def CameraSetBayerDecAlgorithm(hCamera, iIspProcessor, iAlgorithmSel):
	err_code = _sdk.CameraSetBayerDecAlgorithm(hCamera, iIspProcessor, iAlgorithmSel)
	SetLastError(err_code)
	return err_code

def CameraGetBayerDecAlgorithm(hCamera, iIspProcessor):
	piAlgorithmSel = c_int()
	err_code = _sdk.CameraGetBayerDecAlgorithm(hCamera, iIspProcessor, byref(piAlgorithmSel))
	SetLastError(err_code)
	return piAlgorithmSel.value

def CameraSetIspProcessor(hCamera, iIspProcessor):
	err_code = _sdk.CameraSetIspProcessor(hCamera, iIspProcessor)
	SetLastError(err_code)
	return err_code

def CameraGetIspProcessor(hCamera):
	piIspProcessor = c_int()
	err_code = _sdk.CameraGetIspProcessor(hCamera, byref(piIspProcessor))
	SetLastError(err_code)
	return piIspProcessor.value

def CameraSetBlackLevel(hCamera, iBlackLevel):
	err_code = _sdk.CameraSetBlackLevel(hCamera, iBlackLevel)
	SetLastError(err_code)
	return err_code

def CameraGetBlackLevel(hCamera):
	piBlackLevel = c_int()
	err_code = _sdk.CameraGetBlackLevel(hCamera, byref(piBlackLevel))
	SetLastError(err_code)
	return piBlackLevel.value

def CameraSetWhiteLevel(hCamera, iWhiteLevel):
	err_code = _sdk.CameraSetWhiteLevel(hCamera, iWhiteLevel)
	SetLastError(err_code)
	return err_code

def CameraGetWhiteLevel(hCamera):
	piWhiteLevel = c_int()
	err_code = _sdk.CameraGetWhiteLevel(hCamera, byref(piWhiteLevel))
	SetLastError(err_code)
	return piWhiteLevel.value

def CameraSetIspOutFormat(hCamera, uFormat):
	err_code = _sdk.CameraSetIspOutFormat(hCamera, uFormat)
	SetLastError(err_code)
	return err_code

def CameraGetIspOutFormat(hCamera):
	puFormat = c_int()
	err_code = _sdk.CameraGetIspOutFormat(hCamera, byref(puFormat))
	SetLastError(err_code)
	return puFormat.value

def CameraGetErrorString(iStatusCode):
	_sdk.CameraGetErrorString.restype = c_char_p
	msg = _sdk.CameraGetErrorString(iStatusCode)
	if msg:
		return _string_buffer_to_str(msg)
	else:
		return ''

def CameraGetImageBufferEx2(hCamera, pImageData, uOutFormat, wTimes):
	piWidth = c_int()
	piHeight = c_int()
	err_code = _sdk.CameraGetImageBufferEx2(hCamera, c_void_p(pImageData), uOutFormat, byref(piWidth), byref(piHeight), wTimes)
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return (piWidth.value, piHeight.value)

def CameraGetImageBufferEx3(hCamera, pImageData, uOutFormat, wTimes):
	piWidth = c_int()
	piHeight = c_int()
	puTimeStamp = c_int()
	err_code = _sdk.CameraGetImageBufferEx3(hCamera, c_void_p(pImageData), uOutFormat, byref(piWidth), byref(piHeight), byref(puTimeStamp), wTimes)
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return (piWidth.value, piHeight.value, puTimeStamp.value)

def CameraGetCapabilityEx2(hCamera):
	pMaxWidth = c_int()
	pMaxHeight = c_int()
	pbColorCamera = c_int()
	err_code = _sdk.CameraGetCapabilityEx2(hCamera, byref(pMaxWidth), byref(pMaxHeight), byref(pbColorCamera))
	SetLastError(err_code)
	return (pMaxWidth.value, pMaxHeight.value, pbColorCamera.value)

def CameraReConnect(hCamera):
	err_code = _sdk.CameraReConnect(hCamera)
	SetLastError(err_code)
	return err_code

def CameraConnectTest(hCamera):
	err_code = _sdk.CameraConnectTest(hCamera)
	SetLastError(err_code)
	return err_code

def CameraSetLedEnable(hCamera, index, enable):
	err_code = _sdk.CameraSetLedEnable(hCamera, index, enable)
	SetLastError(err_code)
	return err_code

def CameraGetLedEnable(hCamera, index):
	enable = c_int()
	err_code = _sdk.CameraGetLedEnable(hCamera, index, byref(enable))
	SetLastError(err_code)
	return enable.value

def CameraSetLedOnOff(hCamera, index, onoff):
	err_code = _sdk.CameraSetLedOnOff(hCamera, index, onoff)
	SetLastError(err_code)
	return err_code

def CameraGetLedOnOff(hCamera, index):
	onoff = c_int()
	err_code = _sdk.CameraGetLedOnOff(hCamera, index, byref(onoff))
	SetLastError(err_code)
	return onoff.value

def CameraSetLedDuration(hCamera, index, duration):
	err_code = _sdk.CameraSetLedDuration(hCamera, index, duration)
	SetLastError(err_code)
	return err_code

def CameraGetLedDuration(hCamera, index):
	duration = c_uint()
	err_code = _sdk.CameraGetLedDuration(hCamera, index, byref(duration))
	SetLastError(err_code)
	return duration.value

def CameraSetLedBrightness(hCamera, index, uBrightness):
	err_code = _sdk.CameraSetLedBrightness(hCamera, index, uBrightness)
	SetLastError(err_code)
	return err_code

def CameraGetLedBrightness(hCamera, index):
	uBrightness = c_uint()
	err_code = _sdk.CameraGetLedBrightness(hCamera, index, byref(uBrightness))
	SetLastError(err_code)
	return uBrightness.value

def CameraEnableTransferRoi(hCamera, uEnableMask):
	err_code = _sdk.CameraEnableTransferRoi(hCamera, uEnableMask)
	SetLastError(err_code)
	return err_code

def CameraSetTransferRoi(hCamera, index, X1, Y1, X2, Y2):
	err_code = _sdk.CameraSetTransferRoi(hCamera, index, X1, Y1, X2, Y2)
	SetLastError(err_code)
	return err_code

def CameraGetTransferRoi(hCamera, index):
	pX1 = c_uint()
	pY1 = c_uint()
	pX2 = c_uint()
	pY2 = c_uint()
	err_code = _sdk.CameraGetTransferRoi(hCamera, index, byref(pX1), byref(pY1), byref(pX2), byref(pY2))
	SetLastError(err_code)
	return (pX1.value, pY1.value, pX2.value, pY2.value)

def CameraAlignMalloc(size, align = 16):
	_sdk.CameraAlignMalloc.restype = c_void_p
	r = _sdk.CameraAlignMalloc(size, align)
	return r

def CameraAlignFree(membuffer):
	_sdk.CameraAlignFree(c_void_p(membuffer))

def CameraSetAutoConnect(hCamera, bEnable):
	err_code = _sdk.CameraSetAutoConnect(hCamera, bEnable)
	SetLastError(err_code)
	return err_code

def CameraGetAutoConnect(hCamera):
	pbEnable = c_int()
	err_code = _sdk.CameraGetAutoConnect(hCamera, byref(pbEnable))
	SetLastError(err_code)
	return pbEnable.value

def CameraGetReConnectCounts(hCamera):
	puCounts = c_int()
	err_code = _sdk.CameraGetReConnectCounts(hCamera, byref(puCounts))
	SetLastError(err_code)
	return puCounts.value

def CameraSetSingleGrabMode(hCamera, bEnable):
	err_code = _sdk.CameraSetSingleGrabMode(hCamera, bEnable)
	SetLastError(err_code)
	return err_code

def CameraGetSingleGrabMode(hCamera):
	pbEnable = c_int()
	err_code = _sdk.CameraGetSingleGrabMode(hCamera, byref(pbEnable))
	SetLastError(err_code)
	return pbEnable.value

def CameraRestartGrab(hCamera):
	err_code = _sdk.CameraRestartGrab(hCamera)
	SetLastError(err_code)
	return err_code

def CameraEvaluateImageDefinition(hCamera, iAlgorithSel, pbyIn, pFrInfo):
	DefinitionValue = c_double()
	err_code = _sdk.CameraEvaluateImageDefinition(hCamera, iAlgorithSel, c_void_p(pbyIn), byref(pFrInfo), byref(DefinitionValue))
	SetLastError(err_code)
	return DefinitionValue.value

def CameraDrawText(pRgbBuffer, pFrInfo, pFontFileName, FontWidth, FontHeight, pText, Left, Top, Width, Height, TextColor, uFlags):
	err_code = _sdk.CameraDrawText(c_void_p(pRgbBuffer), byref(pFrInfo), _str_to_string_buffer(pFontFileName), FontWidth, FontHeight, _str_to_string_buffer(pText), Left, Top, Width, Height, TextColor, uFlags)
	SetLastError(err_code)
	return err_code

def CameraGigeEnumerateDevice(ipList, MaxCount = 32):
	if type(ipList) in (list, tuple):
		ipList = map(lambda x: _str_to_string_buffer(x), ipList)
	else:
		ipList = (_str_to_string_buffer(ipList),)
	numIP = len(ipList)
	ppIpList = (c_void_p * numIP)(*map(lambda x: addressof(x), ipList))
	Nums = c_int(MaxCount)
	pCameraList = (tSdkCameraDevInfo * Nums.value)()
	err_code = _sdk.CameraGigeEnumerateDevice(ppIpList, numIP, pCameraList, byref(Nums))
	SetLastError(err_code)
	return pCameraList[0:Nums.value]

def CameraGigeGetIp(pCameraInfo):
	CamIp = create_string_buffer(32)
	CamMask = create_string_buffer(32)
	CamGateWay = create_string_buffer(32)
	EtIp = create_string_buffer(32)
	EtMask = create_string_buffer(32)
	EtGateWay = create_string_buffer(32)
	err_code = _sdk.CameraGigeGetIp(byref(pCameraInfo), CamIp, CamMask, CamGateWay, EtIp, EtMask, EtGateWay)
	SetLastError(err_code)
	return (_string_buffer_to_str(CamIp), _string_buffer_to_str(CamMask), _string_buffer_to_str(CamGateWay), 
		_string_buffer_to_str(EtIp), _string_buffer_to_str(EtMask), _string_buffer_to_str(EtGateWay) )

def CameraGigeSetIp(pCameraInfo, Ip, SubMask, GateWay, bPersistent):
	err_code = _sdk.CameraGigeSetIp(byref(pCameraInfo), 
		_str_to_string_buffer(Ip), _str_to_string_buffer(SubMask), _str_to_string_buffer(GateWay), bPersistent)
	SetLastError(err_code)
	return err_code

def CameraGigeGetMac(pCameraInfo):
	CamMac = create_string_buffer(32)
	EtMac = create_string_buffer(32)
	err_code = _sdk.CameraGigeGetMac(byref(pCameraInfo), CamMac, EtMac)
	SetLastError(err_code)
	return (_string_buffer_to_str(CamMac), _string_buffer_to_str(EtMac) )

def CameraEnableFastResponse(hCamera):
	err_code = _sdk.CameraEnableFastResponse(hCamera)
	SetLastError(err_code)
	return err_code

def CameraSetCorrectDeadPixel(hCamera, bEnable):
	err_code = _sdk.CameraSetCorrectDeadPixel(hCamera, bEnable)
	SetLastError(err_code)
	return err_code

def CameraGetCorrectDeadPixel(hCamera):
	pbEnable = c_int()
	err_code = _sdk.CameraGetCorrectDeadPixel(hCamera, byref(pbEnable))
	SetLastError(err_code)
	return pbEnable.value

def CameraFlatFieldingCorrectSetEnable(hCamera, bEnable):
	err_code = _sdk.CameraFlatFieldingCorrectSetEnable(hCamera, bEnable)
	SetLastError(err_code)
	return err_code

def CameraFlatFieldingCorrectGetEnable(hCamera):
	pbEnable = c_int()
	err_code = _sdk.CameraFlatFieldingCorrectGetEnable(hCamera, byref(pbEnable))
	SetLastError(err_code)
	return pbEnable.value

def CameraFlatFieldingCorrectSetParameter(hCamera, pDarkFieldingImage, pDarkFieldingFrInfo, pLightFieldingImage, pLightFieldingFrInfo):
	err_code = _sdk.CameraFlatFieldingCorrectSetParameter(hCamera, c_void_p(pDarkFieldingImage), byref(pDarkFieldingFrInfo), c_void_p(pLightFieldingImage), byref(pLightFieldingFrInfo))
	SetLastError(err_code)
	return err_code

def CameraFlatFieldingCorrectGetParameterState(hCamera):
	pbValid = c_int()
	pFilePath = create_string_buffer(1024)
	err_code = _sdk.CameraFlatFieldingCorrectGetParameterState(hCamera, byref(pbValid), pFilePath)
	SetLastError(err_code)
	return (pbValid.value, _string_buffer_to_str(pFilePath) )

def CameraFlatFieldingCorrectSaveParameterToFile(hCamera, pszFileName):
	err_code = _sdk.CameraFlatFieldingCorrectSaveParameterToFile(hCamera, _str_to_string_buffer(pszFileName))
	SetLastError(err_code)
	return err_code

def CameraFlatFieldingCorrectLoadParameterFromFile(hCamera, pszFileName):
	err_code = _sdk.CameraFlatFieldingCorrectLoadParameterFromFile(hCamera, _str_to_string_buffer(pszFileName))
	SetLastError(err_code)
	return err_code

def CameraCommonCall(hCamera, pszCall, uResultBufSize):
	pszResult = create_string_buffer(uResultBufSize) if uResultBufSize > 0 else None
	err_code = _sdk.CameraCommonCall(hCamera, _str_to_string_buffer(pszCall), pszResult, uResultBufSize)
	SetLastError(err_code)
	return _string_buffer_to_str(pszResult) if pszResult else ''

def CameraSetDenoise3DParams(hCamera, bEnable, nCount, Weights):
	assert(nCount >= 2 and nCount <= 8)
	if Weights:
		assert(len(Weights) == nCount)
		WeightsNative = (c_float * nCount)(*Weights)
	else:
		WeightsNative = None
	err_code = _sdk.CameraSetDenoise3DParams(hCamera, bEnable, nCount, WeightsNative)
	SetLastError(err_code)
	return err_code

def CameraGetDenoise3DParams(hCamera):
	bEnable = c_int()
	nCount = c_int()
	bUseWeight = c_int()
	Weights = (c_float * 8)()
	err_code = _sdk.CameraGetDenoise3DParams(hCamera, byref(bEnable), byref(nCount), byref(bUseWeight), Weights)
	SetLastError(err_code)
	bEnable, nCount, bUseWeight = bEnable.value, nCount.value, bUseWeight.value
	if bUseWeight:
		Weights = Weights[:nCount]
	else:
		Weights = None
	return (bEnable, nCount, bUseWeight, Weights)

def CameraManualDenoise3D(InFramesHead, InFramesData, nCount, Weights, OutFrameHead, OutFrameData):
	assert(nCount > 0)
	assert(len(InFramesData) == nCount)
	assert(Weights is None or len(Weights) == nCount)
	InFramesDataNative = (c_void_p * nCount)(*InFramesData)
	WeightsNative = (c_float * nCount)(*Weights) if Weights else None
	err_code = _sdk.CameraManualDenoise3D(byref(InFramesHead), InFramesDataNative, nCount, WeightsNative, byref(OutFrameHead), c_void_p(OutFrameData))
	SetLastError(err_code)
	return err_code

def CameraCustomizeDeadPixels(hCamera, hParent):
	err_code = _sdk.CameraCustomizeDeadPixels(hCamera, hParent)
	SetLastError(err_code)
	return err_code

def CameraReadDeadPixels(hCamera):
	pNumPixel = c_int()
	err_code = _sdk.CameraReadDeadPixels(hCamera, None, None, byref(pNumPixel))
	SetLastError(err_code)
	if pNumPixel.value < 1:
		return None
	UShortArray = c_ushort * pNumPixel.value
	pRows = UShortArray()
	pCols = UShortArray()
	err_code = _sdk.CameraReadDeadPixels(hCamera, pRows, pCols, byref(pNumPixel))
	SetLastError(err_code)
	if err_code == 0:
		pNumPixel = pNumPixel.value
	else:
		pNumPixel = 0
	return (pRows[:pNumPixel], pCols[:pNumPixel])

def CameraAddDeadPixels(hCamera, pRows, pCols, NumPixel):
	UShortArray = c_ushort * NumPixel
	pRowsNative = UShortArray(*pRows)
	pColsNative = UShortArray(*pCols)
	err_code = _sdk.CameraAddDeadPixels(hCamera, pRowsNative, pColsNative, NumPixel)
	SetLastError(err_code)
	return err_code

def CameraRemoveDeadPixels(hCamera, pRows, pCols, NumPixel):
	UShortArray = c_ushort * NumPixel
	pRowsNative = UShortArray(*pRows)
	pColsNative = UShortArray(*pCols)
	err_code = _sdk.CameraRemoveDeadPixels(hCamera, pRowsNative, pColsNative, NumPixel)
	SetLastError(err_code)
	return err_code

def CameraRemoveAllDeadPixels(hCamera):
	err_code = _sdk.CameraRemoveAllDeadPixels(hCamera)
	SetLastError(err_code)
	return err_code

def CameraSaveDeadPixels(hCamera):
	err_code = _sdk.CameraSaveDeadPixels(hCamera)
	SetLastError(err_code)
	return err_code

def CameraSaveDeadPixelsToFile(hCamera, sFileName):
	err_code = _sdk.CameraSaveDeadPixelsToFile(hCamera, _str_to_string_buffer(sFileName))
	SetLastError(err_code)
	return err_code

def CameraLoadDeadPixelsFromFile(hCamera, sFileName):
	err_code = _sdk.CameraLoadDeadPixelsFromFile(hCamera, _str_to_string_buffer(sFileName))
	SetLastError(err_code)
	return err_code

def CameraGetImageBufferPriority(hCamera, wTimes, Priority):
	pFrameInfo = tSdkFrameHead()
	pbyBuffer = c_void_p()
	err_code = _sdk.CameraGetImageBufferPriority(hCamera, byref(pFrameInfo), byref(pbyBuffer), wTimes, Priority)
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return (pbyBuffer.value, pFrameInfo)

def CameraGetImageBufferPriorityEx(hCamera, wTimes, Priority):
	_sdk.CameraGetImageBufferPriorityEx.restype = c_void_p
	piWidth = c_int()
	piHeight = c_int()
	pFrameBuffer = _sdk.CameraGetImageBufferPriorityEx(hCamera, byref(piWidth), byref(piHeight), wTimes, Priority)
	err_code = CAMERA_STATUS_SUCCESS if pFrameBuffer else CAMERA_STATUS_TIME_OUT
	SetLastError(err_code)
	if pFrameBuffer:
		return (pFrameBuffer, piWidth.value, piHeight.value)
	else:
		raise CameraException(err_code)

def CameraGetImageBufferPriorityEx2(hCamera, pImageData, uOutFormat, wTimes, Priority):
	piWidth = c_int()
	piHeight = c_int()
	err_code = _sdk.CameraGetImageBufferPriorityEx2(hCamera, c_void_p(pImageData), uOutFormat, byref(piWidth), byref(piHeight), wTimes, Priority)
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return (piWidth.value, piHeight.value)

def CameraGetImageBufferPriorityEx3(hCamera, pImageData, uOutFormat, wTimes, Priority):
	piWidth = c_int()
	piHeight = c_int()
	puTimeStamp = c_uint()
	err_code = _sdk.CameraGetImageBufferPriorityEx3(hCamera, c_void_p(pImageData), uOutFormat, byref(piWidth), byref(piHeight), byref(puTimeStamp), wTimes, Priority)
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return (piWidth.value, piHeight.value, puTimeStamp.value)

def CameraClearBuffer(hCamera):
	err_code = _sdk.CameraClearBuffer(hCamera)
	SetLastError(err_code)
	return err_code

def CameraSoftTriggerEx(hCamera, uFlags):
	err_code = _sdk.CameraSoftTriggerEx(hCamera, uFlags)
	SetLastError(err_code)
	return err_code

def CameraSetHDR(hCamera, value):
	err_code = _sdk.CameraSetHDR(hCamera, value)
	SetLastError(err_code)
	return err_code

def CameraGetHDR(hCamera):
	value = c_int()
	err_code = _sdk.CameraGetHDR(hCamera, byref(value))
	SetLastError(err_code)
	return value.value

def CameraGetFrameID(hCamera):
	FrameID = c_uint()
	err_code = _sdk.CameraGetFrameID(hCamera, byref(FrameID))
	SetLastError(err_code)
	return FrameID.value

def CameraGetFrameTimeStamp(hCamera):
	TimeStamp = c_uint64()
	TimeStampL = c_uint32.from_buffer(TimeStamp)
	TimeStampH = c_uint32.from_buffer(TimeStamp, 4)
	err_code = _sdk.CameraGetFrameTimeStamp(hCamera, byref(TimeStampL), byref(TimeStampH))
	SetLastError(err_code)
	return TimeStamp.value

def CameraSetHDRGainMode(hCamera, value):
	err_code = _sdk.CameraSetHDRGainMode(hCamera, value)
	SetLastError(err_code)
	return err_code

def CameraGetHDRGainMode(hCamera):
	value = c_int()
	err_code = _sdk.CameraGetHDRGainMode(hCamera, byref(value))
	SetLastError(err_code)
	return value.value

def CameraCreateDIBitmap(hDC, pFrameBuffer, pFrameHead):
	outBitmap = c_void_p()
	err_code = _sdk.CameraCreateDIBitmap(hDC, c_void_p(pFrameBuffer), byref(pFrameHead), byref(outBitmap))
	SetLastError(err_code)
	return outBitmap.value

def CameraDrawFrameBuffer(pFrameBuffer, pFrameHead, hWnd, Algorithm, Mode):
	err_code = _sdk.CameraDrawFrameBuffer(c_void_p(pFrameBuffer), byref(pFrameHead), c_void_p(hWnd), Algorithm, Mode)
	SetLastError(err_code)
	return err_code

def CameraFlipFrameBuffer(pFrameBuffer, pFrameHead, Flags):
	err_code = _sdk.CameraFlipFrameBuffer(c_void_p(pFrameBuffer), byref(pFrameHead), Flags)
	SetLastError(err_code)
	return err_code

def CameraConvertFrameBufferFormat(hCamera, pInFrameBuffer, pOutFrameBuffer, outWidth, outHeight, outMediaType, pFrameHead):
	err_code = _sdk.CameraConvertFrameBufferFormat(hCamera, c_void_p(pInFrameBuffer), c_void_p(pOutFrameBuffer), outWidth, outHeight, outMediaType, byref(pFrameHead))
	SetLastError(err_code)
	return err_code

def CameraSetConnectionStatusCallback(hCamera, pCallBack, pContext = 0):
	err_code = _sdk.CameraSetConnectionStatusCallback(hCamera, pCallBack, c_void_p(pContext) )
	SetLastError(err_code)
	return err_code

def CameraSetLightingControllerMode(hCamera, index, mode):
	err_code = _sdk.CameraSetLightingControllerMode(hCamera, index, mode)
	SetLastError(err_code)
	return err_code

def CameraSetLightingControllerState(hCamera, index, state):
	err_code = _sdk.CameraSetLightingControllerState(hCamera, index, state)
	SetLastError(err_code)
	return err_code

def CameraSetFrameResendCount(hCamera, count):
	err_code = _sdk.CameraSetFrameResendCount(hCamera, count)
	SetLastError(err_code)
	return err_code

def CameraSetUndistortParams(hCamera, width, height, cameraMatrix, distCoeffs):
	assert(len(cameraMatrix) == 4)
	assert(len(distCoeffs) == 5)
	cameraMatrixNative = (c_double * len(cameraMatrix))(*cameraMatrix)
	distCoeffsNative = (c_double * len(distCoeffs))(*distCoeffs)
	err_code = _sdk.CameraSetUndistortParams(hCamera, width, height, cameraMatrixNative, distCoeffsNative)
	SetLastError(err_code)
	return err_code

def CameraGetUndistortParams(hCamera):
	width = c_int()
	height = c_int()
	cameraMatrix = (c_double * 4)()
	distCoeffs = (c_double * 5)()
	err_code = _sdk.CameraGetUndistortParams(hCamera, byref(width), byref(height), cameraMatrix, distCoeffs)
	SetLastError(err_code)
	width, height = width.value, height.value
	cameraMatrix = cameraMatrix[:]
	distCoeffs = distCoeffs[:]
	return (width, height, cameraMatrix, distCoeffs)

def CameraSetUndistortEnable(hCamera, bEnable):
	err_code = _sdk.CameraSetUndistortEnable(hCamera, bEnable)
	SetLastError(err_code)
	return err_code

def CameraGetUndistortEnable(hCamera):
	value = c_int()
	err_code = _sdk.CameraGetUndistortEnable(hCamera, byref(value))
	SetLastError(err_code)
	return value.value

def CameraCustomizeUndistort(hCamera, hParent):
	err_code = _sdk.CameraCustomizeUndistort(hCamera, hParent)
	SetLastError(err_code)
	return err_code

def CameraGetEyeCount(hCamera):
	EyeCount = c_int()
	err_code = _sdk.CameraGetEyeCount(hCamera, byref(EyeCount))
	SetLastError(err_code)
	return EyeCount.value

def CameraMultiEyeImageProcess(hCamera, iEyeIndex, pbyIn, pInFrInfo, pbyOut, pOutFrInfo, uOutFormat, uReserved):
	err_code = _sdk.CameraMultiEyeImageProcess(hCamera, iEyeIndex, c_void_p(pbyIn), byref(pInFrInfo), c_void_p(pbyOut), byref(pOutFrInfo), uOutFormat, uReserved)
	SetLastError(err_code)
	return err_code

# CameraGrabber

def CameraGrabber_CreateFromDevicePage():
	Grabber = c_void_p()
	err_code = _sdk.CameraGrabber_CreateFromDevicePage(byref(Grabber))
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return Grabber.value

def CameraGrabber_CreateByIndex(Index):
	Grabber = c_void_p()
	err_code = _sdk.CameraGrabber_CreateByIndex(byref(Grabber), Index)
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return Grabber.value

def CameraGrabber_CreateByName(Name):
	Grabber = c_void_p()
	err_code = _sdk.CameraGrabber_CreateByName(byref(Grabber), _str_to_string_buffer(Name))
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return Grabber.value

def CameraGrabber_Create(pDevInfo):
	Grabber = c_void_p()
	err_code = _sdk.CameraGrabber_Create(byref(Grabber), byref(pDevInfo))
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return Grabber.value

def CameraGrabber_Destroy(Grabber):
	err_code = _sdk.CameraGrabber_Destroy(c_void_p(Grabber))
	SetLastError(err_code)
	return err_code

def CameraGrabber_SetHWnd(Grabber, hWnd):
	err_code = _sdk.CameraGrabber_SetHWnd(c_void_p(Grabber), c_void_p(hWnd) )
	SetLastError(err_code)
	return err_code

def CameraGrabber_SetPriority(Grabber, Priority):
	err_code = _sdk.CameraGrabber_SetPriority(c_void_p(Grabber), Priority)
	SetLastError(err_code)
	return err_code

def CameraGrabber_StartLive(Grabber):
	err_code = _sdk.CameraGrabber_StartLive(c_void_p(Grabber))
	SetLastError(err_code)
	return err_code

def CameraGrabber_StopLive(Grabber):
	err_code = _sdk.CameraGrabber_StopLive(c_void_p(Grabber))
	SetLastError(err_code)
	return err_code

def CameraGrabber_SaveImage(Grabber, TimeOut):
	Image = c_void_p()
	err_code = _sdk.CameraGrabber_SaveImage(c_void_p(Grabber), byref(Image), TimeOut)
	SetLastError(err_code)
	if err_code != 0:
		raise CameraException(err_code)
	return Image.value

def CameraGrabber_SaveImageAsync(Grabber):
	err_code = _sdk.CameraGrabber_SaveImageAsync(c_void_p(Grabber))
	SetLastError(err_code)
	return err_code

def CameraGrabber_SaveImageAsyncEx(Grabber, UserData):
	err_code = _sdk.CameraGrabber_SaveImageAsyncEx(c_void_p(Grabber), c_void_p(UserData))
	SetLastError(err_code)
	return err_code

def CameraGrabber_SetSaveImageCompleteCallback(Grabber, Callback, Context = 0):
	err_code = _sdk.CameraGrabber_SetSaveImageCompleteCallback(c_void_p(Grabber), Callback, c_void_p(Context))
	SetLastError(err_code)
	return err_code

def CameraGrabber_SetFrameListener(Grabber, Listener, Context = 0):
	err_code = _sdk.CameraGrabber_SetFrameListener(c_void_p(Grabber), Listener, c_void_p(Context))
	SetLastError(err_code)
	return err_code

def CameraGrabber_SetRawCallback(Grabber, Callback, Context = 0):
	err_code = _sdk.CameraGrabber_SetRawCallback(c_void_p(Grabber), Callback, c_void_p(Context))
	SetLastError(err_code)
	return err_code

def CameraGrabber_SetRGBCallback(Grabber, Callback, Context = 0):
	err_code = _sdk.CameraGrabber_SetRGBCallback(c_void_p(Grabber), Callback, c_void_p(Context))
	SetLastError(err_code)
	return err_code

def CameraGrabber_GetCameraHandle(Grabber):
	hCamera = c_int()
	err_code = _sdk.CameraGrabber_GetCameraHandle(c_void_p(Grabber), byref(hCamera))
	SetLastError(err_code)
	return hCamera.value

def CameraGrabber_GetStat(Grabber):
	stat = tSdkGrabberStat()
	err_code = _sdk.CameraGrabber_GetStat(c_void_p(Grabber), byref(stat))
	SetLastError(err_code)
	return stat

def CameraGrabber_GetCameraDevInfo(Grabber):
	DevInfo = tSdkCameraDevInfo()
	err_code = _sdk.CameraGrabber_GetCameraDevInfo(c_void_p(Grabber), byref(DevInfo))
	SetLastError(err_code)
	return DevInfo

# CameraImage

def CameraImage_Create(pFrameBuffer, pFrameHead, bCopy):
	Image = c_void_p()
	err_code = _sdk.CameraImage_Create(byref(Image), c_void_p(pFrameBuffer), byref(pFrameHead), bCopy)
	SetLastError(err_code)
	return Image.value

def CameraImage_CreateEmpty():
	Image = c_void_p()
	err_code = _sdk.CameraImage_CreateEmpty(byref(Image))
	SetLastError(err_code)
	return Image.value

def CameraImage_Destroy(Image):
	err_code = _sdk.CameraImage_Destroy(c_void_p(Image))
	SetLastError(err_code)
	return err_code

def CameraImage_GetData(Image):
	DataBuffer = c_void_p()
	HeadPtr = c_void_p()
	err_code = _sdk.CameraImage_GetData(c_void_p(Image), byref(DataBuffer), byref(HeadPtr))
	SetLastError(err_code)
	if err_code == 0:
		return (DataBuffer.value, tSdkFrameHead.from_address(HeadPtr.value) )
	else:
		return (0, None)

def CameraImage_GetUserData(Image):
	UserData = c_void_p()
	err_code = _sdk.CameraImage_GetUserData(c_void_p(Image), byref(UserData))
	SetLastError(err_code)
	return UserData.value

def CameraImage_SetUserData(Image, UserData):
	err_code = _sdk.CameraImage_SetUserData(c_void_p(Image), c_void_p(UserData))
	SetLastError(err_code)
	return err_code

def CameraImage_IsEmpty(Image):
	IsEmpty = c_int()
	err_code = _sdk.CameraImage_IsEmpty(c_void_p(Image), byref(IsEmpty))
	SetLastError(err_code)
	return IsEmpty.value

def CameraImage_Draw(Image, hWnd, Algorithm):
	err_code = _sdk.CameraImage_Draw(c_void_p(Image), c_void_p(hWnd), Algorithm)
	SetLastError(err_code)
	return err_code

def CameraImage_DrawFit(Image, hWnd, Algorithm):
	err_code = _sdk.CameraImage_DrawFit(c_void_p(Image), c_void_p(hWnd), Algorithm)
	SetLastError(err_code)
	return err_code

def CameraImage_DrawToDC(Image, hDC, Algorithm, xDst, yDst, cxDst, cyDst):
	err_code = _sdk.CameraImage_DrawToDC(c_void_p(Image), c_void_p(hDC), Algorithm, xDst, yDst, cxDst, cyDst)
	SetLastError(err_code)
	return err_code

def CameraImage_DrawToDCFit(Image, hDC, Algorithm, xDst, yDst, cxDst, cyDst):
	err_code = _sdk.CameraImage_DrawToDCFit(c_void_p(Image), c_void_p(hDC), Algorithm, xDst, yDst, cxDst, cyDst)
	SetLastError(err_code)
	return err_code

def CameraImage_BitBlt(Image, hWnd, xDst, yDst, cxDst, cyDst, xSrc, ySrc):
	err_code = _sdk.CameraImage_BitBlt(c_void_p(Image), c_void_p(hWnd), xDst, yDst, cxDst, cyDst, xSrc, ySrc)
	SetLastError(err_code)
	return err_code

def CameraImage_BitBltToDC(Image, hDC, xDst, yDst, cxDst, cyDst, xSrc, ySrc):
	err_code = _sdk.CameraImage_BitBltToDC(c_void_p(Image), c_void_p(hDC), xDst, yDst, cxDst, cyDst, xSrc, ySrc)
	SetLastError(err_code)
	return err_code

def CameraImage_SaveAsBmp(Image, FileName):
	err_code = _sdk.CameraImage_SaveAsBmp(c_void_p(Image), _str_to_string_buffer(FileName))
	SetLastError(err_code)
	return err_code

def CameraImage_SaveAsJpeg(Image, FileName, Quality):
	err_code = _sdk.CameraImage_SaveAsJpeg(c_void_p(Image), _str_to_string_buffer(FileName), Quality)
	SetLastError(err_code)
	return err_code

def CameraImage_SaveAsPng(Image, FileName):
	err_code = _sdk.CameraImage_SaveAsPng(c_void_p(Image), _str_to_string_buffer(FileName))
	SetLastError(err_code)
	return err_code

def CameraImage_SaveAsRaw(Image, FileName, Format):
	err_code = _sdk.CameraImage_SaveAsRaw(c_void_p(Image), _str_to_string_buffer(FileName), Format)
	SetLastError(err_code)
	return err_code

def CameraImage_IPicture(Image):
	NewPic = c_void_p()
	err_code = _sdk.CameraImage_IPicture(c_void_p(Image), byref(NewPic))
	SetLastError(err_code)
	return NewPic.value
