#include <windows.h>
#include <iostream>

// Определяем типы функций из DLL вручную
typedef int (*nvml_int_f)();
typedef int (*nvml_dev_f)(unsigned int, void**);
typedef int (*nvml_util_f)(void*, void*);
typedef int (*nvml_temp_f)(void*, int, unsigned int*);

struct nvmlUtilization_t { unsigned int gpu; unsigned int memory; };

int main() {
    HMODULE h = LoadLibraryA("nvml.dll");
    if (!h) {
        std::cerr << "{\"error\":\"NVML.dll not found\"}" << std::endl;
        return 1;
    }

    // Загружаем функции
    auto init = (nvml_int_f)GetProcAddress(h, "nvmlInit");
    auto getHandle = (nvml_dev_f)GetProcAddress(h, "nvmlDeviceGetHandleByIndex");
    auto getUtil = (nvml_util_f)GetProcAddress(h, "nvmlDeviceGetUtilizationRates");
    auto getTemp = (nvml_temp_f)GetProcAddress(h, "nvmlDeviceGetTemperature");

    if (init() != 0) return 1;

    void* device;
    getHandle(0, &device);

    unsigned int last_t = 0, last_u = 0;

    while (true) {
        nvmlUtilization_t util;
        unsigned int temp = 0;

        if (getUtil(device, &util) == 0 && getTemp(device, 0, &temp) == 0) {
            if (temp != last_t || util.gpu != last_u) {
                std::cout << "{\"gpu_load_pct\":" << util.gpu 
                          << ",\"gpu_temp_c\":" << temp << "}" << std::endl;
                last_t = temp; last_u = util.gpu;
            }
        }
        Sleep(1000);
    }
    return 0;
}
