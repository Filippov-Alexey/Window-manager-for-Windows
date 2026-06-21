#include "KeyboardHook.h"
#include <sstream>
#include <iomanip>
#include <iostream>
#include <codecvt>

// Инициализация старых статических членов класса
KeyDictionary* KeyboardHook::_dict = nullptr;
HotkeyManager* KeyboardHook::_hm = nullptr;
LanguageMonitor* KeyboardHook::_lm = nullptr;
std::unordered_map<int, DWORD> KeyboardHook::_startTimes;
std::unordered_set<int> KeyboardHook::_currentlyPressedKeys;
std::string KeyboardHook::_pressedKeysStr;

// === ИНИЦИАЛИЗАЦИЯ НОВЫХ СТАТИЧЕСКИХ ЧЛЕНОВ ДЛЯ ПОТОКА СПАМА ===
// std::thread KeyboardHook::_tickerThread;
std::mutex KeyboardHook::_hookMutex;
std::condition_variable KeyboardHook::_cv;
std::atomic<bool> KeyboardHook::_running{true};
KeyStateInfo KeyboardHook::_lastInfo;

void KeyboardHook::initialize(KeyDictionary* dict, HotkeyManager* hm, LanguageMonitor* lm) {
    _dict = dict; 
    _hm = hm; 
    _lm = lm;
    
    // Запускаем фоновый поток спама
    // _tickerThread = std::thread(&KeyboardHook::startTickerLoop);
}

// void KeyboardHook::shutdown() {
// _running = false;
// _cv.notify_all(); // Пробуждаем поток, чтобы он корректно завершился
//     if (_tickerThread.joinable()) {
//         _tickerThread.join();
//     }
// }
// void KeyboardHook::startTickerLoop() {
//     while (_running) {
//         std::unique_lock<std::mutex> lock(_hookMutex);

//         if (_startTimes.empty()) {
//             _cv.wait(lock, [] { return !_startTimes.empty() || !_running; });
//         }

//         if (!_running) break;

//         DWORD currentTick = GetTickCount(); 
//         std::string pressedWithTime = "";
//         int primaryVk = 0;
//         DWORD maxDuration = 0;

//         for (const auto& [pressedVk, startTime] : _startTimes) {
//             std::string name = _dict->getName(pressedVk);
//             if (!name.empty() && (name.front() == '=' || name.front() == '_' || name.front() == '-')) {
//                 name.erase(0, 1); 
//             }
//             if (name.empty()) {
//                 std::stringstream ss;
//                 ss << "0x" << std::uppercase << std::hex << pressedVk;
//                 name = ss.str();
//             }

//             DWORD holdDuration = currentTick - startTime;
//             if (holdDuration >= maxDuration) {
//                 maxDuration = holdDuration;
//                 primaryVk = pressedVk;
//             }

//             std::string timeStr = std::to_string(holdDuration);

//             if (!pressedWithTime.empty()) pressedWithTime += ", ";
//             pressedWithTime += '"' + name + '"' + ":" + '"' + timeStr + '"';
//         }

//         if (primaryVk != 0) {
//             std::stringstream ss;
//             ss << "0x" << std::uppercase << std::hex << std::setw(2) << std::setfill('0') << primaryVk;
//             _lastInfo.hexCode = ss.str();
            
//             std::string pName = _dict->getName(primaryVk);
//             if (!pName.empty() && (pName.front() == '=' || pName.front() == '_' || pName.front() == '-')) {
//                 pName.erase(0, 1);
//             }
//             _lastInfo.keyName = pName;
//             _lastInfo.duration = maxDuration; 
//         }

//         _lastInfo.pressedKeysTime = pressedWithTime;

//         std::vector<std::string> activeOptions;
//         for (const auto& opt : _lastInfo.options) {
//             bool isComponentMissing = false;
//             std::size_t start = 0;
//             std::size_t end = opt.find('+');
//             while (true) {
//                 std::string token = opt.substr(start, end - start);
//                 bool tokenIsPressed = false;
//                 for (const auto& [pressedVk, _] : _startTimes) {
//                     std::string pName = _dict->getName(pressedVk);
//                     if (!pName.empty() && (pName.front() == '=' || pName.front() == '_' || pName.front() == '-')) {
//                         pName.erase(0, 1);
//                     }
//                     if (pName == token || token == "ctrl" || token == "shift" || token == "alt") { 
//                         tokenIsPressed = true;
//                         break;
//                     }
//                 }

//                 if (!tokenIsPressed) {
//                     isComponentMissing = true;
//                     break;
//                 }

//                 if (end == std::string::npos) break;
//                 start = end + 1;
//                 end = opt.find('+', start);
//             }

//             if (!isComponentMissing) {
//                 activeOptions.push_back(opt);
//             }
//         }

//         if (activeOptions.empty()) {
//             for (const auto& [pressedVk, _] : _startTimes) {
//                 std::string name = _dict->getName(pressedVk);
//                 if (!name.empty() && (name.front() == '=' || name.front() == '_' || name.front() == '-')) {
//                     name.erase(0, 1);
//                 }
//                 if (!name.empty()) activeOptions.push_back(name);
//             }
//             _hm->processOptions(activeOptions, "");
//         }

//         _lastInfo.options = activeOptions;

//         // === ИСПРАВЛЕНИЕ: Выставляем "Down" перед выводом в поток ===
//         _lastInfo.status = "Down"; 

//         printKeyInfo(_lastInfo);

//         lock.unlock();
//         std::this_thread::sleep_for(std::chrono::milliseconds(50));
//     }
// }

std::string KeyboardHook::jsonEscape(const std::string& s) {
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
                } else { oss << c; }
        }
    }
    return oss.str();
}

void KeyboardHook::syncKeyState() {
    for (int i = 0; i < 256; ++i) {
        SHORT state = GetAsyncKeyState(i);
        if ((state & 0x8000) != 0) _currentlyPressedKeys.insert(i);
        else _currentlyPressedKeys.erase(i);
    }
}

std::string KeyboardHook::toUtf8(const std::wstring& wstr) {
    std::wstring_convert<std::codecvt_utf8<wchar_t>> conv;
    return conv.to_bytes(wstr);
}

void KeyboardHook::printKeyInfo(const KeyStateInfo& info) {
    std::string optStr;
    for (size_t i = 0; i < info.options.size(); ++i) {
        optStr += "\"" + info.options[i] + "\"" + (i + 1 < info.options.size() ? ", " : "");
    }

    std::cout << "{"
              << "\"key_code\": \""          << info.hexCode << "\", "
              << "\"key_name\": \""          << jsonEscape(info.keyName) << "\", " 
              << "\"key\": \""               << jsonEscape(info.registerKey) << "\", "
              << "\"status\": \""            << info.status << "\", "
              << "\"duretion\": \""          << info.duration << "\", " 
              << "\"numpan\": \""            << info.panel << "\", "
              << "\"pressed_keys\": \""      << info.pressedKeysStr << "\", "
              << "\"pressed_keys_time\": {"  << info.pressedKeysTime << "}, " 
              << "\"option\": ["             << optStr << "], "
              << "\"blocked\": \""           << info.blockStatus << "\", "
              << "\"isInjected\": \""        << info.injectionType << "\", "
              << "\"layout\": {"             << info.currentLayout << "}"
              << "}" << std::endl;
}

LRESULT CALLBACK KeyboardHook::hookCallback(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode != HC_ACTION || !lParam) return CallNextHookEx(nullptr, nCode, wParam, lParam);

    KBDLLHOOKSTRUCT* ks = reinterpret_cast<KBDLLHOOKSTRUCT*>(lParam);
    bool isInjected = ks->flags & LLKHF_INJECTED;
    int vk = static_cast<int>(ks->vkCode);
    bool isKeyDown = (wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN);
    bool isKeyUp = (wParam == WM_KEYUP || wParam == WM_SYSKEYUP);

    // === СИНХРОНИЗАЦИЯ: Захватываем мьютекс для защиты общих ресурсов с потоком спама ===
    std::lock_guard<std::mutex> lock(_hookMutex);

    KeyStateInfo info;
    info.injectionType = isInjected ? "Programm" : "Physical";
    info.status = isKeyDown ? "Down" : (isKeyUp ? "Up" : "None");
    
    if ((vk >= VK_NUMPAD0 && vk <= VK_NUMPAD9) || vk == VK_MULTIPLY || vk == VK_ADD || vk == VK_SUBTRACT || vk == VK_DECIMAL || vk == VK_CLEAR) {
        info.panel = "NumPad";
    } else if (vk == VK_DIVIDE || vk == VK_RETURN) {
        info.panel = (ks->flags & LLKHF_EXTENDED) ? "NumPad" : "Main";
    } else if (vk == VK_HOME || vk == VK_END || vk == VK_PRIOR || vk == VK_NEXT || vk == VK_INSERT || vk == VK_DELETE || vk == VK_UP || vk == VK_DOWN || vk == VK_LEFT || vk == VK_RIGHT) {
        info.panel = (ks->flags & LLKHF_EXTENDED) ? "Main" : "NumPad";
    } else {
        info.panel = "Main";
    }

    BYTE keyState[256] = {0};

    wchar_t wbuf[5] = {0}; 
    if (GetKeyState(VK_SHIFT) & 0x8000) keyState[VK_SHIFT] = 0x80;
    if (GetKeyState(VK_CAPITAL) & 0x0001) keyState[VK_CAPITAL] = 0x01;
    if (GetKeyState(VK_CONTROL) & 0x8000) keyState[VK_CONTROL] = 0x80;
    if (GetKeyState(VK_MENU) & 0x8000) keyState[VK_MENU] = 0x80;

    info.currentLayout = _lm->getCurrentInfo();
    HKL targetHkl = nullptr;
    uintptr_t hklValue = 0;
    const char* hklPtr = strstr(info.currentLayout.c_str(), "\"HKL\": \"0x");
    if (hklPtr) {
        sscanf_s(hklPtr, "\"HKL\": \"0x%llx\"", &hklValue);
        targetHkl = (HKL)hklValue;
    }

    // Рекомендуется флаг 0x04 для предотвращения порчи буфера Windows
    if (ToUnicodeEx(vk, ks->scanCode, keyState, wbuf, 4, 0x04, targetHkl) > 0) {
        info.registerKey = toUtf8(wbuf);
    }

    std::string keyName = _dict->getName(vk);
    if (keyName == "return") info.registerKey = "return";
    
    if (isKeyDown) {
        if (_startTimes.find(vk) == _startTimes.end()) {
            _startTimes[vk] = ks->time;
        }
        info.duration = ks->time - _startTimes[vk];
    } else if (isKeyUp) {
        if (_startTimes.count(vk)) {
            info.duration = ks->time - _startTimes[vk];
        }
    }
    
    std::string pressedWithTime = "";
    if (isKeyDown && _startTimes.find(vk) == _startTimes.end()) {
        _startTimes[vk] = ks->time;
    }
    
    for (const auto& [pressedVk, startTime] : _startTimes) {
        std::string name = _dict->getName(pressedVk);
        if (!name.empty() && (name.front() == '=' || name.front() == '_' || name.front() == '-')) {
            name.erase(0, 1); 
        }
        if (name.empty()) {
            std::stringstream ss;
            ss << "0x" << std::uppercase << std::hex << pressedVk;
            name = ss.str();
        }
        DWORD holdDuration = ks->time - startTime;
        std::string timeStr = std::to_string(holdDuration);

        if (!pressedWithTime.empty()) pressedWithTime += ", ";
        pressedWithTime += '"' + name + '"' + ":" + '"' + timeStr + '"';
    }
    info.pressedKeysTime = pressedWithTime;

    syncKeyState();
    _hm->processKeyName(keyName, _currentlyPressedKeys, *_dict, _pressedKeysStr, info.options);
    _hm->processOptions(info.options, _pressedKeysStr);

    std::string cleanKeyName = keyName;
    if (!cleanKeyName.empty() && (cleanKeyName.front() == '=' || cleanKeyName.front() == '_' || cleanKeyName.front() == '-')) {
        cleanKeyName.erase(0, 1);
    }
    info.keyName = cleanKeyName;
    
    if (_hm->isHotkeyBlocked(keyName)) {
        _pressedKeysStr = keyName;
        info.options = { keyName };
    } else {
        for (const auto& opt : info.options) {
            if (_hm->isHotkeyBlocked(opt)) { _pressedKeysStr = opt; break; }
        }
    }

    if (!_pressedKeysStr.empty() && isKeyUp) {
        if (keyName == _pressedKeysStr) _pressedKeysStr.clear();
        else {
            for (const auto& opt : info.options) {
                if (opt == _pressedKeysStr) { _pressedKeysStr.clear(); break; }
            }
        }
    }

    bool isNumLock = (GetKeyState(VK_NUMLOCK) & 0x0001) != 0;

    bool isBlocked = !isInjected && ((!_pressedKeysStr.empty()) || (info.panel == "NumPad" && !isNumLock));
    std::stringstream ss;ss << "0x" << std::uppercase << std::hex << std::setw(2) << std::setfill('0') << vk;
    info.hexCode = ss.str();info.pressedKeysStr = _pressedKeysStr;info.blockStatus = isBlocked ? "Blocked" : "No blocked";
    // Обновляем общий слепок данных для фонового потока
    _lastInfo = info;// Стираем клавишу только после фиксации в _lastInfo, чтобы событие Up зафиксировало конец
    if (isKeyUp && _startTimes.count(vk)) {_startTimes.erase(vk);}// Если кнопка нажата — будим фоновый поток для спама
    if (isKeyDown) {_cv.notify_one();}// Первичное событие мгновенно выбрасываем в поток
    printKeyInfo(info);if (isBlocked) return 1;return CallNextHookEx(nullptr, nCode, wParam, lParam);}