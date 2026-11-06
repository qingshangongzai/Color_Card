"""单实例保护，防止同一程序目录被重复启动"""

# 标准库导入
import sys
from enum import Enum
from pathlib import Path

# 第三方库导入
from PySide6.QtCore import QLockFile, QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

# 项目模块导入
from instance_key import (
    compute_instance_key,
    get_key_dir,
    get_lock_path,
    get_server_name,
)

from .logger import get_logger

logger = get_logger("single_instance")

ACTIVATE_MESSAGE = b"activate\n"  # 副实例发给主实例的激活指令
NOTIFY_TIMEOUT_MS = 500  # 连接与读写的等待上限，超时不影响启动


class SingleInstanceResult(Enum):
    """单实例检查结果"""
    PRIMARY = "primary"  # 已持有锁，当前进程为主实例
    SECONDARY = "secondary"  # 已有实例在运行，当前进程应退出
    BYPASS = "bypass"  # 锁不可用，跳过单实例保护继续启动


class SingleInstanceGuard(QObject):
    """单实例守卫，持有进程锁并接收副实例的激活消息"""

    activation_requested = Signal()  # 信号：副实例请求激活主窗口

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lock: QLockFile | None = None
        self._server: QLocalServer | None = None
        self._server_name = ""

    def acquire(self) -> SingleInstanceResult:
        """尝试获取主实例身份

        只依赖 QtCore / QtNetwork（通知已有实例时使用 QLocalSocket），不依赖
        QApplication 与 QtWidgets，可在创建 QApplication 之前调用；主实例的监听由
        start_server() 在 QApplication 创建后启动。

        Returns:
            SingleInstanceResult: 主实例 / 副实例 / 跳过保护
        """
        program_root = Path(sys.argv[0]).resolve().parent
        instance_key = compute_instance_key(program_root)
        self._server_name = get_server_name(instance_key)

        key_dir = get_key_dir()
        lock_path = get_lock_path(instance_key)
        try:
            key_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"单实例锁目录不可用，跳过保护: path={key_dir}, error={e}")
            return SingleInstanceResult.BYPASS

        lock = QLockFile(str(lock_path))
        self._lock = lock  # 持有引用，进程存活期间保持锁
        if not lock.tryLock(0):
            lock_info = lock.getLockInfo()
            pid = lock_info[0] if lock_info else 0
            if pid:
                logger.info(f"检测到已有实例，通知后退出: pid={pid}, key={instance_key}")
                self._notify_primary()
                return SingleInstanceResult.SECONDARY
            logger.warning(
                f"单实例锁不可用，跳过保护: path={lock_path}, error={lock.error()}"
            )
            return SingleInstanceResult.BYPASS

        logger.info(f"已获取主实例锁: path={lock_path}")
        return SingleInstanceResult.PRIMARY

    def _notify_primary(self) -> None:
        """通知主实例激活窗口"""
        socket = QLocalSocket(self)
        socket.connectToServer(self._server_name)
        if not socket.waitForConnected(NOTIFY_TIMEOUT_MS):
            logger.warning(f"连接主实例失败，无法激活窗口: error={socket.errorString()}")
            return
        socket.write(ACTIVATE_MESSAGE)
        socket.flush()
        socket.waitForDisconnected(NOTIFY_TIMEOUT_MS)

    def start_server(self) -> None:
        """启动监听，接收副实例消息

        需在 QApplication 创建后调用：QLocalServer 的 newConnection 依赖事件循环。
        """
        server = QLocalServer(self)
        server.newConnection.connect(self._on_new_connection)
        # listen 前必须先清理异常退出留下的服务名
        server.removeServer(self._server_name)
        if not server.listen(self._server_name):
            logger.warning(
                f"单实例监听失败，副实例将无法激活窗口: error={server.errorString()}"
            )
        self._server = server

    def _on_new_connection(self) -> None:
        """处理副实例连接，读走消息后发出激活信号"""
        server = self._server
        if server is None:
            return
        while server.hasPendingConnections():
            socket = server.nextPendingConnection()
            if socket is None:
                continue
            socket.waitForReadyRead(NOTIFY_TIMEOUT_MS)
            socket.readAll()
            socket.disconnectFromServer()
            self.activation_requested.emit()
