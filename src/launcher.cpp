#include <windows.h>
#include <shellapi.h>
#include <filesystem>
#include <string>

static std::wstring Quote(const std::wstring& argument) {
    std::wstring result = L"\"";
    size_t slashes = 0;
    for (wchar_t character : argument) {
        if (character == L'\\') {
            ++slashes;
        } else {
            result.append(slashes * (character == L'"' ? 2 : 1), L'\\');
            slashes = 0;
            if (character == L'"') result += L'\\';
            result += character;
        }
    }
    result.append(slashes * 2, L'\\');
    return result + L'"';
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    wchar_t filename[32768];
    const DWORD length = GetModuleFileNameW(nullptr, filename, 32768);
    if (length == 0 || length >= 32768) return 21;
    const auto root = std::filesystem::path(filename).parent_path();
    const auto python = root / L"python" / L"python.exe";
    const auto script = root / L"app" / L"twin_snakes.py";
    if (!std::filesystem::is_regular_file(python) || !std::filesystem::is_regular_file(script)) {
        MessageBoxW(nullptr, L"Extract the complete Twin Snakes package before starting it.", L"Twin Snakes Recomp", MB_ICONERROR);
        return 21;
    }
    int count = 0;
    auto arguments = CommandLineToArgvW(GetCommandLineW(), &count);
    if (!arguments) return 21;
    std::wstring command = Quote(python.wstring()) + L" " + Quote(script.wstring());
    for (int index = 1; index < count; ++index) command += L" " + Quote(arguments[index]);
    if (count == 1) command += L" --gui";
    LocalFree(arguments);
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    // RecompLauncher captures progress from the inherited standard handles.
    if (GetStdHandle(STD_OUTPUT_HANDLE) != nullptr && GetStdHandle(STD_OUTPUT_HANDLE) != INVALID_HANDLE_VALUE) {
        startup.dwFlags = STARTF_USESTDHANDLES;
        startup.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
        startup.hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
        startup.hStdError = GetStdHandle(STD_ERROR_HANDLE);
    }
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(python.c_str(), command.data(), nullptr, nullptr, TRUE, CREATE_NO_WINDOW,
                        nullptr, root.c_str(), &startup, &process)) return 21;
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD code = 21;
    GetExitCodeProcess(process.hProcess, &code);
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return static_cast<int>(code);
}
