#pragma once
#include <string>
#include <mutex>
#include <atomic>
#include <windows.h>

class LanguageMonitor {
public:
    LanguageMonitor();
    ~LanguageMonitor();

    void startPipeListener();
    void updateInitialLanguage();
    std::string getCurrentInfo();

private:
    std::string _currentInfo;
    std::mutex _mutex;
    std::atomic<bool> _running;
};
