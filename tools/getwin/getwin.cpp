#include <windows.h>
#include <dwmapi.h>
#include <psapi.h>
#include <string>
#include <vector>
#include <iostream>
#include <algorithm>
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "dwmapi.lib")
#pragma comment(lib, "psapi.lib")

static std::string WideToUtf8(const std::wstring &ws)
{
    if (ws.empty()) return std::string();
    int srcLen = static_cast<int>(ws.size());
    int needed = WideCharToMultiByte(CP_UTF8, 0, ws.data(), srcLen, nullptr, 0, nullptr, nullptr);
    if (needed <= 0) return std::string();
    std::string dst(needed, '\0');
    WideCharToMultiByte(CP_UTF8, 0, ws.data(), srcLen, &dst[0], needed, nullptr, nullptr);
    return dst;
}

static std::string EscapeForPyUtf8(const std::string &s)
{
    std::string out;
    out.reserve(s.size() * 2);
    for (unsigned char ch : s) {
        if (ch == '\\') out += "\\\\";
        else if (ch == '\'') out += "\\'";
        else if (ch == '\n') out += "\\n";
        else if (ch == '\r') out += "\\r";
        else out += static_cast<char>(ch);
    }
    return out;
}

static std::string GetProcessPathFromHwndUtf8(HWND hwnd)
{
    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    if (pid == 0) return "<unknown>";

    std::vector<wchar_t> buf(32768);
    HANDLE h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (h) {
        DWORD size = static_cast<DWORD>(buf.size());
        if (QueryFullProcessImageNameW(h, 0, buf.data(), &size)) {
            std::wstring wres(buf.data(), size);
            CloseHandle(h);
            return WideToUtf8(wres);
        }
        if (GetModuleFileNameExW(h, NULL, buf.data(), static_cast<DWORD>(buf.size()))) {
            std::wstring wres(buf.data());
            CloseHandle(h);
            return WideToUtf8(wres);
        }
        CloseHandle(h);
    }
    h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (h) {
        DWORD size = static_cast<DWORD>(buf.size());
        if (QueryFullProcessImageNameW(h, 0, buf.data(), &size)) {
            std::wstring wres(buf.data(), size);
            CloseHandle(h);
            return WideToUtf8(wres);
        }
        CloseHandle(h);
    }
    return "<unknown>";
}

struct EnumData {
    std::vector<std::string>* items;
    const std::string* filter;
};


bool IsWindowSkippable(HWND hwnd) {
    if (!IsWindowVisible(hwnd)) return true;

    int cloaked = 0;
    if (SUCCEEDED(DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, &cloaked, sizeof(cloaked)))) {
        if (cloaked != 0) return true; 
    }

    LONG exStyle = GetWindowLong(hwnd, GWL_EXSTYLE);
    LONG style = GetWindowLong(hwnd, GWL_STYLE);

    if (exStyle & WS_EX_TOOLWINDOW) return true;

    HWND owner = GetWindow(hwnd, GW_OWNER);
    if (owner != NULL) {
        wchar_t clsBuf[256];
        GetClassNameW(hwnd, clsBuf, 256);
        std::wstring cls(clsBuf);

        bool isDialogClass = (cls == L"#32770");
        bool hasAppWindow = (exStyle & WS_EX_APPWINDOW);
        
        if (!isDialogClass && !hasAppWindow) {
            return true;
        }
    }

    wchar_t clsBuf[256];
    if (GetClassNameW(hwnd, clsBuf, 256)) {
        std::wstring cls(clsBuf);
        if (cls == L"Progman" || cls == L"Shell_TrayWnd" || 
            cls == L"Windows.UI.Core.CoreWindow" || 
            cls == L"IconTrayClone" || 
            cls == L"EdgeUiInputTopWndClass") {
            return true;
        }
    }
    if (GetWindowTextLengthW(hwnd) == 0) return true;

    return false;
}
BOOL CALLBACK EnumWndProc(HWND hwnd, LPARAM lParam) {
    if (IsWindowSkippable(hwnd)) return TRUE; 
    EnumData* d = reinterpret_cast<EnumData*>(lParam);

    // 1. ОПРЕДЕЛЕНИЕ ТИПА
    std::string winType = "normal";
    wchar_t clsCheck[256] = {0};
    GetClassNameW(hwnd, clsCheck, 256);
    std::wstring wclsCheck(clsCheck);
    HWND owner = GetWindow(hwnd, GW_OWNER);
    if (wclsCheck == L"#32770" || owner != NULL) {
        winType = "dialog";
    }

    // 2. ДАННЫЕ ОКНА
    HWND foregroundHwnd = GetForegroundWindow();
    int isActive = (hwnd == foregroundHwnd) ? 1 : 0;

    int len = GetWindowTextLengthW(hwnd);
    std::wstring wtitle = L"";
    if (len > 0) {
        std::vector<wchar_t> titleBuf(len + 1);
        if (GetWindowTextW(hwnd, titleBuf.data(), (int)titleBuf.size())) {
            wtitle = titleBuf.data();
        }
    }
    if (wtitle.empty()) wtitle = wclsCheck;
    
    std::string procPathUtf8 = GetProcessPathFromHwndUtf8(hwnd);
    RECT rc = {0};
    if (FAILED(DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, &rc, sizeof(rc)))) {
        GetWindowRect(hwnd, &rc);
    }

    HMONITOR hMonitor = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST);
    MONITORINFO mi = { sizeof(mi) };
    int isFullscreen = 0;
    if (GetMonitorInfo(hMonitor, &mi)) {
        if (rc.left <= mi.rcMonitor.left && rc.top <= mi.rcMonitor.top && 
            rc.right >= mi.rcMonitor.right && rc.bottom >= mi.rcMonitor.bottom) {
            isFullscreen = 1;
        }
    }

    uintptr_t hid = reinterpret_cast<uintptr_t>(hwnd);
    std::string titleUtf8 = WideToUtf8(wtitle);
    std::string escTitle = EscapeForPyUtf8(titleUtf8);
    std::string escPath = EscapeForPyUtf8(procPathUtf8);

    // 3. ФОРМИРОВАНИЕ СЛОВАРЯ (Ключ: Значение)
    // Используем формат Python dict: {'key': value}
    std::string dictEntry = "{"
        "'active': " + std::to_string(isActive) + ", " +
        "'hwnd': " + std::to_string((unsigned long long)hid) + ", " +
        "'title': '" + escTitle + "', " +
        "'path': '" + escPath + "', " +
        "'type': '" + winType + "', " +
        "'rect': (" + std::to_string(rc.left) + ", " + std::to_string(rc.top) + ", " + std::to_string(rc.right) + ", " + std::to_string(rc.bottom) + "), " +
        "'full': " + std::to_string(isFullscreen) + ""
    "}";

    d->items->push_back(dictEntry);
    return TRUE;
}

int wmain(int argc, wchar_t* argv[])
{
    SetConsoleOutputCP(CP_UTF8);

    std::string filterUtf8;
    const std::string* filterPtr = nullptr;
    if (argc > 1) {
        filterUtf8 = WideToUtf8(std::wstring(argv[1]));
        filterPtr = &filterUtf8;
    }

    std::string lastOut = ""; // Хранилище предыдущего состояния

    while (true) {
        std::vector<std::string> items;
        EnumData data{ &items, filterPtr };
        EnumWindows(EnumWndProc, reinterpret_cast<LPARAM>(&data));

        // Сборка текущей строки JSON/Python list
        std::string currentOut = "[";
        for (size_t i = 0; i < items.size(); ++i) {
            currentOut += items[i];
            if (i + 1 < items.size()) currentOut += ", ";
        }
        currentOut += "]";

        // ВЫВОД ТОЛЬКО ПРИ НАЛИЧИИ ИЗМЕНЕНИЙ
        if (currentOut != lastOut) {
            std::cout << currentOut << std::endl;
            lastOut = currentOut; // Обновляем состояние
        }

        Sleep(100); // Пауза 0.5 сек, чтобы не грузить CPU
    }

    return 0;
}