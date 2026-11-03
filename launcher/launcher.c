/*
 * 单实例启动器：已有实例时只发激活消息，不重复启动主程序
 *
 * 与应用侧 core/single_instance.py 共用同一套约定：
 *   - 实例键 = FNV-1a 64(小写程序目录的 UTF-8 字节)，格式化为 16 位十六进制
 *   - 通道   = Windows 命名管道 \\.\pipe\color_card_<key>
 *   - 消息   = 一行 "activate\n"
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

/* 构建时由 launcher_config.h 提供；本地直接编译时使用默认名 */
#if defined(__has_include)
#if __has_include("launcher_config.h")
#include "launcher_config.h"
#endif
#endif
#ifndef MAIN_EXE_NAME
#define MAIN_EXE_NAME L"Color Card.exe"
#endif

#define ACTIVATE_MESSAGE "activate\n"
#define PIPE_PREFIX L"\\\\.\\pipe\\color_card_"
#define FNV_OFFSET 0xcbf29ce484222325ULL
#define FNV_PRIME 0x100000001b3ULL
#define MAX_PATH_LONG 32768
#define PIPE_WAIT_MS 200

/* 只折叠 ASCII 大写：CharLowerBuffW 受当前区域设置影响，会与 Python 端映射不一致 */
static void ascii_lower(wchar_t *text)
{
    for (; *text != L'\0'; text++) {
        if (*text >= L'A' && *text <= L'Z') {
            *text = *text - L'A' + L'a';
        }
    }
}

static uint64_t fnv1a_utf8(const wchar_t *text)
{
    char *utf8;
    int size;
    int i;
    uint64_t value = FNV_OFFSET;

    size = WideCharToMultiByte(CP_UTF8, 0, text, -1, NULL, 0, NULL, NULL);
    if (size <= 0) {
        return value;
    }
    utf8 = (char *)malloc((size_t)size);
    if (utf8 == NULL) {
        return value;
    }
    WideCharToMultiByte(CP_UTF8, 0, text, -1, utf8, size, NULL, NULL);

    for (i = 0; i < size - 1; i++) {
        value = (value ^ (uint64_t)(unsigned char)utf8[i]) * FNV_PRIME;
    }
    free(utf8);
    return value;
}

/* 取程序目录：优先用文件句柄拿到规范化路径，与应用侧 Path.resolve() 对齐 */
static BOOL get_program_root(wchar_t *root)
{
    wchar_t path[MAX_PATH_LONG];
    wchar_t final_path[MAX_PATH_LONG];
    DWORD length;
    HANDLE file;
    wchar_t *slash;

    length = GetModuleFileNameW(NULL, path, MAX_PATH_LONG);
    if (length == 0 || length >= MAX_PATH_LONG) {
        return FALSE;
    }

    file = CreateFileW(path, 0, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                       NULL, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, NULL);
    if (file != INVALID_HANDLE_VALUE) {
        length = GetFinalPathNameByHandleW(file, final_path, MAX_PATH_LONG, VOLUME_NAME_DOS);
        CloseHandle(file);
        if (length > 0 && length < MAX_PATH_LONG) {
            if (wcsncmp(final_path, L"\\\\?\\UNC\\", 8) == 0) {
                wcscpy_s(path, MAX_PATH_LONG, L"\\\\");
                wcsncat_s(path, MAX_PATH_LONG, final_path + 8,
                          MAX_PATH_LONG - wcslen(path) - 1);
            } else if (wcsncmp(final_path, L"\\\\?\\", 4) == 0) {
                wcscpy_s(path, MAX_PATH_LONG, final_path + 4);
            } else {
                wcscpy_s(path, MAX_PATH_LONG, final_path);
            }
        }
    }

    slash = wcsrchr(path, L'\\');
    if (slash == NULL || slash == path + 2) {
        /* 位于驱动器根目录：保留 "X:\" */
        if (slash == path + 2) {
            slash[1] = L'\0';
        } else {
            return FALSE;
        }
    } else {
        *slash = L'\0';
    }

    wcscpy_s(root, MAX_PATH_LONG, path);
    return TRUE;
}

static BOOL notify_running_instance(const wchar_t *root)
{
    wchar_t pipe_name[MAX_PATH_LONG];
    wchar_t key_text[MAX_PATH_LONG];
    HANDLE pipe;
    DWORD written = 0;
    uint64_t key;

    /* 键按小写路径计算，与应用侧一致；启动路径保留原始大小写 */
    wcscpy_s(key_text, MAX_PATH_LONG, root);
    ascii_lower(key_text);
    key = fnv1a_utf8(key_text);

    swprintf_s(pipe_name, MAX_PATH_LONG, L"%s%016llx", PIPE_PREFIX, (unsigned long long)key);

    pipe = CreateFileW(pipe_name, GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
    if (pipe == INVALID_HANDLE_VALUE && GetLastError() == ERROR_PIPE_BUSY) {
        WaitNamedPipeW(pipe_name, PIPE_WAIT_MS);
        pipe = CreateFileW(pipe_name, GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
    }
    if (pipe == INVALID_HANDLE_VALUE) {
        return FALSE;
    }

    if (!WriteFile(pipe, ACTIVATE_MESSAGE, (DWORD)strlen(ACTIVATE_MESSAGE), &written, NULL)
        || written < (DWORD)strlen(ACTIVATE_MESSAGE)) {
        CloseHandle(pipe);
        return FALSE;
    }

    CloseHandle(pipe);
    return TRUE;
}

static void launch_main(const wchar_t *root, int argc, wchar_t **argv)
{
    wchar_t main_path[MAX_PATH_LONG];
    wchar_t command_line[MAX_PATH_LONG];
    STARTUPINFOW startup_info;
    PROCESS_INFORMATION process_info;
    BOOL started;

    if (root[wcslen(root) - 1] == L'\\') {
        swprintf_s(main_path, MAX_PATH_LONG, L"%s%s", root, MAIN_EXE_NAME);
    } else {
        swprintf_s(main_path, MAX_PATH_LONG, L"%s\\%s", root, MAIN_EXE_NAME);
    }

    swprintf_s(command_line, MAX_PATH_LONG, L"\"%s\"", main_path);
    for (int i = 1; i < argc; i++) {
        wcsncat_s(command_line, MAX_PATH_LONG, L" \"", 2);
        wcsncat_s(command_line, MAX_PATH_LONG, argv[i], MAX_PATH_LONG - wcslen(command_line) - 2);
        wcsncat_s(command_line, MAX_PATH_LONG, L"\"", 1);
    }

    ZeroMemory(&startup_info, sizeof(startup_info));
    startup_info.cb = sizeof(startup_info);
    ZeroMemory(&process_info, sizeof(process_info));

    started = CreateProcessW(NULL, command_line, NULL, NULL, FALSE,
                             DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                             NULL, root, &startup_info, &process_info);
    if (started) {
        CloseHandle(process_info.hThread);
        CloseHandle(process_info.hProcess);
        return;
    }

    MessageBoxW(NULL, L"未找到主程序，请确认启动器与主程序在同一目录。",
                L"取色卡", MB_ICONERROR | MB_OK);
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, LPWSTR command_line, int show)
{
    wchar_t root[MAX_PATH_LONG];
    int argc = 0;
    wchar_t **argv;
    BOOL notified;

    (void)instance;
    (void)previous;
    (void)command_line;
    (void)show;

    if (!get_program_root(root)) {
        return 1;
    }

    argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (argv == NULL) {
        return 1;
    }

    /* 带参数时不激活，直接转交主程序（保留 --uninstall 等命令行语义） */
    notified = (argc <= 1) && notify_running_instance(root);
    if (!notified) {
        launch_main(root, argc, argv);
    }

    LocalFree(argv);
    return 0;
}
