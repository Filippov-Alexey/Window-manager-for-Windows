#include <windows.h>
#include <string>  
#include <iostream>
#include <vector>
#include <fcntl.h>
#include <io.h>
#include <algorithm>
#pragma comment(lib, "User32.lib")

// Добавьте эту функцию или замените PrintEscaped
std::wstring EscapeJSON(const wchar_t* str) {
    std::wstring escaped;
    for (; *str; ++str) {
        if (*str == L'\\') escaped += L"\\\\";
        else if (*str == L'\"') escaped += L"\\\"";
        else escaped += *str;
    }
    return escaped;
}

void PrintJSON(DISPLAYCONFIG_TOPOLOGY_ID topology) {
    std::vector<std::wstring> json_monitors;
    long min_x = 0, min_y = 0, max_x = 0, max_y = 0;
    bool first_bounds = true;

    DISPLAY_DEVICEW dd = { sizeof(dd) };
    for (DWORD i = 0; EnumDisplayDevicesW(NULL, i, &dd, 0); ++i) {
        if (!(dd.StateFlags & DISPLAY_DEVICE_ATTACHED_TO_DESKTOP)) continue;

        DEVMODEW dm = { sizeof(dm) };
        if (EnumDisplaySettingsW(dd.DeviceName, ENUM_CURRENT_SETTINGS, &dm)) {
            
            // Расчет границ для общего разрешения
            long left = dm.dmPosition.x;
            long top = dm.dmPosition.y;
            long right = left + dm.dmPelsWidth;
            long bottom = top + dm.dmPelsHeight;

            if (first_bounds) {
                min_x = left; min_y = top; max_x = right; max_y = bottom;
                first_bounds = false;
            } else {
                min_x = (std::min)(min_x, left);
                min_y = (std::min)(min_y, top);
                max_x = (std::max)(max_x, right);
                max_y = (std::max)(max_y, bottom);
            }

            // Формируем JSON объекта монитора
// ... внутри цикла EnumDisplayDevicesW ...
std::wstring m_json = L"{";
// ИСПОЛЬЗУЕМ EscapeJSON для всех строковых полей:
m_json += L"\"adapter\":\"" + EscapeJSON(dd.DeviceName) + L"\",";
m_json += L"\"name\":\"" + EscapeJSON(dd.DeviceString) + L"\",";

m_json += L"\"x\":" + std::to_wstring(dm.dmPosition.x) + L",";
m_json += L"\"y\":" + std::to_wstring(dm.dmPosition.y) + L",";
m_json += L"\"width\":" + std::to_wstring(dm.dmPelsWidth) + L",";
m_json += L"\"height\":" + std::to_wstring(dm.dmPelsHeight) + L",";
m_json += L"\"orientation\":\"" + std::wstring(dm.dmPelsWidth >= dm.dmPelsHeight ? L"landscape" : L"portrait") + L"\",";
m_json += L"\"is_primary\":" + std::wstring((dd.StateFlags & DISPLAY_DEVICE_PRIMARY_DEVICE) ? L"true" : L"false");
m_json += L"}";
json_monitors.push_back(m_json);
        }
    }

    // Вывод итогового JSON
    std::wcout << L"{\"total_bounds\":{";
    std::wcout << L"\"x\":" << min_x << L",\"y\":" << min_y << L",";
    std::wcout << L"\"w\":" << (max_x - min_x) << L",\"h\":" << (max_y - min_y);
    std::wcout << L"},\"monitors\":[";
    for (size_t i = 0; i < json_monitors.size(); ++i) {
        std::wcout << json_monitors[i] << (i == json_monitors.size() - 1 ? L"" : L",");
    }

    const wchar_t* topName = L"Unknown";
    if (topology == DISPLAYCONFIG_TOPOLOGY_INTERNAL) topName = L"PC screen only";
    else if (topology == DISPLAYCONFIG_TOPOLOGY_CLONE) topName = L"Duplicate";
    else if (topology == DISPLAYCONFIG_TOPOLOGY_EXTEND) topName = L"Extend";
    else if (topology == DISPLAYCONFIG_TOPOLOGY_EXTERNAL) topName = L"Second screen only";
// Замените финальный вывод в main:
std::wcout << L"],\"projection_mode\":\"" << topName << L"\"}"<<std::endl; // Убрали endl
// std::wcout.flush(); // Сб/расываем буфер принудительно

}

int main() {
    _setmode(_fileno(stdout), _O_U8TEXT);
    DISPLAYCONFIG_TOPOLOGY_ID lastTopology = (DISPLAYCONFIG_TOPOLOGY_ID)-1;
    UINT32 lastPathCount = 0;

    while (true) {
        UINT32 pathCount = 0, modeCount = 0;
        if (GetDisplayConfigBufferSizes(QDC_DATABASE_CURRENT, &pathCount, &modeCount) == ERROR_SUCCESS) {
            std::vector<DISPLAYCONFIG_PATH_INFO> paths(pathCount);
            std::vector<DISPLAYCONFIG_MODE_INFO> modes(modeCount);
            DISPLAYCONFIG_TOPOLOGY_ID currentTopology;
            
            if (QueryDisplayConfig(QDC_DATABASE_CURRENT, &pathCount, paths.data(), &modeCount, modes.data(), &currentTopology) == ERROR_SUCCESS) {
                if (currentTopology != lastTopology || pathCount != lastPathCount) {
                    PrintJSON(currentTopology);
                    lastTopology = currentTopology;
                    lastPathCount = pathCount;
                }
            }
        }
        Sleep(1000);
    }
    return 0;
}
