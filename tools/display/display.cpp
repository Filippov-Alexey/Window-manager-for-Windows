#include <windows.h>
#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <fcntl.h>
#include <io.h>

std::wstring EscapeJSON(std::wstring val) {
    std::wstring res;
    for (const auto& c : val) {
        if (c == L'\\') res += L"\\\\";
        else if (c == L'\"') res += L"\\\"";
        else res += c;
    }
    return res;
}

std::wstring GetTopologyName(DISPLAYCONFIG_TOPOLOGY_ID id) {
    switch (id) {
        case DISPLAYCONFIG_TOPOLOGY_INTERNAL: return L"PC screen only";
        case DISPLAYCONFIG_TOPOLOGY_CLONE:    return L"Duplicate";
        case DISPLAYCONFIG_TOPOLOGY_EXTEND:   return L"Extend";
        case DISPLAYCONFIG_TOPOLOGY_EXTERNAL: return L"Second screen only";
        default: return L"Unknown";
    }
}

std::wstring GenerateJSON() {
    std::wstringstream json;
    json << L"{\"monitors\":[";

    DISPLAY_DEVICEW dd;
    dd.cb = sizeof(dd);
    DWORD deviceIndex = 0;
    bool firstMonitor = true;

    while (EnumDisplayDevicesW(NULL, deviceIndex, &dd, 0)) {
        DISPLAY_DEVICEW monitor;
        monitor.cb = sizeof(monitor);
        DWORD monitorIndex = 0;
        while (EnumDisplayDevicesW(dd.DeviceName, monitorIndex, &monitor, 0)) {
            if (monitor.StateFlags & DISPLAY_DEVICE_ACTIVE) {
                if (!firstMonitor) json << L",";
                json << L"{\"adapter\":\"" << EscapeJSON(dd.DeviceName) << L"\",";
                json << L"\"name\":\"" << EscapeJSON(monitor.DeviceString) << L"\",";
                json << L"\"id\":\"" << EscapeJSON(monitor.DeviceID) << L"\",";
                json << L"\"is_primary\":" << ((monitor.StateFlags & DISPLAY_DEVICE_PRIMARY_DEVICE) ? L"true" : L"false") << L"}";
                firstMonitor = false;
            }
            monitorIndex++;
        }
        deviceIndex++;
    }

    UINT32 pathCount = 0, modeCount = 0;
    DISPLAYCONFIG_TOPOLOGY_ID topology = (DISPLAYCONFIG_TOPOLOGY_ID)0;
    if (GetDisplayConfigBufferSizes(QDC_DATABASE_CURRENT, &pathCount, &modeCount) == ERROR_SUCCESS) {
        std::vector<DISPLAYCONFIG_PATH_INFO> paths(pathCount);
        std::vector<DISPLAYCONFIG_MODE_INFO> modes(modeCount);
        QueryDisplayConfig(QDC_DATABASE_CURRENT, &pathCount, paths.data(), &modeCount, modes.data(), &topology);
    }

    json << L"],\"projection_mode\":\"" << GetTopologyName(topology) << L"\",\"topology_id\":" << (int)topology << L"}";
    return json.str();
}

int main() {
    _setmode(_fileno(stdout), _O_U16TEXT);
    
    std::wstring lastJson = L"";

    while (true) {
        std::wstring currentJson = GenerateJSON();

        if (currentJson != lastJson) {
            std::wcout << currentJson << std::endl; // Вывод с новой строки для удобства парсинга потока
            lastJson = currentJson;
        }

        Sleep(1000); // Опрос раз в секунду
    }

    return 0;
}
