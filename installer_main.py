"""安装程序打包入口

Nuitka 打包时入口脚本必须位于项目根目录：若直接以 installer/main.py 作为入口，
编译产物不会执行其他顶层包（如 core）的 __init__，导致运行期 importing core 时
拿到空壳包、报 "cannot import name ..."。此处只做转发，实际逻辑仍在 installer/main.py。
"""

from installer.main import main

if __name__ == '__main__':
    main()
