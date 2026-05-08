#include <windows.h>
#include <iostream>
#include <string>
#include <vector>

// Функция для конвертации UTF-16 (WideChar) в UTF-8
std::string utf16_to_utf8(const std::wstring& wstr) {
    if (wstr.empty()) return std::string();
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, &wstr[0], (int)wstr.size(), NULL, 0, NULL, NULL);
    std::string strTo(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, &wstr[0], (int)wstr.size(), &strTo[0], size_needed, NULL, NULL);
    return strTo;
}

int main() {
    // Устанавливаем режим вывода, чтобы избежать лишних преобразований в консоли
    // Но для Python важнее просто поток байтов
    DWORD lastSequence = GetClipboardSequenceNumber();

    while (true) {
        DWORD currentSequence = GetClipboardSequenceNumber();
        
        if (currentSequence != lastSequence) {
            if (OpenClipboard(nullptr)) {
                // Используем CF_UNICODETEXT для поддержки всех языков
                if (IsClipboardFormatAvailable(CF_UNICODETEXT)) {
                    HANDLE hData = GetClipboardData(CF_UNICODETEXT);
                    if (hData != nullptr) {
                        wchar_t* pszText = static_cast<wchar_t*>(GlobalLock(hData));
                        if (pszText != nullptr) {
                            std::wstring wstr = pszText;
                            GlobalUnlock(hData);

                            // Конвертируем в UTF-8 и выводим
                            std::cout << utf16_to_utf8(wstr) << std::ends;

                            EmptyClipboard();
                            CloseClipboard();
                            return 0; // Выход после успешного получения
                        }
                    }
                }
                CloseClipboard();
            }
            lastSequence = currentSequence;
        }
        Sleep(50); 
    }
    return 0;
}
