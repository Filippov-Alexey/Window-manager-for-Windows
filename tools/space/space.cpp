#include <windows.h>
#include <string>
#include <vector>
#include <iostream>

struct AnchorInfo {
    HWND hwnd;
    std::wstring title;
    long lastX;
    long lastY;
};

// Функция поиска значения аргумента
std::wstring GetArgValue(int argc, wchar_t* argv[], const std::wstring& key) {
    for (int i = 1; i < argc - 1; ++i) {
        if (std::wstring(argv[i]) == key) {
            return argv[i + 1];
        }
    }
    return L"";
}

LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam) {
    if (message == WM_DESTROY) { PostQuitMessage(0); return 0; }
    return DefWindowProcW(hWnd, message, wParam, lParam);
}

AnchorInfo CreateInvisibleAnchor(int id, int x, int y) {
    HINSTANCE hInstance = GetModuleHandle(NULL);
    std::wstring title = L"desktop_space_" + std::to_wstring(id);
    const wchar_t CLASS_NAME[] = L"InvisibleAnchorClass";

    WNDCLASSW wc = { 0 };
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = CLASS_NAME;
    RegisterClassW(&wc);

    HWND hwnd = CreateWindowExW(
        WS_EX_TOOLWINDOW | WS_EX_LAYERED | WS_EX_TRANSPARENT,
        CLASS_NAME, title.c_str(),
        WS_POPUP | WS_VISIBLE,
        x, y, 0, 0,
        NULL, NULL, hInstance, NULL
    );

    SetLayeredWindowAttributes(hwnd, 0, 0, LWA_ALPHA);
    return { hwnd, title, -20000, -20000 }; 
}

int wmain(int argc, wchar_t* argv[]) {
    SetConsoleOutputCP(65001);
    int count = 3;
    int stepX = 5000;
    int stepY = 0;

    std::wstring val;
    if (!(val = GetArgValue(argc, argv, L"/space")).empty())    count = std::stoi(val);
    if (!(val = GetArgValue(argc, argv, L"/x")).empty())        stepX = std::stoi(val);
    if (!(val = GetArgValue(argc, argv, L"/y")).empty())        stepY = std::stoi(val);

    std::vector<AnchorInfo> anchors;
    for (int i = 0; i < count; ++i) {
        int posX = i * stepX;
        int posY = i * stepY;
        anchors.push_back(CreateInvisibleAnchor(i + 1, posX, posY));
    }

    std::wcout << L"Count: " << count << L" | Interval X: " << stepX << L", Y: " << stepY << std::endl;

    MSG msg = { 0 };

    while (msg.message != WM_QUIT) {
        if (PeekMessageW(&msg, NULL, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }

        bool changed = false;
        std::wstring currentSnapshot = L"[";

        for (size_t i = 0; i < anchors.size(); ++i) {
            RECT rect;
            if (GetWindowRect(anchors[i].hwnd, &rect)) {
                if (rect.left != anchors[i].lastX || rect.top != anchors[i].lastY) {
                    anchors[i].lastX = rect.left;
                    anchors[i].lastY = rect.top;
                    changed = true;
                }
                // Формируем кортеж: (HWND, "название", (x, y))
                currentSnapshot += L"(" + std::to_wstring((unsigned long long)anchors[i].hwnd) + 
                                   L", 'desktop_space_" + std::to_wstring(i+1) + 
                                   L"', (" + std::to_wstring(anchors[i].lastX) + 
                                   L", " + std::to_wstring(anchors[i].lastY) + L"))";
                if (i + 1 < anchors.size()) currentSnapshot += L", ";
            }
        }
        currentSnapshot += L"]";

        if (changed) {
            // Выводим в stdout
            std::wcout << currentSnapshot << std::endl;
            std::wcout.flush(); // ОБЯЗАТЕЛЬНО для readline() в Python
        }
        Sleep(50);
    }
    return 0;
}