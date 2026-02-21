#include <windows.h>
#include <thread>
#include <chrono>
#include <random>

void physicalRightClick() {
    INPUT input = {0};
    input.type = INPUT_MOUSE;
    input.mi.dwFlags = MOUSEEVENTF_RIGHTDOWN;
    SendInput(1, &input, sizeof(INPUT));

    // Случайная задержка 30-70 мс
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(30, 70);
    std::this_thread::sleep_for(std::chrono::milliseconds(dis(gen)));

    input.mi.dwFlags = MOUSEEVENTF_RIGHTUP;
    SendInput(1, &input, sizeof(INPUT));
}
void main(){
    physicalRightClick();
}