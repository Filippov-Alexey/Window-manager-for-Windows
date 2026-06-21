#pragma once
#include <windows.h>
#include "KeyDictionary.h"
#include "HotkeyManager.h"
#include "LanguageMonitor.h"
#include <unordered_map>
#include <unordered_set>
#include <string>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <atomic>

class KeyboardHook {
public:
    static void initialize(KeyDictionary* dict, HotkeyManager* hm, LanguageMonitor* lm);
    static LRESULT CALLBACK hookCallback(int nCode, WPARAM wParam, LPARAM lParam);
    static void shutdown(); // Метод для корректной остановки потока при выходе

private:
    static std::string jsonEscape(const std::string& s);
    static void printKeyInfo(const KeyStateInfo& info);
    static void syncKeyState();
    static std::string toUtf8(const std::wstring& wstr);
    
    // Функция фонового цикла спама
    static void startTickerLoop(); 

    static KeyDictionary* _dict;
    static HotkeyManager* _hm;
    static LanguageMonitor* _lm;
    static std::unordered_map<int, DWORD> _startTimes;
    static std::unordered_set<int> _currentlyPressedKeys;
    static std::string _pressedKeysStr;

    // === НОВЫЕ СТАТИЧЕСКИЕ ЧЛЕНЫ ДЛЯ ПОТОКА СПАМА ===
    static std::thread _tickerThread;
    static std::mutex _hookMutex;
    static std::condition_variable _cv;
    static std::atomic<bool> _running;
    static KeyStateInfo _lastInfo; // Шаблон для генерации непрерывного вывода
};
