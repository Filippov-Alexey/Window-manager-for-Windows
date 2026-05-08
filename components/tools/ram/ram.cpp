#include <windows.h>
#include <iostream>
#include <string>
#include <cmath>

double convert(unsigned long long b, std::string u) {
    if (u == "kb") return b / 1024.0;
    if (u == "mb") return b / 1024.0 / 1024.0;
    if (u == "gb") return b / 1024.0 / 1024.0 / 1024.0;
    if (u == "tb") return b / 1024.0 / 1024.0 / 1024.0 / 1024.0;
    return (double)b;
}

int main(int argc, char* argv[]) {
    std::string unit = (argc > 1) ? argv[1] : "mb";
    // Используем long long для хранения предыдущих целых значений
    long long last_u = -1, last_f = -1;

    while (true) {
        MEMORYSTATUSEX mem = { sizeof(mem) };
        if (GlobalMemoryStatusEx(&mem)) {
            // Округляем сразу до целого
            long long cur_u = static_cast<long long>(std::round(convert(mem.ullTotalPhys - mem.ullAvailPhys, unit)));
            long long cur_f = static_cast<long long>(std::round(convert(mem.ullAvailPhys, unit)));

            if (cur_u != last_u || cur_f != last_f) {
                // Вывод без дробной части
                std::cout << "{\"used_" << unit << "\":" << cur_u << ",\"free_" << unit << "\":" << cur_f << "}" << std::endl;
                last_u = cur_u; 
                last_f = cur_f;
            }
        }
        Sleep(1000);
    }
    return 0;
}
