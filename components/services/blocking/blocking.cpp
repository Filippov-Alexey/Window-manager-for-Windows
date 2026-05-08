
#include <iostream>
#include <fstream>
#include <string>
#include <filesystem>
#include <algorithm>

#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#include <limits.h>
#endif

namespace fs = std::filesystem;

// Функция для получения пути к папке, где лежит EXE
fs::path GetExecutableDir() {
#ifdef _WIN32
    wchar_t path[MAX_PATH];
    GetModuleFileNameW(NULL, path, MAX_PATH);
    return fs::path(path).parent_path();
    #endif
}    

#include <codecvt> 
#include <conio.h>
#include <thread>
#include <chrono>
#include <vector>
#include <windows.h>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <map>
#include <fstream>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>
#include <mutex> 
#include <fcntl.h>
#include <io.h>
#include <msctf.h> // Text Services Framework
#include <tlhelp32.h> 

#pragma comment(lib, "ole32.lib")

// Глобальные переменные для связи частей
std::string g_pipeData = ""; 
std::mutex g_pipeMutex;
HHOOK keyboardHook;
bool isBlocked = false;

std::map<int, std::string> keyDictionary;
std::unordered_set<int> currentlyPressedKeys;     
struct Hotkey {
    std::string combination; 
    bool isBlocked;
};
std::vector<Hotkey> hotkeysToBlock;
std::string pressedKeys;

bool IsHotkeyBlocked(const std::string& combination) {
    return std::any_of(hotkeysToBlock.begin(), hotkeysToBlock.end(),
                       [&combination](const Hotkey& hotkey) {
                           return hotkey.combination == combination;
                       });
                    }

std::string VKCodeToHex(int vkCode) {
    std::stringstream ss;
    ss << "0x" << std::uppercase << std::hex << std::setw(2) << std::setfill('0') << vkCode;
    return ss.str();
}

void ProcessKeyModifier(std::string& keyName, const char prefix, std::vector<std::string>& modifierKeys) {
    if (keyName.front() == prefix) {
        keyName.erase(0, 1); 
        if (std::find(modifierKeys.begin(), modifierKeys.end(), keyName) == modifierKeys.end()) {
            modifierKeys.push_back(keyName);
        }
    }
}

void SeparateModifiersAndNonModifiers(const std::string& keyname, const std::unordered_set<int>& vk_key, 
                                       std::vector<int>& vk, 
                                       std::unordered_set<int>& modifiers, 
                                       std::unordered_set<int>& nonModifiers) {
    bool keyFound = false;

    for (int key : vk_key) {
        std::string keyName = keyDictionary.count(key) ? keyDictionary.at(key) : "";
        
        if (!keyName.empty()) {
            if ((keyName.front() != '=') && (keyName.front() != '_') && (keyName.front() != '-')) {
                nonModifiers.insert(key);
            } else {
                modifiers.insert(key);
            }
        }
        
        if (keyName == keyname) {
            keyFound = true; 
        }
    }

    if (!keyFound) {
        int keyCode = std::find_if(keyDictionary.begin(), keyDictionary.end(),
        [&keyname](const auto& pair) { return pair.second == keyname; })->first;
        nonModifiers.insert(keyCode);
    }
    vk.insert(vk.end(), modifiers.begin(), modifiers.end());
    vk.insert(vk.end(), nonModifiers.begin(), nonModifiers.end());
}
void TrimOptions(std::vector<std::string>& options, const std::string& keyName) {
    options.erase(
        std::remove_if(options.begin(), options.end(),
                       [&keyName](const std::string& s) { return s.find(keyName) == std::string::npos; }),
        options.end()
    );
}

void AddOptions(const std::vector<std::string>& modifiers, const std::string& keyName, std::vector<std::string>& options) {
    for (const auto& modifier : modifiers) {
        // Добавляем только если текущая клавиша - это не тот же самый модификатор
        if (modifier != keyName) {
            options.push_back(modifier + "+" + keyName);
        }
    }
    TrimOptions(options, keyName);
}

void AddComplexOptions(const std::vector<std::string>& firstModifier, const std::vector<std::string>& secondModifier, const std::string& keyName, std::vector<std::string>& options) {
    for (const auto& first : firstModifier) {
        if (first == keyName) continue; // Пропускаем, если совпадает с первой частью

        for (const auto& second : secondModifier) {
            if (second == keyName) continue; // Пропускаем, если совпадает со второй частью
            
            options.push_back(first + "+" + second + "+" + keyName);
        }
    }
    TrimOptions(options, keyName);
}

void AddComplexOptions1(const std::vector<std::string>& firstModifier, const std::vector<std::string>& secondModifier, const std::vector<std::string>& thirdModifier, const std::string& keyName, std::vector<std::string>& options) {
    for (const auto& first : firstModifier) {
        if (first == keyName) continue;

        for (const auto& second : secondModifier) {
            if (second == keyName) continue;

            for (const auto& third : thirdModifier) {
                if (third == keyName) continue;

                options.push_back(first + "+" + second + "+" + third + "+" + keyName);
            }
        }
    }
    TrimOptions(options, keyName);
}

template<typename ContainerType>
void replace_all(ContainerType& container, typename ContainerType::value_type old_val, typename ContainerType::value_type new_val) {
    for(auto it = container.begin(); it != container.end(); ++it) {
        if(*it == old_val)
            *it = new_val;
    }
}

void ProcessKeyName(std::string& keyName,
                    std::unordered_set<int>& vk_key,
                    std::vector<std::string>& pressShift,
                    std::vector<std::string>& pressCtrl,
                    std::vector<std::string>& pressAlt,
                    std::string& pressedKeys,
                    std::vector<std::string>& options) {
    
    std::vector<int> vk; 
    std::unordered_set<int> modifiers; 
    std::unordered_set<int> nonModifiers;

    SeparateModifiersAndNonModifiers(keyName, vk_key, vk, modifiers, nonModifiers);

    const int left_alt = 0x12;
    const int alt = 0xa4;
    const int right_alt = 0xa5;
    if(std::find(vk.begin(), vk.end(), left_alt) != vk.end() &&
       std::find(vk.begin(), vk.end(), right_alt) != vk.end()) {
        replace_all(vk, left_alt, alt);
    }
    for (int key : vk) {
        std::string keyName = keyDictionary.count(key) ? keyDictionary.at(key) : "";
        
        if (!keyName.empty()) {
            ProcessKeyModifier(keyName, '=', pressShift);
            ProcessKeyModifier(keyName, '_', pressCtrl);
            ProcessKeyModifier(keyName, '-', pressAlt);
            
            bool hasShift = !pressShift.empty();
            bool hasCtrl = !pressCtrl.empty();
            bool hasAlt = !pressAlt.empty();
            
            if (hasShift && !hasCtrl && !hasAlt) {
                AddOptions(pressShift, keyName, options);
            } else if (!hasShift && hasCtrl && !hasAlt) {
                AddOptions(pressCtrl, keyName, options);
            } else if (!hasShift && !hasCtrl && hasAlt) {
                AddOptions(pressAlt, keyName, options);
            } else if (hasShift && hasCtrl && !hasAlt) {
                AddComplexOptions(pressShift, pressCtrl, keyName, options);
            } else if (hasShift && !hasCtrl && hasAlt) {
                AddComplexOptions(pressShift, pressAlt, keyName, options);
            } else if (!hasShift && hasCtrl && hasAlt) {
                AddComplexOptions(pressCtrl, pressAlt, keyName, options);
            } else if (hasShift && hasCtrl && hasAlt) {
                AddComplexOptions1(pressShift, pressCtrl, pressAlt, keyName, options);
            } else {
                if (pressedKeys!=keyName)
                options.push_back(keyName);
            }
        }
    }
}

// Функция для превращения любой строки в безопасное JSON-значение
std::string json_escape(const std::string& s) {
    std::ostringstream oss;
    for (auto c : s) {
        switch (c) {
            case '"':  oss << "\\\""; break;
            case '\\': oss << "\\\\"; break;
            case '\b': oss << "\\b";  break;
            case '\f': oss << "\\f";  break;
            case '\n': oss << "\\n";  break;
            case '\r': oss << "\\r";  break;
            case '\t': oss << "\\t";  break;
            default:
                if ('\x00' <= c && c <= '\x1f') {
                    oss << "\\u" << std::hex << std::setw(4) << std::setfill('0') << (int)c;
                } else {
                    oss << c;
                }
        }
    }
    return oss.str();
}

void PrintKeyInfo(const std::string& hexCode, const std::string& keyName, 
                  const std::string& pressedKeys, 
                  const std::string& status,DWORD duration, 
                  const std::vector<std::string>& options,
                  const std::string& block, const std::string& isInjected, 
                  const std::string& register_key, const std::string& currentInfo,
                  const std::string& panel 
                ) {

    std::string optionsStr;
    for (const auto& option : options) {
        optionsStr += "\""+option+"\"" + ", ";
    }

    if (!optionsStr.empty()) {
        optionsStr = optionsStr.substr(0, optionsStr.size() - 2); 
    }

// Используйте функцию json_escape из предыдущего ответа
std::cout 
    << "{"
    << "\"key_code\": \""      << hexCode << "\", "
    << "\"key_name\": \""      << json_escape(keyName) << "\", "
    << "\"key\": \""           << json_escape(register_key) << "\", "
    << "\"status\": \""        << status << "\", "
    << "\"duretion\": \""      << duration << "\", "
    << "\"numpan\": \""        << panel << "\", "
    << "\"pressed_keys\": \""  << pressedKeys << "\", "
    << "\"option\": ["         << optionsStr << "], "
    << "\"blocked\": \""       << block << "\", "
    << "\"isInjected\": \""    << isInjected << "\", "
    << "\"layout\": {"         << currentInfo << "}"  // ДОБАВЛЕНЫ СКOБКИ {} ЗДЕСЬ
    << "}" << std::endl;

}


void HandleKeyPress(int vkCode) {
    for (int i = 0; i < 256; ++i) {
        SHORT state = GetAsyncKeyState(i);
        
        std::string keyName = keyDictionary.count(i) ? keyDictionary[i] : std::to_string(i);
        
        bool isKeyDown = (state & 0x8000) != 0;
        bool isKeyUp = (state & 0x8000) == 0 && currentlyPressedKeys.find(i) != currentlyPressedKeys.end();

        if (isKeyDown) {
            if (currentlyPressedKeys.find(i) == currentlyPressedKeys.end()) {
                currentlyPressedKeys.insert(i);
            }
        }

        if (isKeyUp) {
            if (currentlyPressedKeys.find(i) != currentlyPressedKeys.end()){
                currentlyPressedKeys.erase(i);
            }
        }
    }
}

void ProcessOptions(std::vector<std::string>& options, const std::string& pressedKeys) {
    if (options.empty()) return;
    if (!pressedKeys.empty()) {
        options.push_back(pressedKeys);
    }

    auto itHasPlus = std::find_if(options.begin(), options.end(),
                                  [](const std::string& s){ return s.find('+') != std::string::npos; });

    if (itHasPlus != options.end()) {
        std::vector<std::string> filtered;
        for (const auto& s : options) {
            if (s.find('+') != std::string::npos) filtered.push_back(s);
        }
        options.swap(filtered);
        return;
    }

    std::sort(options.begin(), options.end()); 
    std::vector<std::string> permutations;
    do {
        std::string combined;
        for (size_t i = 0; i < options.size(); ++i) {
            if (i > 0) combined += "+";
            combined += options[i];
        }
        permutations.push_back(std::move(combined));
    } while (std::next_permutation(options.begin(), options.end()));

    options.swap(permutations);
}

std::string to_utf8(const std::wstring& wstr) {
    std::wstring_convert<std::codecvt_utf8<wchar_t>> conv;
    return conv.to_bytes(wstr);
} 
HKL lastLayout = NULL;

// --- ЧАСТЬ 1: Поток прослушивания (Pipe Listener) ---
void PipeListener() {
    while (true) {
        HANDLE hPipe = CreateNamedPipeA("\\\\.\\pipe\\LangHookPipe", 
            PIPE_ACCESS_INBOUND, PIPE_TYPE_BYTE | PIPE_WAIT, 1, 1024, 1024, 0, NULL);
        if (hPipe != INVALID_HANDLE_VALUE) {
            if (ConnectNamedPipe(hPipe, NULL) || GetLastError() == ERROR_PIPE_CONNECTED) {
                char buffer[256];
                DWORD read;
                if (ReadFile(hPipe, buffer, sizeof(buffer) - 1, &read, NULL)) {
                    buffer[read] = '\0';
                    // Сохраняем строку для второй части
                    g_pipeData = buffer; 
                    std::lock_guard<std::mutex> lock(g_pipeMutex);
                    // std::cout << buffer << std::flush;
                }
            }
            DisconnectNamedPipe(hPipe);
            CloseHandle(hPipe);
        }
    }
}

std::string currentInfo;
void get_layout(){
    {
        std::lock_guard<std::mutex> lock(g_pipeMutex);
        currentInfo = g_pipeData;
    }
}

std::unordered_map<int, DWORD> startTimes;

LRESULT CALLBACK KeyboardHookCallback(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode != HC_ACTION) return CallNextHookEx(nullptr, nCode, wParam, lParam);
    KBDLLHOOKSTRUCT* pKeyStruct = (KBDLLHOOKSTRUCT*)lParam;
    KBDLLHOOKSTRUCT* ks = reinterpret_cast<KBDLLHOOKSTRUCT*>(lParam);
    if (!ks) return CallNextHookEx(nullptr, nCode, wParam, lParam);
    bool isInjected = pKeyStruct->flags & LLKHF_INJECTED;

    const int vk = static_cast<int>(ks->vkCode);
    const bool isKeyDown = (wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN);
    const bool isKeyUp = (wParam == WM_KEYUP || wParam == WM_SYSKEYUP);
    const bool isExtended = (ks->flags & LLKHF_EXTENDED);

    std::string panel = "Main";
    std::string status = "";

    if ((vk >= VK_NUMPAD0 && vk <= VK_NUMPAD9) || vk == VK_MULTIPLY || 
        vk == VK_ADD || vk == VK_SUBTRACT || vk == VK_DECIMAL || vk == VK_CLEAR) {
        panel = "NumPad";
    } 
    else if (vk == VK_DIVIDE || vk == VK_RETURN) {
        panel = (ks->flags & LLKHF_EXTENDED) ? "NumPad" : "Main";
    } 
    else if (vk == VK_HOME || vk == VK_END || vk == VK_PRIOR || vk == VK_NEXT || 
             vk == VK_INSERT || vk == VK_DELETE || 
             vk == VK_UP || vk == VK_DOWN || vk == VK_LEFT || vk == VK_RIGHT) {
        // Для этих клавиш: нет флага Extended = NumPad
        panel = (ks->flags & LLKHF_EXTENDED) ? "Main" : "NumPad";
    }
    
    
    std::string register_key;
    
    HWND hwnd = GetForegroundWindow();
    DWORD remoteThreadId = GetWindowThreadProcessId(hwnd, NULL);
    BYTE keyState[256] = { 0 };
    
    // Получаем реальное состояние Shift, Ctrl, Alt на момент нажатия
    if (GetKeyState(VK_SHIFT) & 0x8000) keyState[VK_SHIFT] = 0x80;
    if (GetKeyState(VK_CAPITAL) & 0x0001) keyState[VK_CAPITAL] = 0x01; // Caps Lock включен
    if (GetKeyState(VK_CONTROL) & 0x8000) keyState[VK_CONTROL] = 0x80;
    if (GetKeyState(VK_MENU) & 0x8000) keyState[VK_MENU] = 0x80;
    
    // 2. Извлекаем нужный HKL (раскладку) из вашей строки currentInfo
    HKL targetHkl = nullptr;
    uintptr_t hklValue = 0;
    const char* hklPtr = strstr(currentInfo.c_str(), "\"HKL\": \"0x");
    if (hklPtr) {
        sscanf_s(hklPtr, "\"HKL\": \"0x%llx\"", &hklValue);
        targetHkl = (HKL)hklValue;
    }
    
    // 3. Конвертируем с учетом регистра
    wchar_t buffer[5] = { 0 };
    int res = ToUnicodeEx(vk, ks->scanCode, keyState, buffer, 4, 0, targetHkl);
    
    if (res > 0) {
        // Теперь здесь будет 'C' или 'c' (или 'С'/'с' для RU) в зависимости от Shift/Caps
        std::wstring ws(buffer, res);
        register_key = to_utf8(ws);
    }
    
    // register_key="l";
    get_layout();
    
    static thread_local std::vector<std::string> pressShift;
    static thread_local std::vector<std::string> pressCtrl;
    static thread_local std::vector<std::string> pressAlt;
    static thread_local std::vector<std::string> options;
    pressShift.clear(); pressCtrl.clear(); pressAlt.clear(); options.clear();
    
    auto it = keyDictionary.find(vk);
    std::string keyName = (it != keyDictionary.end()) ? it->second : std::string();
    ProcessKeyModifier(keyName, '=', pressShift);
    ProcessKeyModifier(keyName, '_', pressCtrl);
    ProcessKeyModifier(keyName, '-', pressAlt);
    
    if (keyName=="return"){register_key="return";}
    HandleKeyPress(vk);
    
    ProcessKeyName(keyName, currentlyPressedKeys, pressShift, pressCtrl, pressAlt, pressedKeys, options);
    ProcessOptions(options, pressedKeys);
    DWORD duration = 0;

    if (isKeyDown) {
        if (startTimes.find(vk) == startTimes.end()) {
            startTimes[vk] = ks->time;
        } else {
            duration = ks->time - startTimes[vk];
        }
    } 
    else if (isKeyUp) {
        if (startTimes.count(vk)) {
            duration = ks->time - startTimes[vk];
            startTimes.erase(vk);
        }
    }

    if (IsHotkeyBlocked(keyName)) {
        pressedKeys = keyName;
        options.clear();
        options.push_back(keyName);
    } else {
        for (const auto& opt : options) {
            if (IsHotkeyBlocked(opt)) { pressedKeys = opt; break; }
        }
    }
    
    if (!pressedKeys.empty() && isKeyUp) {
        if (keyName == pressedKeys) {
            pressedKeys.clear();
        } else {
            for (const auto& opt : options) {
                if (opt == pressedKeys) { pressedKeys.clear(); break; }
            }
        }
    }
    
    bool isNumLock = (GetKeyState(VK_NUMLOCK) & 0x0001) != 0;
    bool isCapsLock = (GetKeyState(VK_CAPITAL) & 0x0001) != 0;
    isBlocked = ((!pressedKeys.empty()&&!isInjected)||(panel=="NumPad"&&!isNumLock));
    
    PrintKeyInfo(VKCodeToHex(vk), keyName, pressedKeys, (isKeyDown ? "Down" : (isKeyUp ? "Up" : "None")), duration, options, (isBlocked?"Blocked":"No blocked"), (isInjected?"Programm":"Physical"), register_key, currentInfo, panel);
    
    if (isBlocked)return 1;
    return CallNextHookEx(nullptr, nCode, wParam, lParam);
}
void GeneratePermutations(const std::vector<std::string>& keys, std::vector<std::string>& results, int start) {
    if (start == keys.size() - 1) {
        std::string permutation;
        for (const auto& key : keys) {
            if (!permutation.empty()) {
                permutation += "+";
            }
            permutation += key; 
        }
        results.push_back(permutation);
        return;
    }

    for (int i = start; i < keys.size(); ++i) {
        std::vector<std::string> tempKeys = keys; 
        std::swap(tempKeys[start], tempKeys[i]); 
        GeneratePermutations(tempKeys, results, start + 1);
    }
}
void ParseArguments(int argc, char* argv[]) {
    for (int i = 1; i < argc; ++i) {
        std::string hotkeyCombination = argv[i];

        std::istringstream ss(hotkeyCombination);
        std::vector<std::string> keys;
        std::string token;

        while (std::getline(ss, token, '+')) {
            keys.push_back(token); 
        }

        hotkeysToBlock.push_back({ hotkeyCombination, true });

        std::vector<std::string> permutations;
        GeneratePermutations(keys, permutations, 0);

        for (const auto& perm : permutations) {
            if (perm != hotkeyCombination) { 
                hotkeysToBlock.push_back({ perm, true });
            }
        }
    }
}

void ParseKeyCodeFile(const std::string& fileName) {
    // Формируем полный путь: папка_программы + имя_файла
    fs::path fullPath = GetExecutableDir() / fileName;

    std::ifstream file(fullPath);
    if (!file.is_open()) {
        std::cerr << "Error opening key code file: " << fileName << std::endl;
        return;
    }

    std::string line;
    while (std::getline(file, line)) {
        line.erase(std::remove(line.begin(), line.end(), ' '), line.end());
        size_t pos = line.find(':');
        if (pos != std::string::npos) {
            std::string keyName = line.substr(1, pos - 2);
            std::string hexCode = line.substr(pos + 1);
            try {
                int keyCode = std::stoi(hexCode, nullptr, 16);
                keyDictionary[keyCode] = keyName;
            } catch (const std::invalid_argument& e) {
                std::cerr << "Error parsing key code: " << hexCode << std::endl;
            }
        }
    }
    file.close();
}
void GetInitialLanguage() {
    HRESULT hr = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    ITfInputProcessorProfiles* pProfiles = NULL;

    hr = CoCreateInstance(CLSID_TF_InputProcessorProfiles, NULL, 
                          CLSCTX_INPROC_SERVER, IID_ITfInputProcessorProfiles, 
                          (void**)&pProfiles);

    if (SUCCEEDED(hr)) {
        LANGID langId = 0;
        hr = pProfiles->GetCurrentLanguage(&langId);
        
        if (SUCCEEDED(hr)) {
            char langName[LOCALE_NAME_MAX_LENGTH] = {0};
            char buf[512]; // Буфер для итоговой строки
            
            // 1. Получаем понятное имя (например, "English")
            GetLocaleInfoA(MAKELCID(langId, SORT_DEFAULT), (0x1001), langName, sizeof(langName));
            
            // 2. Получаем текущий HKL (Handle к раскладке)
            HKL hkl = GetKeyboardLayout(0);

            // 3. Формируем строку строго по вашему формату
            sprintf_s(buf, "\"Name\": \"%s\", \"HKL\": \"0x%p\", \"ID\": \"0x%04x\"", 
                      langName, (void*)hkl, langId);

            // 4. Записываем в общую переменную с защитой мьютексом
            {
                std::lock_guard<std::mutex> lock(g_pipeMutex);
                g_pipeData = buf;
            }

        }
        pProfiles->Release();
    }
    CoUninitialize();
}


void TerminateOtherInstances(const std::wstring& processName) {
    // Получаем ID текущего процесса, чтобы не закрыть самого себя
    DWORD currentPID = GetCurrentProcessId();

    while (true) {
        HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if (hSnap != INVALID_HANDLE_VALUE) {
            PROCESSENTRY32W pe;
            pe.dwSize = sizeof(pe);

            if (Process32FirstW(hSnap, &pe)) {
                do {
                    // 1. Проверяем имя файла (без учета регистра)
                    // 2. Проверяем, что это НЕ текущий процесс
                    if (_wcsicmp(pe.szExeFile, processName.c_str()) == 0 && pe.th32ProcessID != currentPID) {
                        
                        HANDLE hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, pe.th32ProcessID);
                        if (hProcess != NULL) {
                            TerminateProcess(hProcess, 0);
                            CloseHandle(hProcess);
                        }
                    }
                } while (Process32NextW(hSnap, &pe));
            }
            CloseHandle(hSnap);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    }
}

int main(int argc, char* argv[]) {
    ParseArguments(argc, argv);
    ParseKeyCodeFile("key_code.txt");
    GetInitialLanguage();
    
    SetConsoleOutputCP(CP_UTF8);
    setvbuf(stdout, nullptr, _IOFBF, 1000); // Чтобы избежать разрыва UTF-8 последовательностей

    std::thread(TerminateOtherInstances, L"blocking.exe").detach();
    HHOOK keyboardHook = SetWindowsHookEx(WH_KEYBOARD_LL, KeyboardHookCallback, NULL, 0);
    if (!keyboardHook) {
        std::cerr << "Failed to install hook!" << std::endl;
        return 1;
    }
    std::thread(PipeListener).detach();

    HMODULE hDll = LoadLibrary(TEXT("g.dll"));
    if (!hDll) { std::cout << "DLL NOT FOUND!" << std::endl; return 1; }

    HOOKPROC proc = (HOOKPROC)GetProcAddress(hDll, "CallWndRetProc");
    if (!proc) { std::cout << "FUNC NOT FOUND!" << std::endl; return 1; }

    HHOOK hHook = SetWindowsHookEx(12, proc, hDll, 0);

    MSG msg;
    while (GetMessage(&msg, nullptr, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    UnhookWindowsHookEx(keyboardHook);
        UnhookWindowsHookEx(hHook);
    return 0;
}
