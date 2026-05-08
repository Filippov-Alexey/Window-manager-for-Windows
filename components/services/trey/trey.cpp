#include <dwmapi.h>
#pragma comment(lib, "dwmapi.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "shell32.lib")
#include <windows.h>
#include <commctrl.h>
#include <vector>

#define IDT_REFRESH_TIMER 5001

struct TRAYDATA {
    HWND hwnd;
    UINT uID;
    UINT uCallbackMessage;
    DWORD reserved[2]; // Смещение может зависеть от версии Windows
    HICON hIcon;       // Иконка лежит здесь
};

struct TrayApp {
    HWND targetHwnd;
    UINT msg;
    UINT iconID;
    HICON hIcon;
};

std::vector<TrayApp> g_apps;
std::vector<HWND> g_btnWnds;

void ClearButtons() {
    for (HWND hBtn : g_btnWnds) DestroyWindow(hBtn);
    g_btnWnds.clear();
    g_apps.clear();
}

void ScanTray(HWND hToolbar, HANDLE hProcess, void* pRemoteBtn) {
    if (!hToolbar) return;

    int count = (int)SendMessageW(hToolbar, TB_BUTTONCOUNT, 0, 0);
    for (int i = 0; i < count; i++) {
        TBBUTTON btn = { 0 };
        SendMessageW(hToolbar, TB_GETBUTTON, i, (LPARAM)pRemoteBtn);
        ReadProcessMemory(hProcess, pRemoteBtn, &btn, sizeof(TBBUTTON), NULL);

        if (btn.fsState & TBSTATE_HIDDEN) continue;

        TRAYDATA data = { 0 };
        ReadProcessMemory(hProcess, (LPCVOID)btn.dwData, &data, sizeof(TRAYDATA), NULL);

        if (data.hwnd != NULL && data.hIcon != NULL) {
            g_apps.push_back({ data.hwnd, data.uCallbackMessage, data.uID, data.hIcon });
        }
    }
}


void SendTrayClick(size_t idx, UINT mouseMsg) {
    if (idx >= g_apps.size()) return;
    TrayApp& app = g_apps[idx];
    AllowSetForegroundWindow(ASFW_ANY);
    SetForegroundWindow(app.targetHwnd);
    
    WPARAM wp = (WPARAM)app.iconID;
    PostMessageW(app.targetHwnd, app.msg, wp, (mouseMsg == WM_RBUTTONUP) ? WM_RBUTTONDOWN : WM_LBUTTONDOWN);
    PostMessageW(app.targetHwnd, app.msg, wp, mouseMsg);
}

#include <shellapi.h> // Обязательно для CommandLineToArgvW
void RefreshList(HWND hWnd, HINSTANCE hInst) {
    ClearButtons(); 
    HWND hShell = FindWindowW(L"Shell_TrayWnd", NULL);
    HWND hNotify = FindWindowExW(hShell, NULL, L"TrayNotifyWnd", NULL);
    HWND hPager = FindWindowExW(hNotify, NULL, L"SysPager", NULL);
    HWND hMainTray = FindWindowExW(hPager, NULL, L"ToolbarWindow32", NULL);
    HWND hOverflow = FindWindowExW(FindWindowW(L"NotifyIconOverflowWindow", NULL), NULL, L"ToolbarWindow32", NULL);
    
    DWORD pid;
    GetWindowThreadProcessId(hMainTray, &pid);
    HANDLE hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid);
    if (!hProcess) return;

    void* pRemoteBtn = VirtualAllocEx(hProcess, NULL, sizeof(TBBUTTON), MEM_COMMIT, PAGE_READWRITE);
    
    ScanTray(hMainTray, hProcess, pRemoteBtn);
    ScanTray(hOverflow, hProcess, pRemoteBtn);
    
    const int ICON_SIZE = 40;
    const int MARGIN = 10;
    const int SPACING = 5;
    const int STEP = ICON_SIZE + SPACING;
    
    RECT clientRect;
    GetClientRect(hWnd, &clientRect);
    int currentClientW = clientRect.right - clientRect.left;
    
    int availableW = currentClientW - (MARGIN * 2);
    
    int cols = (availableW + SPACING) / STEP;
    if (cols <= 0) cols = 1;
    int totalApps = (int)g_apps.size();
    if (totalApps == 0) return;
    
    int rows = (totalApps + cols - 1) / cols;

    int targetClientH = (rows * STEP) - SPACING + (MARGIN * 2);
    
    int x = MARGIN, y = MARGIN;
for (size_t i = 0; i < g_apps.size(); i++) {
    // Используем WS_EX_TRANSPARENT, чтобы кнопка не рисовала свой фон поверх окна
    HWND hBtn = CreateWindowExW(WS_EX_TRANSPARENT, L"BUTTON", L"", 
        WS_VISIBLE | WS_CHILD | BS_ICON | BS_FLAT, // BS_FLAT убирает 3D рамку
        x, y, ICON_SIZE, ICON_SIZE, hWnd, (HMENU)i, hInst, NULL);
    
    SendMessageW(hBtn, BM_SETIMAGE, IMAGE_ICON, (LPARAM)g_apps[i].hIcon);
    g_btnWnds.push_back(hBtn);

    x += STEP;
    if ((i + 1) % cols == 0) { 
        x = MARGIN; 
        y += STEP; 
    }
}
    
    RECT wr = { 0, 0, currentClientW, targetClientH };
    AdjustWindowRectEx(&wr, GetWindowLong(hWnd, GWL_STYLE), FALSE, GetWindowLong(hWnd, GWL_EXSTYLE));
    SetWindowPos(hWnd, NULL, 0, 0, currentClientW + (wr.right - wr.left - currentClientW), wr.bottom - wr.top, 
    SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE);
    VirtualFreeEx(hProcess, pRemoteBtn, 0, MEM_RELEASE);
    CloseHandle(hProcess);
}
LRESULT CALLBACK WndProc(HWND hWnd, UINT m, WPARAM w, LPARAM l) {
    switch (m) {
        case WM_ACTIVATE:
            // Если окно становится неактивным (фокус ушел)
            if (LOWORD(w) == WA_INACTIVE) {
                PostQuitMessage(0);
            }
            break;
        case WM_CREATE:
        SetTimer(hWnd, IDT_REFRESH_TIMER, 2000, NULL);
            RefreshList(hWnd, ((LPCREATESTRUCT)l)->hInstance);
            break;
            case WM_TIMER:
            RefreshList(hWnd, (HINSTANCE)GetWindowLongPtr(hWnd, GWLP_HINSTANCE));
            break;
        case WM_COMMAND:
        SendTrayClick((size_t)LOWORD(w), WM_LBUTTONUP);
            break;
        case WM_CONTEXTMENU: {
            int id = GetWindowLong((HWND)w, GWL_ID);
            if (id >= 0 && (size_t)id < g_apps.size()) SendTrayClick((size_t)id, WM_RBUTTONUP);
            break;
        }
        case WM_DESTROY:
        KillTimer(hWnd, IDT_REFRESH_TIMER);
            PostQuitMessage(0);
            break;
        default: return DefWindowProcW(hWnd, m, w, l);
    }
    return 0;
}

int WINAPI WinMain(HINSTANCE hInst, HINSTANCE, LPSTR, int nShow) {
    int argc;
    LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);

    int x = 200, y = 200, w = 340, h = 400;
    if (argc >= 5) {
        x = _wtoi(argv[1]);
        y = _wtoi(argv[2]);
        w = _wtoi(argv[3]);
        h = _wtoi(argv[4]);
    }
    
    if (argv) LocalFree(argv);


    WNDCLASSW wc = { 0 };
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInst;
    // Используем черный цвет как "ключ" прозрачности
    wc.hbrBackground = CreateSolidBrush(RGB(0, 0, 0)); 
    wc.lpszClassName = L"IconTrayClone";
    RegisterClassW(&wc);

    // WS_POPUP убирает элементы управления
    // WS_EX_LAYERED позволяет управлять прозрачностью
    HWND hWnd = CreateWindowExW(WS_EX_TOPMOST | WS_EX_LAYERED, L"IconTrayClone", NULL, 
        WS_POPUP | WS_VISIBLE, 
        x, y, w, h, NULL, NULL, hInst, NULL);

    // 1. Делаем ЧЕРНЫЙ цвет (фон) полностью прозрачным ("дырка")
    // Это позволит кнопкам быть на 100% непрозрачными
    SetLayeredWindowAttributes(hWnd, RGB(0, 0, 0), 0, LWA_COLORKEY);

    DWM_BLURBEHIND bb = { 0 };
    bb.dwFlags = DWM_BB_ENABLE;
    bb.fEnable = true;
    bb.hRgnBlur = NULL;
    DwmEnableBlurBehindWindow(hWnd, &bb);
   MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    return 0;
}