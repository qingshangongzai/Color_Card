/*
 * 便携版根目录入口：拉起 app\Color Card.exe
 *
 * onedir 的运行库必须与主程序同目录，因此主程序整体放在 app\ 子目录；
 * 本程序只负责从所在目录定位 app\Color Card.exe 并启动，单实例激活由主程序负责。
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <strsafe.h>
#include <wchar.h>

#define MAX_PATH_LONG 32768
#define APP_DIR_NAME L"app"
#define APP_EXE_NAME L"Color Card.exe"

static void show_error(const wchar_t *detail)
{
    wchar_t message[512];

    StringCchPrintfW(message, ARRAYSIZE(message), L"启动取色卡失败：\n%s", detail);
    MessageBoxW(NULL, message, L"取色卡", MB_ICONERROR);
}

/* 错误码单独拼进提示，避免把定位路径与错误码混在同一个格式串里 */
static void show_launch_error(const wchar_t *app_path, INT_PTR code)
{
    wchar_t detail[MAX_PATH_LONG + 64];

    StringCchPrintfW(detail, ARRAYSIZE(detail), L"%s\n错误码: %lld", app_path, (long long)code);
    show_error(detail);
}

/* 把自身命令行参数拼成带引号的参数字符串，保留 --uninstall 等语义 */
static void build_parameters(wchar_t *parameters, size_t size)
{
    int argc = 0;
    wchar_t **argv = CommandLineToArgvW(GetCommandLineW(), &argc);

    parameters[0] = L'\0';
    if (argv == NULL) {
        return;
    }

    for (int index = 1; index < argc; index++) {
        if (parameters[0] != L'\0') {
            StringCchCatW(parameters, size, L" ");
        }
        StringCchCatW(parameters, size, L"\"");
        StringCchCatW(parameters, size, argv[index]);
        StringCchCatW(parameters, size, L"\"");
    }

    LocalFree(argv);
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR command_line, int show)
{
    wchar_t root[MAX_PATH_LONG];
    wchar_t app_dir[MAX_PATH_LONG];
    wchar_t app_path[MAX_PATH_LONG];
    wchar_t parameters[MAX_PATH_LONG];
    wchar_t *slash;
    DWORD length;
    HINSTANCE result;

    (void)instance;
    (void)previous;
    (void)command_line;
    (void)show;

    length = GetModuleFileNameW(NULL, root, MAX_PATH_LONG);
    if (length == 0 || length >= MAX_PATH_LONG) {
        show_error(L"无法定位程序所在目录");
        return 1;
    }

    slash = wcsrchr(root, L'\\');
    if (slash == NULL) {
        show_error(L"无法解析程序所在目录");
        return 1;
    }
    *slash = L'\0';

    if (FAILED(StringCchPrintfW(app_dir, ARRAYSIZE(app_dir), L"%s\\%s", root, APP_DIR_NAME)) ||
        FAILED(StringCchPrintfW(app_path, ARRAYSIZE(app_path), L"%s\\%s", app_dir, APP_EXE_NAME))) {
        show_error(L"程序路径过长");
        return 1;
    }

    build_parameters(parameters, ARRAYSIZE(parameters));

    result = ShellExecuteW(NULL, L"open", app_path,
                           parameters[0] != L'\0' ? parameters : NULL,
                           app_dir, SW_SHOWNORMAL);
    if ((INT_PTR)result <= 32) {
        show_launch_error(app_path, (INT_PTR)result);
        return 1;
    }

    return 0;
}
