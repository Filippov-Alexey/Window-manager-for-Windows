#include "HotkeyManager.h"
#include <sstream>
#include <algorithm>

void HotkeyManager::generatePermutations(const std::vector<std::string>& keys, std::vector<std::string>& results, size_t start) {
    if (start == keys.size() - 1) {
        std::string perm;
        for (const auto& key : keys) {
            if (!perm.empty()) perm += "+";
            perm += key;
        }
        results.push_back(perm);
        return;
    }
    for (size_t i = start; i < keys.size(); ++i) {
        std::vector<std::string> temp = keys;
        std::swap(temp[start], temp[i]);
        generatePermutations(temp, results, start + 1);
    }
}

void HotkeyManager::parseArguments(int argc, char* argv[]) {
    for (int i = 1; i < argc; ++i) {
        std::string combination = argv[i];
        _hotkeysToBlock.push_back({ combination, true });

        std::istringstream ss(combination);
        std::vector<std::string> keys;
        std::string token;
        while (std::getline(ss, token, '+')) {
            keys.push_back(token);
        }

        std::vector<std::string> perms;
        generatePermutations(keys, perms, 0);
        for (const auto& perm : perms) {
            if (perm != combination) {
                _hotkeysToBlock.push_back({ perm, true });
            }
        }
    }
}

bool HotkeyManager::isHotkeyBlocked(const std::string& combination) const {
    return std::any_of(_hotkeysToBlock.begin(), _hotkeysToBlock.end(),
        [&combination](const Hotkey& hk) { return hk.combination == combination; });
}

void HotkeyManager::processKeyModifier(std::string& keyName, const char prefix, std::vector<std::string>& modifierKeys) {
    if (!keyName.empty() && keyName.front() == prefix) {
        keyName.erase(0, 1); 
        if (std::find(modifierKeys.begin(), modifierKeys.end(), keyName) == modifierKeys.end()) {
            modifierKeys.push_back(keyName);
        }
    }
}

void HotkeyManager::separateModifiersAndNonModifiers(const std::string& keyname, const std::unordered_set<int>& vk_key, 
                                                     const KeyDictionary& dict, std::vector<int>& vk, 
                                                     std::unordered_set<int>& modifiers, std::unordered_set<int>& nonModifiers) {
    bool keyFound = false;
    for (int key : vk_key) {
        std::string keyName = dict.hasCode(key) ? dict.getName(key) : "";
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
        int keyCode = dict.getCodeByName(keyname);
        if (keyCode != 0) {
            nonModifiers.insert(keyCode);
        }
    }
    vk.insert(vk.end(), modifiers.begin(), modifiers.end());
    vk.insert(vk.end(), nonModifiers.begin(), nonModifiers.end());
}

void HotkeyManager::trimOptions(std::vector<std::string>& options, const std::string& keyName) {
    options.erase(
        std::remove_if(options.begin(), options.end(),
                       [&keyName](const std::string& s) { return s.find(keyName) == std::string::npos; }),
        options.end()
    );
}

void HotkeyManager::addOptions(const std::vector<std::string>& modifiers, const std::string& keyName, std::vector<std::string>& options) {
    for (const auto& modifier : modifiers) {
        if (modifier != keyName) {
            options.push_back(modifier + "+" + keyName);
        }
    }
    trimOptions(options, keyName);
}

void HotkeyManager::addComplexOptions(const std::vector<std::string>& firstModifier, const std::vector<std::string>& secondModifier, const std::string& keyName, std::vector<std::string>& options) {
    for (const auto& first : firstModifier) {
        if (first == keyName) continue;
        for (const auto& second : secondModifier) {
            if (second == keyName) continue;
            options.push_back(first + "+" + second + "+" + keyName);
        }
    }
    trimOptions(options, keyName);
}

void HotkeyManager::addComplexOptions1(const std::vector<std::string>& firstModifier, const std::vector<std::string>& secondModifier, const std::vector<std::string>& thirdModifier, const std::string& keyName, std::vector<std::string>& options) {
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
    trimOptions(options, keyName);
}

template<typename ContainerType>
void replace_all(ContainerType& container, typename ContainerType::value_type old_val, typename ContainerType::value_type new_val) {
    for(auto it = container.begin(); it != container.end(); ++it) {
        if(*it == old_val)
            *it = new_val;
    }
}

void HotkeyManager::processKeyName(std::string keyName, const std::unordered_set<int>& pressedKeys, 
                                    const KeyDictionary& dict, const std::string& pressedKeysStr, 
                                    std::vector<std::string>& outOptions) {
    std::vector<int> vk; 
    std::unordered_set<int> modifiers; 
    std::unordered_set<int> nonModifiers;

    outOptions.clear(); 
    separateModifiersAndNonModifiers(keyName, pressedKeys, dict, vk, modifiers, nonModifiers);

    const int left_alt = 0x12;
    const int alt = 0xa4;
    const int right_alt = 0xa5;
    if(std::find(vk.begin(), vk.end(), left_alt) != vk.end() &&
       std::find(vk.begin(), vk.end(), right_alt) != vk.end()) {
        replace_all(vk, left_alt, alt);
    }

    std::vector<std::string> pressShift;
    std::vector<std::string> pressCtrl;
    std::vector<std::string> pressAlt;

    for (int key : vk) {
        std::string currentKeyName = dict.hasCode(key) ? dict.getName(key) : "";
        
        if (!currentKeyName.empty()) {
            processKeyModifier(currentKeyName, '=', pressShift);
            processKeyModifier(currentKeyName, '_', pressCtrl);
            processKeyModifier(currentKeyName, '-', pressAlt);
            
            bool hasShift = !pressShift.empty();
            bool hasCtrl = !pressCtrl.empty();
            bool hasAlt = !pressAlt.empty();
            
            if (hasShift && !hasCtrl && !hasAlt) {
                addOptions(pressShift, currentKeyName, outOptions);
            } else if (!hasShift && hasCtrl && !hasAlt) {
                addOptions(pressCtrl, currentKeyName, outOptions);
            } else if (!hasShift && !hasCtrl && hasAlt) {
                addOptions(pressAlt, currentKeyName, outOptions);
            } else if (hasShift && hasCtrl && !hasAlt) {
                addComplexOptions(pressShift, pressCtrl, currentKeyName, outOptions);
            } else if (hasShift && !hasCtrl && hasAlt) {
                addComplexOptions(pressShift, pressAlt, currentKeyName, outOptions);
            } else if (!hasShift && hasCtrl && hasAlt) {
                addComplexOptions(pressCtrl, pressAlt, currentKeyName, outOptions);
            } else if (hasShift && hasCtrl && hasAlt) {
                addComplexOptions1(pressShift, pressCtrl, pressAlt, currentKeyName, outOptions);
            } else {
                if (pressedKeysStr != currentKeyName)
                    outOptions.push_back(currentKeyName);
            }
        }
    }
}

void HotkeyManager::processOptions(std::vector<std::string>& options, const std::string& pressedKeysStr) {
    if (options.empty()) return;
    if (!pressedKeysStr.empty()) {
        options.push_back(pressedKeysStr);
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
