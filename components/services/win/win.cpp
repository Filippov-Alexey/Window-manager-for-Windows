#include <windows.h>
#include <string>
#include <iostream>
#include <cctype>
#include <cstdlib>
#include <cstdio>
#include <thread>
#include <conio.h>
#include <vector>

typedef void (*SetSWBlockedFn)(int, BOOL);
static HHOOK g_hCbt = NULL;
static HHOOK g_hCall = NULL;
static HMODULE g_hDll = NULL;
static const char* PIPE_NAME = "\\\\.\\pipe\\HookLogger";

void PrintUtf8(const std::string &utf8)
{
    HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
    if (hOut != INVALID_HANDLE_VALUE) {
        DWORD mode;
        if (GetConsoleMode(hOut, &mode)) {
            int wideLen = MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), (int)utf8.size(), NULL, 0);
            if (wideLen > 0) {
                std::wstring w(wideLen, 0);
                MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), (int)utf8.size(), &w[0], wideLen);
                DWORD written = 0;
                WriteConsoleW(hOut, w.c_str(), (DWORD)w.size(), &written, NULL);
                fflush(stdout); // ИСПРАВЛЕНО: Гарантирует мгновенную отправку в Python
                return;
            }
        }
    }
    std::cout << utf8;
    std::cout.flush(); // ИСПРАВЛЕНО: Резервный сброс буфера
    fflush(stdout);    // ИСПРАВЛЕНО
}

void PipeClientThread(HANDLE hPipe)
{
    const DWORD bufSize = 8192;
    char buffer[bufSize];
    std::string partial;
    DWORD bytesRead = 0;

    auto getWindowTitle = [](HWND hWnd) -> std::string {
        if (!IsWindow(hWnd)) return "None";
        wchar_t wbuf[1024];
        int len = GetWindowTextW(hWnd, wbuf, 1024);
        if (len <= 0) return "None";
        int outLen = WideCharToMultiByte(CP_UTF8, 0, wbuf, len, NULL, 0, NULL, NULL);
        if (outLen <= 0) return "None";
        std::string out(outLen, 0);
        WideCharToMultiByte(CP_UTF8, 0, wbuf, len, &out[0], outLen, NULL, NULL);
        for (char &c : out) { if (c == '\n' || c == '\r') c = ' '; if (c == '"') c = '\''; }
        return out;
    };

    auto processLogLine = [&](const std::string& line) {
        if (line.empty()) return;
        
        std::vector<std::string> tokens;
        size_t start = 0, end = 0;
        while ((end = line.find('|', start)) != std::string::npos) {
            tokens.push_back(line.substr(start, end - start));
            start = end + 1;
        }
        tokens.push_back(line.substr(start));
        if (tokens.size() < 3) return;

        std::string opCode   = tokens[0];
        std::string name     = tokens[1];
        std::string hwndHex  = tokens[2];

        while(!hwndHex.empty() && (hwndHex.back() == '\n' || hwndHex.back() == '\r')) {
            hwndHex.pop_back();
        }

        unsigned long long hwndVal = _strtoui64(hwndHex.c_str(), NULL, 16);
        char decbuf[32];
        _ui64toa_s(hwndVal, decbuf, sizeof(decbuf), 10);

        std::string title = getWindowTitle((HWND)(uintptr_t)hwndVal);

        // Чистый JSON-вывод с английскими ключами и сквозными кодами 0-15
        std::string output = "{code:" + opCode + 
                             ", name:\"" + name + "\"" +
                             ", title:\"" + title + "\"" + 
                             ", hwnd:" + decbuf + "}\n";
        PrintUtf8(output);
    };

    while (ReadFile(hPipe, buffer, bufSize - 1, &bytesRead, NULL) && bytesRead > 0) {
        partial.append(buffer, bytesRead);
        size_t pos;
        while ((pos = partial.find('\n')) != std::string::npos) {
            processLogLine(partial.substr(0, pos + 1));
            partial.erase(0, pos + 1);
        }
    }
    DisconnectNamedPipe(hPipe);
    CloseHandle(hPipe);
}

void PipeServerThread()
{
    while (true) {
        HANDLE hPipe = CreateNamedPipeA(PIPE_NAME, PIPE_ACCESS_INBOUND, PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT, PIPE_UNLIMITED_INSTANCES, 8192, 8192, 0, NULL);
        if (hPipe == INVALID_HANDLE_VALUE) { Sleep(1000); continue; }
        if (ConnectNamedPipe(hPipe, NULL) || GetLastError() == ERROR_PIPE_CONNECTED) {
            std::thread(PipeClientThread, hPipe).detach();
        } else {
            CloseHandle(hPipe);
        }
    }
}

int main(int argc, char* argv[])
{
    std::thread(PipeServerThread).detach();
    Sleep(50);

    g_hDll = LoadLibraryA("hookdll.dll");
    if (!g_hDll) return 1;

    auto setSWBlocked = reinterpret_cast<SetSWBlockedFn>(GetProcAddress(g_hDll, "SetSWBlocked"));
    auto cbtProc = reinterpret_cast<HOOKPROC>(GetProcAddress(g_hDll, "CBTProc"));
    auto callProc = reinterpret_cast<HOOKPROC>(GetProcAddress(g_hDll, "CallWndProc"));
    if (!setSWBlocked || !cbtProc || !callProc) return 1;

    if (argc > 1) {
        for (int i = 1; i < argc; ++i) {
            int code = std::atoi(argv[i]);
            setSWBlocked(code, TRUE);
        }
    }

    g_hCbt = SetWindowsHookExA(WH_CBT, cbtProc, g_hDll, 0);
    g_hCall = SetWindowsHookExA(WH_CALLWNDPROC, callProc, g_hDll, 0);
    
    while (true) {
        if (_kbhit()) { int c = _getch(); if (c == '\r' || c == '\n') break; }
        Sleep(50);
    }

    if (g_hCbt) UnhookWindowsHookEx(g_hCbt);
    if (g_hCall) UnhookWindowsHookEx(g_hCall);
    FreeLibrary(g_hDll);
    return 0;
}
