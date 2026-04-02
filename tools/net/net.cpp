#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <iphlpapi.h>
#include <netioapi.h>
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "ws2_32.lib")

// Массив для сопоставления индекса и единицы
const char* units[] = { "b", "kb", "mb", "gb", "tb" };

// Возвращает индекс единицы измерения (0-4)
int get_unit_index(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), ::tolower);
    for (int i = 0; i < 5; ++i) {
        if (s == units[i] || (s.length() > 0 && s[0] == units[i][0] && s.length() == 1)) return i;
    }
    return 0;
}

// Определяет, в какой индекс попадает текущее кол-во байт
int get_current_unit_index(double bytes) {
    int i = 0;
    while (bytes >= 1024.0 && i < 4) {
        bytes /= 1024.0;
        i++;
    }
    return i;
}

std::string format_smart(double bytes) {
    int i = get_current_unit_index(bytes);
    double val = bytes;
    
    // Приводим значение к нужной единице измерения
    for(int j = 0; j < i; ++j) val /= 1024.0;
    
    char buf[64];
    // %.0f — выводит число как целое (округляет до ближайшего целого)
    // %s — добавляет единицу измерения (kb, mb и т.д.)
    sprintf_s(buf, "%.0f%s", val, units[i]);
    
    return std::string(buf);
}


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

                std::wstring ws(table->Table[i].Description);
                std::string name(ws.begin(), ws.end());

                if (target == "all" || name.find(target) != std::string::npos) {
                    cur_rx += table->Table[i].InOctets;
                    cur_tx += table->Table[i].OutOctets;
                }
            }

            if (last_rx > 0) {
                double diff_rx = (double)(cur_rx - last_rx);
                double diff_tx = (double)(cur_tx - last_tx);

                // Получаем индексы текущих единиц для RX и TX
                int cur_rx_idx = get_current_unit_index(diff_rx);
                int cur_tx_idx = get_current_unit_index(diff_tx);

                // Проверка: попадает ли порядок величины в [min_idx, max_idx]
                bool rx_ok = (cur_rx_idx >= min_idx && cur_rx_idx <= max_idx);
                bool tx_ok = (cur_tx_idx >= min_idx && cur_tx_idx <= max_idx);

                if (rx_ok || tx_ok) {
                    std::cout << "{\"rx\":\"" << format_smart(diff_rx) 
                              << "\",\"tx\":\"" << format_smart(diff_tx) << "\"}" << std::endl;
                }
            }
            last_rx = cur_rx; last_tx = cur_tx;
            if (table) FreeMibTable(table);
        }
        Sleep(1000);
    }
    return 0;
}
