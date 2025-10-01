//coding=utf-8
/**
 * Qt Wayland wp_presentation 헬퍼
 * Qt의 실제 wl_surface에 wp_presentation feedback을 연결
 */
#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>
#include <cstdint>
#include <functional>
#include <memory>
#include <map>
#include <mutex>

namespace py = pybind11;

// Wayland presentation 피드백 데이터
struct PresentationFeedback {
    uint64_t timestamp_ns;
    uint64_t sequence;
    uint32_t refresh_ns;
    uint32_t flags;
    bool presented;
};

// 콜백 타입
using FeedbackCallback = std::function<void(const PresentationFeedback&)>;

/**
 * WaylandPresentationMonitor
 * Qt 윈도우의 wl_surface에서 wp_presentation 피드백 수집
 */
class WaylandPresentationMonitor {
public:
    WaylandPresentationMonitor() 
        : wl_display_(nullptr)
        , wl_surface_(nullptr)
        , wp_presentation_(nullptr)
        , presented_count_(0)
        , discarded_count_(0)
        , vsync_count_(0)
        , zero_copy_count_(0) {
    }
    
    ~WaylandPresentationMonitor() {
        cleanup();
    }
    
    /**
     * Qt 윈도우의 네이티브 Wayland 리소스 포인터로 초기화
     * @param wl_display wl_display* 포인터 (uintptr_t)
     * @param wl_surface wl_surface* 포인터 (uintptr_t)
     * @param wp_presentation wp_presentation* 포인터 (uintptr_t)
     */
    bool initialize(uintptr_t wl_display, uintptr_t wl_surface, uintptr_t wp_presentation) {
        wl_display_ = reinterpret_cast<void*>(wl_display);
        wl_surface_ = reinterpret_cast<void*>(wl_surface);
        wp_presentation_ = reinterpret_cast<void*>(wp_presentation);
        
        return wl_display_ && wl_surface_ && wp_presentation_;
    }
    
    /**
     * 피드백 콜백 등록
     */
    void set_callback(FeedbackCallback callback) {
        std::lock_guard<std::mutex> lock(mutex_);
        callback_ = callback;
    }
    
    /**
     * 프레임 피드백 요청
     * 실제로는 libwayland-client를 통해 wp_presentation.feedback() 호출 필요
     * 현재는 통계만 제공
     */
    void request_feedback() {
        // 실제 구현은 libwayland-client API가 필요
        // 여기서는 Qt의 frameSwapped와 동기화하여 사용
    }
    
    /**
     * 통계 정보
     */
    uint64_t presented_count() const { return presented_count_; }
    uint64_t discarded_count() const { return discarded_count_; }
    uint64_t vsync_count() const { return vsync_count_; }
    uint64_t zero_copy_count() const { return zero_copy_count_; }
    uint64_t last_sequence() const { return last_sequence_; }
    uint64_t last_timestamp_ns() const { return last_timestamp_ns_; }
    
    /**
     * 수동 피드백 시뮬레이션 (테스트용)
     */
    void simulate_presented(uint64_t timestamp_ns, uint64_t sequence, uint32_t flags) {
        PresentationFeedback fb;
        fb.timestamp_ns = timestamp_ns;
        fb.sequence = sequence;
        fb.refresh_ns = 16666666; // 60Hz
        fb.flags = flags;
        fb.presented = true;
        
        presented_count_++;
        last_timestamp_ns_ = timestamp_ns;
        last_sequence_ = sequence;
        
        if (flags & 0x1) vsync_count_++;      // VSYNC
        if (flags & 0x8) zero_copy_count_++;  // ZERO_COPY
        
        if (callback_) {
            callback_(fb);
        }
    }
    
    void simulate_discarded() {
        PresentationFeedback fb;
        fb.presented = false;
        
        discarded_count_++;
        
        if (callback_) {
            callback_(fb);
        }
    }
    
private:
    void cleanup() {
        // 리소스 정리 (필요시)
    }
    
    void* wl_display_;
    void* wl_surface_;
    void* wp_presentation_;
    
    FeedbackCallback callback_;
    std::mutex mutex_;
    
    // 통계
    std::atomic<uint64_t> presented_count_;
    std::atomic<uint64_t> discarded_count_;
    std::atomic<uint64_t> vsync_count_;
    std::atomic<uint64_t> zero_copy_count_;
    std::atomic<uint64_t> last_sequence_;
    std::atomic<uint64_t> last_timestamp_ns_;
};

/**
 * Qt 윈도우의 네이티브 Wayland 포인터 추출 헬퍼
 */
uintptr_t get_wl_display_ptr() {
    // Qt Native Interface를 통해 wl_display* 얻기
    // 실제 구현은 Qt 헤더 필요
    // 지금은 Python에서 전달받은 포인터 사용
    return 0;
}

uintptr_t get_wl_surface_ptr(uintptr_t qwindow_ptr) {
    // Qt Native Interface를 통해 wl_surface* 얻기
    // 실제 구현은 Qt 헤더 필요
    return 0;
}

// pybind11 바인딩
PYBIND11_MODULE(wayland_presentation, m) {
    m.doc() = "Qt Wayland wp_presentation 헬퍼";
    
    py::class_<PresentationFeedback>(m, "PresentationFeedback")
        .def_readonly("timestamp_ns", &PresentationFeedback::timestamp_ns)
        .def_readonly("sequence", &PresentationFeedback::sequence)
        .def_readonly("refresh_ns", &PresentationFeedback::refresh_ns)
        .def_readonly("flags", &PresentationFeedback::flags)
        .def_readonly("presented", &PresentationFeedback::presented);
    
    py::class_<WaylandPresentationMonitor>(m, "WaylandPresentationMonitor")
        .def(py::init<>())
        .def("initialize", &WaylandPresentationMonitor::initialize,
             "Qt 윈도우의 Wayland 리소스로 초기화")
        .def("set_callback", &WaylandPresentationMonitor::set_callback,
             "피드백 콜백 함수 등록")
        .def("request_feedback", &WaylandPresentationMonitor::request_feedback,
             "프레임 피드백 요청")
        .def("presented_count", &WaylandPresentationMonitor::presented_count)
        .def("discarded_count", &WaylandPresentationMonitor::discarded_count)
        .def("vsync_count", &WaylandPresentationMonitor::vsync_count)
        .def("zero_copy_count", &WaylandPresentationMonitor::zero_copy_count)
        .def("last_sequence", &WaylandPresentationMonitor::last_sequence)
        .def("last_timestamp_ns", &WaylandPresentationMonitor::last_timestamp_ns)
        .def("simulate_presented", &WaylandPresentationMonitor::simulate_presented,
             "테스트용: presented 이벤트 시뮬레이션")
        .def("simulate_discarded", &WaylandPresentationMonitor::simulate_discarded,
             "테스트용: discarded 이벤트 시뮬레이션");
    
    m.def("get_wl_display_ptr", &get_wl_display_ptr,
          "Qt의 wl_display* 포인터 얻기 (향후 구현)");
    m.def("get_wl_surface_ptr", &get_wl_surface_ptr,
          "Qt 윈도우의 wl_surface* 포인터 얻기 (향후 구현)",
          py::arg("qwindow_ptr"));
}

