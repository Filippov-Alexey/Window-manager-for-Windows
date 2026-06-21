cmake_minimum_required(VERSION 3.16)
project(KeyBlocker LANGUAGES CXX)

# Включаем поддержку стандарта C++17 (необходим для std::filesystem)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Собираем все исходные файлы проекта
set(SOURCES
    main.cpp
    KeyDictionary.cpp
    HotkeyManager.cpp
    LanguageMonitor.cpp
    KeyboardHook.cpp
)

set(HEADERS
    AppConfig.h
    KeyDictionary.h
    HotkeyManager.h
    LanguageMonitor.h
    KeyboardHook.h
)

# Создаем исполняемый файл (имя blocking.exe, как заложено в коде)
add_executable(blocking ${SOURCES} ${HEADERS})

# Лиdropим необходимые системные библиотеки Windows
target_link_libraries(blocking PRIVATE
    ole32
    user32
    advapi32
)

# Настройки для MSVC (отключаем предупреждения о старых функциях типа sprintf/sscanf)
if(MSVC)
    target_compile_definitions(blocking PRIVATE _CRT_SECURE_NO_WARNINGS)
endif()
