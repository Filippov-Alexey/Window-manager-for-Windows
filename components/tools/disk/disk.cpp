#include <windows.h>
#include <iostream>
#include <string>

double convert(unsigned long long b, std::string u) {
    if (u == "kb") return b / 1024.0;
    if (u == "mb") return b / 1024.0 / 1024.0;
    if (u == "gb") return b / 1024.0 / 1024.0 / 1024.0;
    if (u == "tb") return b / 1024.0 / 1024.0 / 1024.0 / 1024.0;
    return (double)b;
}

int main(int argc, char* argv[]) {
    if (argc < 2) return 1;
    std::string path = std::string(argv[1]) + ":\\";
    std::string unit = (argc > 2) ? argv[2] : "gb";
    double last_u = -1, last_f = -1;

    while (true) {
        ULARGE_INTEGER f, t, tf;
        if (GetDiskFreeSpaceExA(path.c_str(), &f, &t, &tf)) {
// Используем прямое приведение к unsigned long long для отсечения дроби
unsigned long long cur_u = (unsigned long long)convert(t.QuadPart - f.QuadPart, unit);
unsigned long long cur_f = (unsigned long long)convert(f.QuadPart, unit);

if (cur_u != (unsigned long long)last_u || cur_f != (unsigned long long)last_f) {
    // Выводим как целые числа (%llu или просто через поток)
    std::cout << "{\"drive\":\"" << argv[1] 
              << "\",\"used_" << unit << "\":" << cur_u 
              << ",\"free_" << unit << "\":" << cur_f << "}" << std::endl;
    
    last_u = (double)cur_u; 
    last_f = (double)cur_f;
}
        }
        Sleep(5000);
    }
}
