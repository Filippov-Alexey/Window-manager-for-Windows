#include "LanguageMonitor.h"
#include <msctf.h>
#include <iostream>

LanguageMonitor::LanguageMonitor() : _running(true) {}
LanguageMonitor::~LanguageMonitor() { _running = false; }

void LanguageMonitor::startPipeListener() {
    while (_running) {
        HANDLE hPipe = CreateNamedPipeA("\\\\.\\pipe\\LangHookPipe", 
            PIPE_ACCESS_INBOUND, PIPE_TYPE_BYTE | PIPE_WAIT, 1, 1024, 1024, 0, NULL);
        if (hPipe != INVALID_HANDLE_VALUE) {
            if (ConnectNamedPipe(hPipe, NULL) || GetLastError() == ERROR_PIPE_CONNECTED) {
                char buffer[256];
                DWORD read;
                if (ReadFile(hPipe, buffer, sizeof(buffer) - 1, &read, NULL)) {
                    buffer[read] = '\0';
                    std::lock_guard<std::mutex> lock(_mutex);
                    _currentInfo = buffer;
                }
            }
            DisconnectNamedPipe(hPipe);
            CloseHandle(hPipe);
        }
        Sleep(10); // Снижение нагрузки на процессор
    }
}

void LanguageMonitor::updateInitialLanguage() {
    if (FAILED(CoInitializeEx(NULL, COINIT_APARTMENTTHREADED))) return;
    
    ITfInputProcessorProfiles* pProfiles = nullptr;
    if (SUCCEEDED(CoCreateInstance(CLSID_TF_InputProcessorProfiles, NULL, CLSCTX_INPROC_SERVER, IID_ITfInputProcessorProfiles, (void**)&pProfiles))) {
        LANGID langId = 0;
        if (SUCCEEDED(pProfiles->GetCurrentLanguage(&langId))) {
            char langName[LOCALE_NAME_MAX_LENGTH] = {0};
            char buf[512];
            GetLocaleInfoA(MAKELCID(langId, SORT_DEFAULT), 0x1001, langName, sizeof(langName));
            HKL hkl = GetKeyboardLayout(0);
            sprintf_s(buf, "\"Name\": \"%s\", \"HKL\": \"0x%p\", \"ID\": \"0x%04x\"", langName, (void*)hkl, langId);
            
            std::lock_guard<std::mutex> lock(_mutex);
            _currentInfo = buf;
        }
        pProfiles->Release();
    }
    CoUninitialize();
}

std::string LanguageMonitor::getCurrentInfo() {
    std::lock_guard<std::mutex> lock(_mutex);
    return _currentInfo;
}
