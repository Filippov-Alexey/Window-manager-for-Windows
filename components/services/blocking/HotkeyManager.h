#pragma once
#include "AppConfig.h"
#include "KeyDictionary.h"
#include <unordered_set>
#include <string>
#include <vector>

class HotkeyManager {
public:
    void parseArguments(int argc, char* argv[]);
    bool isHotkeyBlocked(const std::string& combination) const;
    
    void processKeyModifier(std::string& keyName, const char prefix, std::vector<std::string>& modifierKeys);
    
    void processKeyName(std::string keyName, const std::unordered_set<int>& pressedKeys, 
                        const KeyDictionary& dict, const std::string& pressedKeysStr, 
                        std::vector<std::string>& outOptions);
    
    void processOptions(std::vector<std::string>& options, const std::string& pressedKeysStr);

private:
    void generatePermutations(const std::vector<std::string>& keys, std::vector<std::string>& results, size_t start);
    void separateModifiersAndNonModifiers(const std::string& keyname, const std::unordered_set<int>& vk_key, 
                                          const KeyDictionary& dict, std::vector<int>& vk, 
                                          std::unordered_set<int>& modifiers, std::unordered_set<int>& nonModifiers);
    
    void trimOptions(std::vector<std::string>& options, const std::string& keyName);
    void addOptions(const std::vector<std::string>& modifiers, const std::string& keyName, std::vector<std::string>& options);
    void addComplexOptions(const std::vector<std::string>& firstModifier, const std::vector<std::string>& secondModifier, const std::string& keyName, std::vector<std::string>& options);
    void addComplexOptions1(const std::vector<std::string>& firstModifier, const std::vector<std::string>& secondModifier, const std::vector<std::string>& thirdModifier, const std::string& keyName, std::vector<std::string>& options);

    std::vector<Hotkey> _hotkeysToBlock;
};
