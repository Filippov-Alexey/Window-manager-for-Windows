#include <windows.h>
#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    // Проверка наличия аргументов
    if (argc < 3) {
        std::cout << "Usage: layout.exe <hwnd> <hkl>" << std::endl;
        std::cout << "Example: layout.exe 1575516 0x04190419" << std::endl;
        return 1;
    }

    try {
        // Парсим HWND. Если это 1575516, stoull поймет его как десятичное.
        // Если передадите 0x..., он поймет его как HEX.
        unsigned long long raw_hwnd = std::stoull(argv[1], nullptr, 0);
        HWND hwnd = reinterpret_cast<HWND>(raw_hwnd);

        // Парсим HKL (раскладку). Параметр 0 позволяет автоматически определить 
        // десятичный формат или HEX (если есть префикс 0x).
        LPARAM hkl = static_cast<LPARAM>(std::stoull(argv[2], nullptr, 0));

        if (IsWindow(hwnd)) {
            // Отправляем сообщение окну
            if (PostMessage(hwnd, WM_INPUTLANGCHANGEREQUEST, 0, hkl)) {
                std::cout << "Success: Layout change request sent to HWND " << raw_hwnd << std::endl;
            } else {
                std::cerr << "Error: PostMessage failed. Code: " << GetLastError() << std::endl;
            }
        } else {
            std::cerr << "Error: Window with HWND " << raw_hwnd << " not found!" << std::endl;
            return 1;
        }

    } catch (const std::exception& e) {
        std::cerr << "Parsing error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
