#include <pybind11/pybind11.h>
#include <chrono>
#include <cstdint>

namespace py = pybind11;

// 하드웨어 타이머 값을 가져오는 함수 (마이크로초 단위)
uint64_t get_hardware_timer() {
    auto now = std::chrono::high_resolution_clock::now();
    auto duration = now.time_since_epoch();
    return std::chrono::duration_cast<std::chrono::microseconds>(duration).count();
}

// 타이머 차이를 계산하는 함수
double get_timer_diff_ms(uint64_t start, uint64_t end) {
    return (end - start) / 1000.0;  // 밀리초로 변환
}

// pybind11 모듈 정의
PYBIND11_MODULE(timer_module, m) {
    m.doc() = "Hardware timer module";
    
    m.def("get_hardware_timer", &get_hardware_timer, 
          "Get hardware timer value in microseconds");
    
    m.def("get_timer_diff_ms", &get_timer_diff_ms, 
          "Calculate timer difference in milliseconds",
          py::arg("start"), py::arg("end"));
}
