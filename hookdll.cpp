
#include <windows.h>
#include <cstdio>
#include <cstring>

static void LogToHost(const char* msg)
{
    HANDLE h = CreateFileA(
        "\\\\.\\pipe\\HookLogger",
        GENERIC_WRITE,
        0,
        NULL,
        OPEN_EXISTING,
        0,
        NULL);

    if (h != INVALID_HANDLE_VALUE)
    {
        DWORD written = 0;
        DWORD len = (DWORD)strlen(msg);
        WriteFile(h, msg, len, &written, NULL);
        CloseHandle(h);
    }
    else
    {
        OutputDebugStringA(msg);
    }
}

static const DWORD MOVE_SIZE_LOG_THROTTLE_MS = 500;

extern "C" __declspec(dllexport) LRESULT CALLBACK CBTProc(int nCode, WPARAM wParam, LPARAM lParam)
{
    if (nCode == HCBT_MINMAX)
    {
        int cmd = (int)lParam;
        if (cmd == SW_MAXIMIZE)
        {
            char buf[256];
            HWND hwnd = (HWND)wParam;
            DWORD pid = 0;
            GetWindowThreadProcessId(hwnd, &pid);
            snprintf(buf, sizeof(buf), "CBTProc: blocked MIN/MAX, cmd=%d, hwnd=0x%p, pid=%u\n",
                     cmd, (unsigned long long)(uintptr_t)hwnd, (unsigned)pid);
            LogToHost(buf);
            return 1;
        }
    }
    return CallNextHookEx(NULL, nCode, wParam, lParam);
}

extern "C" __declspec(dllexport) LRESULT CALLBACK CallWndProc(int nCode, WPARAM wParam, LPARAM lParam)
{
    if (nCode >= 0 && lParam)
    {
        CWPSTRUCT* p = reinterpret_cast<CWPSTRUCT*>(lParam);
        if (!p) return CallNextHookEx(NULL, nCode, wParam, lParam);

        HWND hwnd = p->hwnd;
        DWORD pid = 0;
        GetWindowThreadProcessId(hwnd, &pid);

        char buf[512];

        switch (p->message)
        {
        case WM_SHOWWINDOW:
        {
            BOOL fShow = static_cast<BOOL>(p->wParam);
            snprintf(buf, sizeof(buf), "CallWndProc: WM_SHOWWINDOW %s blocked hwnd=0x%p pid=%u\n",
                     fShow ? "SHOW" : "HIDE", (unsigned long long)(uintptr_t)hwnd, (unsigned)pid);
            LogToHost(buf);

            p->message = WM_NULL; 
            return 0;
        }

        case WM_CLOSE:
        {
            snprintf(buf, sizeof(buf), "CallWndProc: WM_CLOSE blocked hwnd=0x%p pid=%u\n",
                     (unsigned long long)(uintptr_t)hwnd, (unsigned)pid);
            LogToHost(buf);
            p->message = WM_NULL;
            return 0;
        }

        case WM_MOVE:
        {
            if (MOVE_SIZE_LOG_THROTTLE_MS > 0)
            {
                static DWORD lastTick = 0;
                DWORD tick = GetTickCount();
                if (tick - lastTick >= MOVE_SIZE_LOG_THROTTLE_MS)
                {
                    int x = static_cast<int>(static_cast<short>(LOWORD(p->lParam)));
                    int y = static_cast<int>(static_cast<short>(HIWORD(p->lParam)));

                    LogToHost(buf);
                    lastTick = tick;
                }
            }
            break;
        }

        case WM_SIZE:
        {
            if (MOVE_SIZE_LOG_THROTTLE_MS > 0)
            {
                static DWORD lastTickSize = 0;
                DWORD tick = GetTickCount();
                if (tick - lastTickSize >= MOVE_SIZE_LOG_THROTTLE_MS)
                {
                    int wstate = static_cast<int>(p->wParam);
                    const char* sState = "UNKNOWN";
                    if (wstate == SIZE_MINIMIZED) sState = "MINIMIZED";
                    else if (wstate == SIZE_MAXIMIZED) sState = "MAXIMIZED";
                    else if (wstate == SIZE_RESTORED) sState = "RESTORED";
                    int cx = static_cast<int>(LOWORD(p->lParam));
                    int cy = static_cast<int>(HIWORD(p->lParam));
                    snprintf(buf, sizeof(buf), "CallWndProc: WM_SIZE hwnd=0x%p pid=%u state=%s cx=%d cy=%d\n",
                             (unsigned long long)(uintptr_t)hwnd, (unsigned)pid, sState, cx, cy);
                             
                    LogToHost(buf);
                    lastTickSize = tick;
                }
            }
            break;
        }

        default:
            break;
        }
    }

    return CallNextHookEx(NULL, nCode, wParam, lParam);
}

BOOL WINAPI DllMain(HINSTANCE hinst, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        DisableThreadLibraryCalls(hinst);
    }
    return TRUE;
}