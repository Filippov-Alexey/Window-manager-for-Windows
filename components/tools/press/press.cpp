
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

#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <sstream>
#include <regex>
#pragma comment(lib, "user32.lib")

std::map<std::string, int> keyDictionary;

void PressKeyCombination(const std::vector<int>& keyCodes) {
    for (const int& keyCode : keyCodes) {
        INPUT input = { 0 };
        input.type = INPUT_KEYBOARD;
        input.ki.wVk = keyCode;
        SendInput(1, &input, sizeof(INPUT));
        std::cout << "Pressed key: " << keyCode << std::endl;
    }

    for (auto it = keyCodes.rbegin(); it != keyCodes.rend(); ++it) {
        INPUT input = { 0 };
        input.type = INPUT_KEYBOARD;
        input.ki.wVk = *it;
        input.ki.dwFlags = KEYEVENTF_KEYUP;
        SendInput(1, &input, sizeof(INPUT));
        std::cout << "Released key: " << *it << std::endl;
    }
}

void LoadKeyCodes(const std::string& fileName) {
        fs::path fullPath = GetExecutableDir() / fileName;
        std::ifstream file(fullPath);
        if (!file.is_open()) {
            std::cerr << "Could not open the file: " << fullPath << std::endl;
            return;
        }

        std::string line;
        int value;


        while (std::getline(file, line)) {
            std::istringstream iss(line);


            if (line.find('\'') != std::string::npos) {
                size_t start = line.find('\'') + 1;
                size_t end = line.find('\'', start);
                std::string key = line.substr(start, end - start);

                if (line.find("0x") != std::string::npos) {
                    size_t start = line.find("0x") + 2;
                    std::stringstream ss(line.substr(start));
                    ss >> std::hex >> value;
                     

                    keyDictionary[key] = value;
                }
            }
        }

        file.close();
    }

std::vector<int> ParseArguments(int argc, char* argv[], const std::map<std::string, int>& keyDictionary) {
    std::vector<int> keyCodes;

    for (int i = 1; i < argc; ++i) {
        std::string hotKey = argv[i];
        std::string cleanedKey = hotKey;
        
        if (cleanedKey.front() == '\'' && cleanedKey.back() == '\'') {
            cleanedKey = cleanedKey.substr(1, cleanedKey.size() - 2);
        }

        std::vector<std::string> components;
        std::string delimiter = "+";
        size_t pos = 0;
        
        while ((pos = cleanedKey.find(delimiter)) != std::string::npos) {
            components.push_back(cleanedKey.substr(0, pos));
            cleanedKey.erase(0, pos + delimiter.length());
        }
        components.push_back(cleanedKey); 
        for (const auto& component : components) {
            auto it = keyDictionary.find(component);
            if (it != keyDictionary.end()) {
                keyCodes.push_back(it->second);
            } else {
                std::cerr << "Error: Invalid key \"" << component << "\"." << std::endl;
                return {};
            }
        }
    }

    return keyCodes;
}

int main(int argc, char* argv[]) {

    LoadKeyCodes("key_code.txt");

    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " '<key1+key2>' '<key3+key4>' ..." << std::endl;
        return 1;
    }

    std::vector<int> keyCodes = ParseArguments(argc, argv, keyDictionary);
    if (keyCodes.empty()) {
        return 1;
    }

    PressKeyCombination(keyCodes);

    std::cout << "Done!" << std::endl;

    return 0;
}
