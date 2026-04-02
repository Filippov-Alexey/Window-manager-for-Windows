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
static bool IsWindowSkippable(HWND hwnd)
{
    if (!IsWindowVisible(hwnd)) return true;

    // Проверка, не скрыто ли окно оболочкой (Cloaked)
    int cloaked = 0;
    if (SUCCEEDED(DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, &cloaked, sizeof(cloaked)))) {
        if (cloaked != 0) return true; 
    }

    RECT rc;
    GetWindowRect(hwnd, &rc);
    if ((rc.right - rc.left) <= 0 || (rc.bottom - rc.top) <= 0) return true;

    // Проверка на ToolWindow (плавающие панели, которые не должны быть в списке)
    if (GetWindowLong(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW) return true;

    return false; 
}

static BOOL CALLBACK EnumWndProc(HWND hwnd, LPARAM lParam)
{
    if (IsWindowSkippable(hwnd)) return TRUE; // Пропускаем мусор
    // ... остальной код
    EnumData* d = reinterpret_cast<EnumData*>(lParam);

    wchar_t clsBuf[256] = {0};
    GetClassNameW(hwnd, clsBuf, 256);
    std::wstring wcls(clsBuf);

    int len = GetWindowTextLengthW(hwnd);
    std::wstring wtitle = L"";
    if (len > 0) {
        std::vector<wchar_t> titleBuf(len + 1);
        if (GetWindowTextW(hwnd, titleBuf.data(), static_cast<int>(titleBuf.size()))) {
            wtitle = titleBuf.data();
        }
    }

    if (wtitle.empty()) {
        wtitle = L"[" + wcls + L"]";
    }

    std::string procPathUtf8 = GetProcessPathFromHwndUtf8(hwnd);

    RECT rc = {0};
    if (FAILED(DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, &rc, sizeof(rc)))) {
        GetWindowRect(hwnd, &rc);
    }

    uintptr_t hid = reinterpret_cast<uintptr_t>(hwnd);
    std::string titleUtf8 = WideToUtf8(wtitle);
    std::string escTitle = EscapeForPyUtf8(titleUtf8);
    std::string escPath = EscapeForPyUtf8(procPathUtf8);

    std::string tuple = "(" + std::to_string((unsigned long long)hid) + 
                       ", '" + escTitle + "', '" + escPath + "', (" +
                       std::to_string(rc.left) + ", " + std::to_string(rc.top) + ", " +
                       std::to_string(rc.right) + ", " + std::to_string(rc.bottom) + "))";

    d->items->push_back(tuple);
    return TRUE;
}

int wmain(int argc, wchar_t* argv[])
{
    std::string filterUtf8;
    const std::string* filterPtr = nullptr;
    if (argc > 1) {
        filterUtf8 = WideToUtf8(std::wstring(argv[1]));
        filterPtr = &filterUtf8;
    }

    std::vector<std::string> items;
    EnumData data{ &items, filterPtr };
    EnumWindows(EnumWndProc, reinterpret_cast<LPARAM>(&data));

    std::string out = "[";
    for (size_t i = 0; i < items.size(); ++i) {
        out += items[i];
        if (i + 1 < items.size()) out += ", ";
    }
    out += "]";

    SetConsoleOutputCP(CP_UTF8);
    std::cout << out << std::endl;
    return 0;
}