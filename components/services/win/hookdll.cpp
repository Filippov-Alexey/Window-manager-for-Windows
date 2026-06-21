#include <windows.h>
#include <cstdio>
#include <cstring>

#pragma section(".shared", read, write, shared)
// Массив флагов блокировки для всех 16 кодов операций
__declspec(allocate(".shared")) volatile BOOL g_BlockedOps[32] = { FALSE };

extern "C" __declspec(dllexport) void SetSWBlocked(int opCode, BOOL block)
{
    if (opCode >= 0 && opCode < 32)
    {
        g_BlockedOps[opCode] = block;
    }
}

static void LogToHost(const char* msg)
{
    HANDLE h = CreateFileA("\\\\.\\pipe\\HookLogger", GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
    if (h != INVALID_HANDLE_VALUE)
    {
        DWORD written = 0;
        WriteFile(h, msg, (DWORD)strlen(msg), &written, NULL);
        CloseHandle(h);
    }
}

static const char* GetOpName(int opCode)
{
    switch (opCode)
    {
        case 0:  return "SW_HIDE";
        case 1:  return "SW_SHOWNORMAL";
        case 2:  return "SW_SHOWMINIMIZED";
        case 3:  return "SW_SHOWMAXIMIZED";
        case 4:  return "SW_SHOWNOACTIVATE";
        case 5:  return "SW_SHOW";
        case 6:  return "SW_MINIMIZE";
        case 7:  return "SW_SHOWMINNOACTIVE";
        case 8:  return "SW_SHOWNA";
        case 9:  return "SW_RESTORE";
        case 10: return "SW_SHOWDEFAULT";
        case 11: return "SW_FORCEMINIMIZE";
        case 12: return "CUSTOM_MOVE";
        case 13: return "CUSTOM_SIZE";
        case 14: return "CUSTOM_CLOSE";
        case 15: return "CUSTOM_SHOWWINDOW";
        default: return "UNKNOWN_OPERATION";
    }
}

extern "C" __declspec(dllexport) LRESULT CALLBACK CBTProc(int nCode, WPARAM wParam, LPARAM lParam)
{
    if (nCode >= 0)
    {
        HWND hwnd = (HWND)wParam;

        // 1. Обработка сворачивания / разворачивания / восстановления (0 - 11)
        if (nCode == HCBT_MINMAX)
        {
            int swCode = (int)lParam;
            if (swCode >= 0 && swCode < 12)
            {
                BOOL isBlocked = g_BlockedOps[swCode];
                char buf[512];
                snprintf(buf, sizeof(buf), "%d|%s|0x%p\n", swCode, GetOpName(swCode), (void*)hwnd);
                LogToHost(buf);
                if (isBlocked) return 1;
            }
        }

        // 2. Обработка перемещения (12) и изменения размеров мышью (13)
        if (nCode == HCBT_MOVESIZE)
        {
            int currentCode = 12; // По умолчанию Move
            
            // Если пользователь кликнул на область изменения размера, проверяем стиль окна
            // В Windows во время MOVESIZE lParam содержит RECT*, но структура движения определяется позицией курсора.
            // Для точности проверяем, куда нажал пользователь через сообщения, но здесь используем базовое разделение:
            // Если окно имеет изменяемые границы, и это не простой перенос, верифицируем операцию.
            LONG_PTR style = GetWindowLongPtrW(hwnd, GWL_STYLE);
            
            // Если событие инициировано, логируем движение.
            // Динамически разделяем Move (12) и Size (13) на основе состояния мыши (инженерный трюк Win32)
            if (GetAsyncKeyState(VK_LBUTTON) & 0x8000) {
                POINT pt;
                GetCursorPos(&pt);
                LRESULT hit = SendMessageW(hwnd, WM_NCHITTEST, 0, MAKELPARAM(pt.x, pt.y));
                if (hit >= HTLEFT && hit <= HTBOTTOMRIGHT) {
                    currentCode = 13; // Пользователь тянет за край -> Изменение размера
                }
            }

            BOOL isBlocked = g_BlockedOps[currentCode];
            char buf[512];
            snprintf(buf, sizeof(buf), "%d|%s|0x%p\n", currentCode, GetOpName(currentCode), (void*)hwnd);
            LogToHost(buf);

            if (isBlocked) return 1; // Замораживает действие
        }
    }
    return CallNextHookEx(NULL, nCode, wParam, lParam);
}

extern "C" __declspec(dllexport) LRESULT CALLBACK CallWndProc(int nCode, WPARAM wParam, LPARAM lParam)
{
    if (nCode >= 0 && lParam)
    {
        CWPSTRUCT* p = reinterpret_cast<CWPSTRUCT*>(lParam);
        if (p)
        {
            // 3. Обработка закрытия окон (14)
            if (p->message == WM_CLOSE)
            {
                BOOL isBlocked = g_BlockedOps[14];
                char buf[512];
                snprintf(buf, sizeof(buf), "14|%s|0x%p\n", GetOpName(14), (void*)p->hwnd);
                LogToHost(buf);

                if (isBlocked) {
                    p->message = WM_NULL;
                    return 0;
                }
            }

            // 4. Программный показ / скрытие через сообщения (15)
            if (p->message == WM_SHOWWINDOW)
            {
                BOOL isBlocked = g_BlockedOps[15];
                char buf[512];
                snprintf(buf, sizeof(buf), "15|%s|0x%p\n", GetOpName(15), (void*)p->hwnd);
                LogToHost(buf);

                if (isBlocked) {
                    p->message = WM_NULL;
                    return 0;
                }
            }
        }
    }
    return CallNextHookEx(NULL, nCode, wParam, lParam);
}

BOOL WINAPI DllMain(HINSTANCE hinst, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH) DisableThreadLibraryCalls(hinst);
    return TRUE;
}
