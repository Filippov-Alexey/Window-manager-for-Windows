#include <windows.h>

void EnableMouseKeys() {
    MOUSEKEYS mk = { sizeof(MOUSEKEYS) };
    // Получаем текущие настройки
    if (SystemParametersInfo(SPI_GETMOUSEKEYS, sizeof(MOUSEKEYS), &mk, 0)) {
        mk.dwFlags |= MKF_MOUSEKEYSON; // Включаем режим
        mk.dwFlags |= MKF_AVAILABLE;   // Делаем доступным
        // Применяем глобально
        SystemParametersInfo(SPI_SETMOUSEKEYS, sizeof(MOUSEKEYS), &mk, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE);
    }
}

int main() {
 // Заставляет систему пересканировать устройства ввода
PostMessage(HWND_BROADCAST, WM_DEVICECHANGE, 0x0007, 0); // DBT_DEVNODES_CHANGED
   // EnableMouseKeys();

    return 0;
}
