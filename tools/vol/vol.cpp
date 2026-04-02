#include <windows.h>
#include <mmdeviceapi.h>
#include <endpointvolume.h>
#include <iostream>

#pragma comment(lib, "Ole32.lib")

// Класс-обработчик событий изменения громкости
class VolumeEvents : public IAudioEndpointVolumeCallback {
    LONG _refCount = 1;
public:
    STDMETHODIMP QueryInterface(REFIID riid, void** ppv) {
        if (riid == __uuidof(IUnknown) || riid == __uuidof(IAudioEndpointVolumeCallback)) {
            *ppv = static_cast<IAudioEndpointVolumeCallback*>(this);
            return S_OK;
        }
        *ppv = nullptr; return E_NOINTERFACE;
    }
    STDMETHODIMP_(ULONG) AddRef() { return InterlockedIncrement(&_refCount); }
    STDMETHODIMP_(ULONG) Release() {
        ULONG res = InterlockedDecrement(&_refCount);
        if (res == 0) delete this; return res;
    }
    // Вызывается системой при изменении громкости или Mute
    STDMETHODIMP OnNotify(PAUDIO_VOLUME_NOTIFICATION_DATA pData) {
        std::cout << "{\"mut\": \"" << (pData->bMuted ? 1 : 0) 
                  << "\", \"vol\": \"" << (int(pData->fMasterVolume * 100.0f + 0.5f)) 
                  << "\"}" << std::endl;
        return S_OK;
    }
};

int main() {
    CoInitializeEx(NULL, COINIT_MULTITHREADED);

    IMMDeviceEnumerator* pEnumerator = nullptr;
    IMMDevice* pDevice = nullptr;
    IAudioEndpointVolume* pVolume = nullptr;
    VolumeEvents* pCallback = new VolumeEvents();

    // 1. Подготовка интерфейсов
    CoCreateInstance(__uuidof(MMDeviceEnumerator), NULL, CLSCTX_ALL, __uuidof(IMMDeviceEnumerator), (void**)&pEnumerator);
    pEnumerator->GetDefaultAudioEndpoint(eRender, eConsole, &pDevice);
    pDevice->Activate(__uuidof(IAudioEndpointVolume), CLSCTX_INPROC_SERVER, NULL, (void**)&pVolume);

    // 2. Регистрация колбэка (теперь Windows сама скажет нам об изменениях)
    pVolume->RegisterControlChangeNotify(pCallback);

    // Выведем начальное состояние
    BOOL muted; float vol;
    pVolume->GetMute(&muted);
    pVolume->GetMasterVolumeLevelScalar(&vol);
    std::cout << "{\"mut\": \"" << (muted ? 1 : 0) << "\", \"vol\": \"" << (int(vol * 100.0f + 0.5f)) << "\"}" << std::endl;

    // 3. Бесконечный цикл с минимальным потреблением
    // Программа просто ждет системных сообщений
    MSG msg;
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    // Очистка (в данном бесконечном примере недостижима, но полезна для структуры)
    pVolume->UnregisterControlChangeNotify(pCallback);
    pVolume->Release();
    pDevice->Release();
    pEnumerator->Release();
    CoUninitialize();

    return 0;
}
