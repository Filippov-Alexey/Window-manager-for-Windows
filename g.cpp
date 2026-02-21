#include <windows.h>
#include <stdio.h>

extern "C" __declspec(dllexport) LRESULT CALLBACK CallWndRetProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION) {
        CWPRETSTRUCT* pData = (CWPRETSTRUCT*)lParam;

        if (pData->message == 0x0051) { // WM_INPUTLANGCHANGE
            HKL hkl = (HKL)pData->lParam; 
            unsigned short langID = LOWORD(hkl); 
            
            char langName[128] = "Unknown";
            
            // Используем универсальный флаг LOCALE_SENGLISHLANGUAGENAME (0x00001001)
            if (GetLocaleInfoA(MAKELCID(langID, SORT_DEFAULT), 0x00001001, langName, sizeof(langName)) == 0) {
                sprintf_s(langName, "UnknownCode");
            }

            char buf[256];
            // Там, где данные записываются в буфер перед отправкой в пайп:
sprintf_s(buf, "\"Name\": \"%s\", \"HKL\": \"0x%p\", \"ID\": \"0x%04x\"", langName, hkl, langID);

            HANDLE hPipe = CreateFileA("\\\\.\\pipe\\LangHookPipe", GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
            if (hPipe != INVALID_HANDLE_VALUE) {
                DWORD written;
                WriteFile(hPipe, buf, (DWORD)strlen(buf), &written, NULL);
                CloseHandle(hPipe);
            }
        }
    }
    return CallNextHookEx(NULL, nCode, wParam, lParam);
}
