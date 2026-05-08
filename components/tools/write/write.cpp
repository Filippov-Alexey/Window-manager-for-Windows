#include <windows.h>
#include <string>
#include <shellapi.h>

// Автоматическое подключение нужных библиотек для линкера
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "shell32.lib")

void SendKey(WORD vk) {
    INPUT input = {0};
    input.type = INPUT_KEYBOARD;
    input.ki.wVk = vk;
    SendInput(1, &input, sizeof(INPUT));
    input.ki.dwFlags = KEYEVENTF_KEYUP;
    SendInput(1, &input, sizeof(INPUT));
}

void SendString(const std::wstring& str) {
    for (wchar_t ch : str) {
        if (ch == L'\xf9') {
            SendKey(VK_RETURN);
        } else if (ch == L'\xf8') {
            SendKey(VK_TAB);
        } else {
            INPUT input = {0};
            input.type = INPUT_KEYBOARD;
            input.ki.dwFlags = KEYEVENTF_UNICODE;
            input.ki.wScan = ch;
            SendInput(1, &input, sizeof(INPUT));
            input.ki.dwFlags |= KEYEVENTF_KEYUP;
            SendInput(1, &input, sizeof(INPUT));
        }
    }
}

int main() {
    int argc;
    // Получаем аргументы командной строки в Unicode
    LPWSTR* argvW = CommandLineToArgvW(GetCommandLineW(), &argc);
    
    if (argvW == NULL || argc < 2) {
        if (argvW) LocalFree(argvW);
        return 1;
    }

    // Аргумент [1] — это текст сообщения
    std::wstring message = argvW[1];

    // Пауза 2 секунды перед началом ввода
    // Sleep(2000);
    SendString(message);

    return 0;
}
