#include <windows.h>
#include <mmdeviceapi.h>
#include <endpointvolume.h>
#include <iostream>

#pragma comment(lib, "Ole32.lib")

struct VolumeInfo {
    bool ok;      // true если удалось получить данные
    bool muted;   // состояние mute
    float volume; // 0.0 .. 1.0
};

// Возвращает VolumeInfo; не бросает исключений
VolumeInfo get_master_volume_info() {
    VolumeInfo vi{false, false, 0.0f};

    HRESULT hr = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    bool coInitialized = SUCCEEDED(hr);

    if (FAILED(hr) && hr != RPC_E_CHANGED_MODE) {
        // не удалось инициализировать COM
        if (coInitialized) CoUninitialize();
        return vi;
    }

    IMMDeviceEnumerator* pEnumerator = nullptr;
    hr = CoCreateInstance(__uuidof(MMDeviceEnumerator), NULL, CLSCTX_ALL,
                          __uuidof(IMMDeviceEnumerator), (void**)&pEnumerator);
    if (FAILED(hr) || pEnumerator == nullptr) {
        if (coInitialized) CoUninitialize();
        return vi;
    }

    IMMDevice* pEndpoint = nullptr;
    hr = pEnumerator->GetDefaultAudioEndpoint(eRender, eConsole, &pEndpoint);
    if (FAILED(hr) || pEndpoint == nullptr) {
        pEnumerator->Release();
        if (coInitialized) CoUninitialize();
        return vi;
    }

    IAudioEndpointVolume* pEndpointVolume = nullptr;
    hr = pEndpoint->Activate(__uuidof(IAudioEndpointVolume), CLSCTX_INPROC_SERVER, NULL, (void**)&pEndpointVolume);
    if (FAILED(hr) || pEndpointVolume == nullptr) {
        pEndpoint->Release();
        pEnumerator->Release();
        if (coInitialized) CoUninitialize();
        return vi;
    }

    BOOL bMuted = FALSE;
    hr = pEndpointVolume->GetMute(&bMuted);
    if (FAILED(hr)) {
        // ошибка чтения mute
        pEndpointVolume->Release();
        pEndpoint->Release();
        pEnumerator->Release();
        if (coInitialized) CoUninitialize();
        return vi;
    }

    float volumeLevel = 0.0f;
    hr = pEndpointVolume->GetMasterVolumeLevelScalar(&volumeLevel);
    if (FAILED(hr)) {
        // ошибка чтения уровня
        pEndpointVolume->Release();
        pEndpoint->Release();
        pEnumerator->Release();
        if (coInitialized) CoUninitialize();
        return vi;
    }

    // успех — заполняем структуру
    vi.ok = true;
    vi.muted = (bMuted != 0);
    vi.volume = volumeLevel; // 0.0 .. 1.0

    // освобождение
    pEndpointVolume->Release();
    pEndpoint->Release();
    pEnumerator->Release();
    if (coInitialized) CoUninitialize();

    return vi;
}

int main() {
    VolumeInfo vi = get_master_volume_info();
    if (!vi.ok) {
        std::cout << "{mut: -, vol: -}" << std::endl;
        return 1;
    }

    // Выводим в нужном формате: mut как 0/1, vol в процентах с одной десятой
    int mut_flag = vi.muted ? 1 : 0;
    std::cout << "{\"mut\": \"" << mut_flag << "\", \"vol\": \"" << (vi.volume * 100.0f) << "\"}" << std::endl;
    return 0;
}
