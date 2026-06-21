#pragma once
#include <string>
#include <vector>

struct Hotkey {
    std::string combination;
    bool isBlocked = true;
};

struct KeyStateInfo {
    std::string hexCode;
    std::string keyName;
    std::string registerKey;
    std::string status;
    unsigned long duration = 0;
    std::vector<std::string> options;
    std::string blockStatus;
    std::string injectionType;
    std::string currentLayout;
    std::string panel;
    std::string pressedKeysStr;
    std::string pressedKeysTime; // Новое поле для списка "имя : время"
};
