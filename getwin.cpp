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

static bool IsWindowSkippable(HWND hwnd)
{
    if (!IsWindowVisible(hwnd)) return true;
    BOOL cloaked = FALSE;
    if (SUCCEEDED(DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, &cloaked, sizeof(cloaked))) && cloaked)
        return true;
    if (GetWindow(hwnd, GW_OWNER) != NULL) return true;
    LONG_PTR ex = GetWindowLongPtr(hwnd, GWL_EXSTYLE);
    if (ex & WS_EX_TOOLWINDOW) return true;
    return false;
}

struct EnumData {
    std::vector<std::string>* items;
    const std::string* filter; // nullptr если без фильтра
};
static BOOL CALLBACK EnumWndProc(HWND hwnd, LPARAM lParam)
{
    EnumData* d = reinterpret_cast<EnumData*>(lParam);
    if (!d || !d->items) return TRUE;
    if (IsWindowSkippable(hwnd)) return TRUE;

    int len = GetWindowTextLengthW(hwnd);
    if (len <= 0) return TRUE;

    std::vector<wchar_t> titleBuf(len + 1);
    if (GetWindowTextW(hwnd, titleBuf.data(), static_cast<int>(titleBuf.size())) == 0) return TRUE;
    std::wstring wtitle(titleBuf.data());
    std::string titleUtf8 = WideToUtf8(wtitle);

    std::string procPathUtf8 = GetProcessPathFromHwndUtf8(hwnd);
    if (d->filter && !d->filter->empty()) {
        std::string filter = *d->filter;

        // Привести пути к нижнему регистру для нечувствительной фильтрации
        std::transform(procPathUtf8.begin(), procPathUtf8.end(), procPathUtf8.begin(), ::tolower);
        std::transform(filter.begin(), filter.end(), filter.begin(), ::tolower);

        if (procPathUtf8.find(filter) == std::string::npos) return TRUE; // Пропускаем, если не соответствует фильтру
    }

    RECT rc = {};
    RECT ext = {};
    if (SUCCEEDED(DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, &ext, sizeof(ext))))
        rc = ext;
    else if (!GetWindowRect(hwnd, &rc))
        return TRUE;

    int width = rc.right - rc.left;
    int height = rc.bottom - rc.top;
    if (width <= 0 || height <= 0) return TRUE;

    uintptr_t hid = reinterpret_cast<uintptr_t>(hwnd);

    std::string escTitle = EscapeForPyUtf8(titleUtf8);
    std::string escPath = EscapeForPyUtf8(procPathUtf8);

    std::string tuple;
    tuple.reserve(256);
    tuple += "(";
    tuple += std::to_string((unsigned long long)hid);
    tuple += ", '";
    tuple += escTitle;
    tuple += "', '";
    tuple += escPath;
    tuple += "', (";
    tuple += std::to_string(rc.left);
    tuple += ", ";
    tuple += std::to_string(rc.top);
    tuple += ", ";
    tuple += std::to_string(rc.right);
    tuple += ", ";
    tuple += std::to_string(rc.bottom);
    tuple += "))";

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