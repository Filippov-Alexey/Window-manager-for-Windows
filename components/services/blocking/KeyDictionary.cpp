#include "KeyDictionary.h"
#include <fstream>
#include <algorithm>
#include <iostream>

bool KeyDictionary::loadFromFile(const std::filesystem::path& executableDir, const std::string& fileName) {
    std::ifstream file(executableDir / fileName);
    if (!file.is_open()) {
        std::cerr << "Error opening key code file: " << fileName << std::endl;
        return false;
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
                _dict[keyCode] = keyName;
            } catch (...) {}
        }
    }
    return true;
}

std::string KeyDictionary::getName(int vkCode) const {
    auto it = _dict.find(vkCode);
    return (it != _dict.end()) ? it->second : std::to_string(vkCode);
}

int KeyDictionary::getCodeByName(const std::string& name) const {
    for (const auto& [code, kName] : _dict) {
        if (kName == name) return code;
    }
    return 0;
}

bool KeyDictionary::hasCode(int vkCode) const {
    return _dict.find(vkCode) != _dict.end();
}
