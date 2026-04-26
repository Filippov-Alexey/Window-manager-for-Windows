#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <iphlpapi.h>
#include <netioapi.h>
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <cmath>

#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "ws2_32.lib")

const char* units[] = { "b", "kb", "mb", "gb", "tb" };

int get_unit_index(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), ::tolower);
    for (int i = 0; i < 5; ++i) {
        if (s == units[i]) return i;
    }
    return 0; 
}

// Новая функция форматирования с учетом границ
std::string format_constrained(double bytes, int min_idx, int max_idx) {
    // 1. Определяем "идеальный" индекс
    int idx = 0;
    double temp = bytes;
    while (temp >= 1024.0 && idx < 4) {
        temp /= 1024.0;
        idx++;
    }

    // 2. Применяем ограничения min/max
    if (idx < min_idx) idx = min_idx;
    if (idx > max_idx) idx = max_idx;

    // 3. Вычисляем итоговое значение для выбранного индекса
    double final_val = bytes / std::pow(1024.0, idx);

    char buf[64];
    // %.1f если нужны дробные, или %.0f для целых как в вашем примере
    sprintf_s(buf, "%.0f%s", final_val, units[idx]);
    return std::string(buf);
}

// Поиск аргумента (исправлен предел цикла до argc)
std::string find_arg(int argc, char* argv[], std::string flag, std::string def) {
    for (int i = 1; i < argc - 1; ++i) {
        if (std::string(argv[i]) == flag) return argv[i + 1];
    }
    return def;
}

int main(int argc, char* argv[]) {
    std::string target = find_arg(argc, argv, "/a", "all");
    int min_idx = get_unit_index(find_arg(argc, argv, "/min", "b"));
    int max_idx = get_unit_index(find_arg(argc, argv, "/max", "tb"));

    unsigned long long last_rx = 0, last_tx = 0;

    while (true) {
        PMIB_IF_TABLE2 table = NULL;
        if (GetIfTable2(&table) == NO_ERROR) {
            unsigned long long cur_rx = 0, cur_tx = 0;
            for (ULONG i = 0; i < table->NumEntries; i++) {
                if (table->Table[i].Type == IF_TYPE_SOFTWARE_LOOPBACK) continue;
                if (table->Table[i].OperStatus != IfOperStatusUp) continue;

                // Фильтр по имени интерфейса
                if (target != "all") {
                    std::wstring ws(table->Table[i].Description);
                    std::string name(ws.begin(), ws.end());
                    if (name.find(target) == std::string::npos) continue;
                }
                
                cur_rx += table->Table[i].InOctets;
                cur_tx += table->Table[i].OutOctets;
            }

            if (last_rx > 0 || last_tx > 0) {
                double diff_rx = (double)(cur_rx >= last_rx ? cur_rx - last_rx : 0);
                double diff_tx = (double)(cur_tx >= last_tx ? cur_tx - last_tx : 0);

                // Выводим всегда, так как format_constrained сам подгонит под min_idx
                std::cout << "{\"rx\":\"" << format_constrained(diff_rx, min_idx, max_idx) 
                          << "\",\"tx\":\"" << format_constrained(diff_tx, min_idx, max_idx) << "\"}" << std::endl;
            }
            
            last_rx = cur_rx; 
            last_tx = cur_tx;
            if (table) FreeMibTable(table);
        }
        Sleep(1000);
    }
    return 0;
}
