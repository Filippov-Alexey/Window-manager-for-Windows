#pragma once
#include <string>
#include <unordered_map>
#include <filesystem>

class KeyDictionary {
public:
    bool loadFromFile(const std::filesystem::path& executableDir, const std::string& fileName);
    std::string getName(int vkCode) const;
    int getCodeByName(const std::string& name) const;
    bool hasCode(int vkCode) const;

private:
    std::unordered_map<int, std::string> _dict;
};
