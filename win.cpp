
#include <windows.h>
#include <string>
#include <iostream>
#include <cctype>
#include <cstdlib>
#include <cstdio>
#include <thread>
#include <conio.h>

static HHOOK g_hCbt = NULL;
static HHOOK g_hCall = NULL;
static HMODULE g_hDll = NULL;
static const char* PIPE_NAME = "\\\\.\\pipe\\HookLogger";

void PrintLastError(const char* msgPrefix)
{
    DWORD err = GetLastError();
    if (err == 0)
    {
        std::cout << msgPrefix << ": (no error)\n";
        return;
    }
    LPSTR buf = nullptr;
    FormatMessageA(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
                   nullptr, err, MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), (LPSTR)&buf, 0, nullptr);
    if (buf)
    {
        std::cout << msgPrefix << ": (" << err << ") " << buf;
        LocalFree(buf);
    }
    else
    {
        std::cout << msgPrefix << ": error code " << err << "\n";
    }
}

static void PrintUtf8(const std::string &utf8)
{
    HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
    if (hOut != INVALID_HANDLE_VALUE)
    {
        DWORD mode;
        // Если стандартный вывод — реальная консоль, используем WriteConsoleW для корректного отображения Unicode
        if (GetConsoleMode(hOut, &mode))
        {
            int wideLen = MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), (int)utf8.size(), NULL, 0);
            if (wideLen > 0)
            {
                std::wstring w;
                w.resize(wideLen);
                MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), (int)utf8.size(), &w[0], wideLen);
                DWORD written = 0;
                WriteConsoleW(hOut, w.c_str(), (DWORD)w.size(), &written, NULL);
                return;
            }
        }
    }
    // Если не консоль (перенаправление/pipe) или WriteConsoleW не удался — просто выводим UTF-8 байты
    std::cout << utf8;
}

void PipeClientThread(HANDLE hPipe)
{
    const DWORD bufSize = 8192;
    char buffer[bufSize];
    std::string partial;
    DWORD bytesRead = 0;

    auto getWindowTitle = [](unsigned long long val) -> std::string {
        HWND hWnd = (HWND)(uintptr_t)val;
        if (!IsWindow(hWnd)) return std::string();

        const int MAXT = 1024;
        wchar_t wbuf[MAXT];
        int len = GetWindowTextW(hWnd, wbuf, MAXT);
        if (len <= 0) return std::string();

        int outLen = WideCharToMultiByte(CP_UTF8, 0, wbuf, len, NULL, 0, NULL, NULL);
        if (outLen <= 0) return std::string();
        std::string out;
        out.resize(outLen);
        WideCharToMultiByte(CP_UTF8, 0, wbuf, len, &out[0], outLen, NULL, NULL);
        for (char &c : out) { if (c == '\n' || c == '\r') c = ' '; if (c == '"') c = '\''; }
        return out;
    };

    auto convertHwndToDecimalAndAttachTitle = [&](std::string &line) {
        size_t pos = 0;
        while (true)
        {
            pos = line.find("hwnd=", pos);
            if (pos == std::string::npos) break;
            size_t start = pos + 5;
            if (start >= line.size()) break;

            size_t i = start;
            unsigned long long val = 0;
            size_t len = 0;
            if (i + 1 < line.size() && line[i] == '0' && (line[i+1] == 'x' || line[i+1] == 'X'))
            {
                size_t j = i + 2;
                while (j < line.size() && std::isxdigit(static_cast<unsigned char>(line[j]))) ++j;
                if (j <= i + 2) { pos = start; continue; }
                len = j - start;
                std::string numstr = line.substr(start, len);
                val = _strtoui64(numstr.c_str(), NULL, 0);
            }
            else
            {
                size_t j = i;
                while (j < line.size() && std::isdigit(static_cast<unsigned char>(line[j]))) ++j;
                if (j == i) { pos = start; continue; } // нет цифр
                len = j - start;
                std::string numstr = line.substr(start, len);
                val = _strtoui64(numstr.c_str(), NULL, 10);
            }

            char decbuf[32];
            _ui64toa_s(val, decbuf, sizeof(decbuf), 10);
            std::string dec(decbuf);

            line.replace(start, len, dec);

            std::string title = getWindowTitle(val);
            if (title.empty())
            {
                pos = start + dec.size();
            }
            else
            {
                std::string insert = ", title=";
                insert += title;
                line.insert(start + dec.size(), insert);
                pos = start + dec.size() + insert.size();
            }
        }
    };

    while (true)
    {
        BOOL ok = ReadFile(hPipe, buffer, bufSize - 1, &bytesRead, NULL);
        if (!ok || bytesRead == 0) break;

        partial.append(buffer, buffer + bytesRead);

        size_t pos;
        while ((pos = partial.find('\n')) != std::string::npos)
        {
            std::string line = partial.substr(0, pos + 1);
            partial.erase(0, pos + 1);

            if (line.find("CBTProc") != std::string::npos)
            {
                convertHwndToDecimalAndAttachTitle(line);
                PrintUtf8( line);
                std::cout.flush();
            }
        }
    }

    if (!partial.empty() && partial.find("CBTProc") != std::string::npos)
    {
        convertHwndToDecimalAndAttachTitle(partial);
        std::cout << "[HOOK0] " << partial << std::endl;
    }

    DisconnectNamedPipe(hPipe);
    CloseHandle(hPipe);
}

void PipeServerThread()
{
    while (true)
    {
        HANDLE hPipe = CreateNamedPipeA(
            PIPE_NAME,
            PIPE_ACCESS_INBOUND,PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
            PIPE_UNLIMITED_INSTANCES,
            8192, 8192, 0, NULL);

        if (hPipe == INVALID_HANDLE_VALUE)
        {
            PrintLastError("CreateNamedPipe failed");
            return;
        }

        BOOL connected = ConnectNamedPipe(hPipe, NULL) ? TRUE : (GetLastError() == ERROR_PIPE_CONNECTED);
        if (connected)
        {
            std::thread(PipeClientThread, hPipe).detach();
        }
        else
        {
            CloseHandle(hPipe);
        }
    }
}

int main()
{
    const char* dllName = "hookdll.dll";
    std::thread(PipeServerThread).detach();

    g_hDll = LoadLibraryA(dllName);
    if (!g_hDll) { PrintLastError("LoadLibrary failed"); return 1; }

    auto cbtProc = reinterpret_cast<HOOKPROC>(GetProcAddress(g_hDll, "CBTProc"));
    auto callProc = reinterpret_cast<HOOKPROC>(GetProcAddress(g_hDll, "CallWndProc"));
    if (!cbtProc || !callProc) { std::cout << "GetProcAddress failed\n"; FreeLibrary(g_hDll); return 1; }

    g_hCbt = SetWindowsHookExA(WH_CBT, cbtProc, g_hDll, 0);
    // if (!g_hCbt) PrintLastError("SetWindowsHookEx(WH_CBT) failed"); else std::cout << "WH_CBT hooked\n";

    g_hCall = SetWindowsHookExA(WH_CALLWNDPROC, callProc, g_hDll, 0);
    // if (!g_hCall) PrintLastError("SetWindowsHookEx(WH_CALLWNDPROC) failed"); else std::cout << "WH_CALLWNDPROC hooked\n";

    if (!g_hCbt || !g_hCall)
    {
        if (g_hCbt) UnhookWindowsHookEx(g_hCbt);
        if (g_hCall) UnhookWindowsHookEx(g_hCall);
        FreeLibrary(g_hDll);
        return 1;
    }

    // std::cout << "Hooks installed. Press Enter to uninstall and exit...\n";

    while (true)
    {
        if (_kbhit())
        {
            int c = _getch();
            if (c == '\r' || c == '\n') break;
        }
        Sleep(50);
    }

    if (g_hCbt) UnhookWindowsHookEx(g_hCbt);
    if (g_hCall) UnhookWindowsHookEx(g_hCall);
    if (g_hDll) FreeLibrary(g_hDll);
    // std::cout << "Exiting.\n";
    return 0;
}