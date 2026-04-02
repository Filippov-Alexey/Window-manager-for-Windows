#include <windows.h>
#include <iostream>
#include <vector>
#include <fcntl.h>
#include <io.h>

// Печать сразу в stdout без лишних аллокаций строк
void PrintEscaped(const wchar_t* str) {
    for (; *str; ++str) {
        if (*str == L'\\') std::wcout << L"\\\\";
        else if (*str == L'\"') std::wcout << L"\\\"";
        else std::wcout << *str;
    }
}

void PrintJSON(DISPLAYCONFIG_TOPOLOGY_ID topology) {
    std::wcout << L"{\"monitors\":[";
    DISPLAY_DEVICEW dd = { sizeof(dd) };
    bool first = true;

    for (DWORD i = 0; EnumDisplayDevicesW(NULL, i, &dd, 0); ++i) {
        DISPLAY_DEVICEW monitor = { sizeof(monitor) };
        for (DWORD j = 0; EnumDisplayDevicesW(dd.DeviceName, j, &monitor, 0); ++j) {
            if (monitor.StateFlags & DISPLAY_DEVICE_ACTIVE) {
                if (!first) std::wcout << L",";
                std::wcout << L"{\"adapter\":\""; PrintEscaped(dd.DeviceName);
                std::wcout << L"\",\"name\":\""; PrintEscaped(monitor.DeviceString);
                std::wcout << L"\",\"id\":\"";   PrintEscaped(monitor.DeviceID);
                std::wcout << L"\",\"is_primary\":" << ((monitor.StateFlags & DISPLAY_DEVICE_PRIMARY_DEVICE) ? L"true" : L"false") << L"}";
                first = false;
            }
        }
    }

    const wchar_t* topName = L"Unknown";
    if (topology == DISPLAYCONFIG_TOPOLOGY_INTERNAL) topName = L"PC screen only";
    else if (topology == DISPLAYCONFIG_TOPOLOGY_CLONE) topName = L"Duplicate";
    else if (topology == DISPLAYCONFIG_TOPOLOGY_EXTEND) topName = L"Extend";
    else if (topology == DISPLAYCONFIG_TOPOLOGY_EXTERNAL) topName = L"Second screen only";

    std::wcout << L"],\"projection_mode\":\"" << topName 
               << L"\",\"topology_id\":" << (int)topology << L"}" << std::endl;
}

int main() {
    _setmode(_fileno(stdout), _O_U16TEXT);

    DISPLAYCONFIG_TOPOLOGY_ID lastTopology = (DISPLAYCONFIG_TOPOLOGY_ID)-1;
    UINT32 lastPathCount = 0;

    while (true) {
        UINT32 pathCount = 0, modeCount = 0;
        DISPLAYCONFIG_TOPOLOGY_ID currentTopology = (DISPLAYCONFIG_TOPOLOGY_ID)0;

        // Легкая проверка: изменилось ли количество путей или режим
        if (GetDisplayConfigBufferSizes(QDC_DATABASE_CURRENT, &pathCount, &modeCount) == ERROR_SUCCESS) {
            // Если топология или число путей (мониторов) изменилось — перерисовываем
            // Можно добавить проверку контрольной суммы имен, если нужно ловить переименования без смены топологии
            if (pathCount != lastPathCount) { 
                // Получаем текущую топологию
                std::vector<DISPLAYCONFIG_PATH_INFO> paths(pathCount);
                std::vector<DISPLAYCONFIG_MODE_INFO> modes(modeCount);
                if (QueryDisplayConfig(QDC_DATABASE_CURRENT, &pathCount, paths.data(), &modeCount, modes.data(), &currentTopology) == ERROR_SUCCESS) {
                    
                    if (currentTopology != lastTopology || pathCount != lastPathCount) {
                        PrintJSON(currentTopology);
                        lastTopology = currentTopology;
                        lastPathCount = pathCount;
                    }
                }
            }
        }

        Sleep(1000); 
    }
    return 0;
}
