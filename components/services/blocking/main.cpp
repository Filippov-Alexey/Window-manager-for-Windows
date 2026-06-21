#include <windows.h>
#include <tlhelp32.h>
#include <iostream>
#include <thread>
#include <filesystem>
#include "KeyDictionary.h"
#include "HotkeyManager.h"
#include "LanguageMonitor.h"
#include "KeyboardHook.h"

namespace fs = std::filesystem;

fs::path GetExecutableDir() {
    wchar_t path[MAX_PATH];
    GetModuleFileNameW(NULL, path, MAX_PATH);
    return fs::path(path).parent_path();
}

void TerminateOtherInstances(const std::wstring& processName) {
    DWORD currentPID = GetCurrentProcessId();
    // Ограничение работы бесконечного цикла, чтобы не нагружать ядро
    while (true) {
        HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if (hSnap != INVALID_HANDLE_VALUE) {
            PROCESSENTRY32W pe{.dwSize = sizeof(PROCESSENTRY32W)};
            if (Process32FirstW(hSnap, &pe)) {
                do {
                    if (_wcsicmp(pe.szExeFile, processName.c_str()) == 0 && pe.th32ProcessID != currentPID) {
                        HANDLE hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, pe.th32ProcessID);
                        if (hProcess) {
                            TerminateProcess(hProcess, 0);
                            CloseHandle(hProcess);
                        }
                    }
                } while (Process32NextW(hSnap, &pe));
            }
            CloseHandle(hSnap);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    }
}

int main(int argc, char* argv[]) {
    KeyDictionary dict;
    HotkeyManager hm;
    LanguageMonitor lm;

    hm.parseArguments(argc, argv);
    if (!dict.loadFromFile(GetExecutableDir(), "key_code.txt")) {
        return 1;
    }
    lm.updateInitialLanguage();

    SetConsoleOutputCP(CP_UTF8);

    std::thread(TerminateOtherInstances, L"blocking.exe").detach();
    std::thread(&LanguageMonitor::startPipeListener, &lm).detach();

    KeyboardHook::initialize(&dict, &hm, &lm);
    HHOOK keyboardHook = SetWindowsHookEx(WH_KEYBOARD_LL, KeyboardHook::hookCallback, NULL, 0);
    if (!keyboardHook) {
        std::cerr << "Failed to install hook!" << std::endl;
        return 1;
    }

    HMODULE hDll = LoadLibrary(TEXT("g.dll"));
    HHOOK hHook = nullptr;
    if (hDll) {
        HOOKPROC proc = (HOOKPROC)GetProcAddress(hDll, "CallWndRetProc");
        if (proc) {
            hHook = SetWindowsHookEx(12, proc, hDll, 0);
        }
    }

    MSG msg;
    while (GetMessage(&msg, nullptr, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    UnhookWindowsHookEx(keyboardHook);
    if (hHook) UnhookWindowsHookEx(hHook);
    return 0;
}
