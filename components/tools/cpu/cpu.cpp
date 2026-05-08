#include <windows.h>
#include <iostream>
#include <cmath>

// Функция для расчета загрузки CPU
double GetCPUUsage() {
    static FILETIME prevIdleTime, prevKernelTime, prevUserTime;
    FILETIME idleTime, kernelTime, userTime;

    if (!GetSystemTimes(&idleTime, &kernelTime, &userTime)) return 0;

    auto FileTimeToQuad = [](FILETIME ft) {
        return (unsigned __int64)ft.dwLowDateTime | ((unsigned __int64)ft.dwHighDateTime << 32);
    };

    unsigned __int64 idle = FileTimeToQuad(idleTime) - FileTimeToQuad(prevIdleTime);
    unsigned __int64 kernel = FileTimeToQuad(kernelTime) - FileTimeToQuad(prevKernelTime);
    unsigned __int64 user = FileTimeToQuad(userTime) - FileTimeToQuad(prevUserTime);

    prevIdleTime = idleTime; prevKernelTime = kernelTime; prevUserTime = userTime;

    unsigned __int64 total = kernel + user;
    if (total == 0) return 0;
    return (double)(total - idle) * 100.0 / total;
}

int main() {
    int last_load = -1;
    GetCPUUsage(); 
    Sleep(500);

    while (true) {
        // Округляем до ближайшего целого
        int current_load = static_cast<int>(std::round(GetCPUUsage()));

        // Гарантируем диапазон 0-100 (иногда из-за специфики замера бывает микро-вылет)
        if (current_load < 0) current_load = 0;
        if (current_load > 100) current_load = 100;

        if (current_load != last_load) {
            std::cout << "{\"cpu_load_pct\":" << current_load << "}" << std::endl;
            last_load = current_load;
        }
        Sleep(1000);
    }
    return 0;
}
