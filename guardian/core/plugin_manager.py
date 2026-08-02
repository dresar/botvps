"""Plugin Manager — discovery, loading, dan lifecycle management plugin."""

import importlib
import pkgutil
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Coroutine

import structlog

from guardian.core.exceptions import (
    PluginAlreadyRegisteredError,
    PluginDependencyError,
    PluginLoadError,
    PluginNotFoundError,
    PluginSetupError,
)
from guardian.interfaces.base_plugin import BasePlugin

if TYPE_CHECKING:
    from guardian.core.engine import ApplicationContext

logger = structlog.get_logger(__name__)

CommandHandlerFn = Callable[..., Coroutine[Any, Any, None]]


@dataclass
class RegisteredCommand:
    """Informasi command yang terdaftar."""

    namespace: str
    command: str
    handler: CommandHandlerFn
    permissions: list[str]
    description: str


@dataclass
class RegisteredCallback:
    """Informasi callback yang terdaftar."""

    prefix: str
    handler: CommandHandlerFn


class PluginManager:
    """Mengelola lifecycle seluruh plugin Serverinka Guardian.

    Bertanggung jawab atas:
    - Menemukan plugin dari folder guardian/plugins/.
    - Memuat plugin dalam urutan dependency yang benar.
    - Menginisialisasi dan menghentikan plugin.
    - Menyediakan registry command dan callback.

    Args:
        disabled_plugins: Nama plugin yang dinonaktifkan.
    """

    def __init__(self, disabled_plugins: list[str] | None = None) -> None:
        self._plugins: dict[str, BasePlugin] = {}
        self._load_order: list[str] = []
        self._commands: dict[str, RegisteredCommand] = {}
        self._callbacks: list[RegisteredCallback] = []
        self._disabled = set(disabled_plugins or [])
        self._ctx: "ApplicationContext | None" = None

    def register_command(
        self,
        namespace: str,
        command: str,
        handler: CommandHandlerFn,
        permissions: list[str],
        description: str = "",
    ) -> None:
        """Daftarkan command handler ke registry.

        Args:
            namespace: Namespace plugin (misal "docker").
            command: Nama sub-command (misal "list", "restart").
            handler: Async function handler.
            permissions: List permission yang diperlukan.
            description: Deskripsi command untuk /help.

        Raises:
            PluginAlreadyRegisteredError: Jika command sudah terdaftar.
        """
        key = f"{namespace}:{command}"
        if key in self._commands:
            raise PluginAlreadyRegisteredError(
                f"Command '{key}' sudah terdaftar oleh plugin lain."
            )
        self._commands[key] = RegisteredCommand(
            namespace=namespace,
            command=command,
            handler=handler,
            permissions=permissions,
            description=description,
        )
        logger.debug("Command terdaftar.", key=key)

    def register_callback(self, prefix: str, handler: CommandHandlerFn) -> None:
        """Daftarkan callback query handler.

        Args:
            prefix: Prefix callback data, misal "docker" akan menangani
                    semua callback yang dimulai dengan "docker:".
            handler: Async function handler.
        """
        self._callbacks.append(RegisteredCallback(prefix=prefix, handler=handler))
        logger.debug("Callback handler terdaftar.", prefix=prefix)

    def get_command(self, namespace: str, command: str) -> RegisteredCommand | None:
        """Dapatkan registered command berdasarkan namespace dan command.

        Args:
            namespace: Namespace plugin.
            command: Nama command.

        Returns:
            RegisteredCommand atau None jika tidak ditemukan.
        """
        return self._commands.get(f"{namespace}:{command}")

    def get_callback_handler(self, callback_data: str) -> CommandHandlerFn | None:
        """Dapatkan handler untuk callback data.

        Args:
            callback_data: Data callback dari tombol inline keyboard.

        Returns:
            Handler function atau None.
        """
        for reg in self._callbacks:
            if callback_data.startswith(f"{reg.prefix}:") or callback_data == reg.prefix:
                return reg.handler
        return None

    def get_all_commands(self) -> list[RegisteredCommand]:
        """Dapatkan semua command yang terdaftar."""
        return list(self._commands.values())

    def get_plugin(self, name: str) -> BasePlugin:
        """Dapatkan plugin berdasarkan nama.

        Args:
            name: Nama plugin.

        Returns:
            BasePlugin instance.

        Raises:
            PluginNotFoundError: Jika plugin tidak ditemukan.
        """
        if name not in self._plugins:
            raise PluginNotFoundError(f"Plugin '{name}' tidak ditemukan.")
        return self._plugins[name]

    async def discover_and_load(self, ctx: "ApplicationContext") -> None:
        """Temukan dan muat semua plugin dari folder guardian/plugins/.

        Args:
            ctx: ApplicationContext.

        Raises:
            PluginLoadError: Jika plugin gagal dimuat.
        """
        self._ctx = ctx
        discovered = self._discover_plugins()

        if not discovered:
            logger.warning("Tidak ada plugin yang ditemukan.")
            return

        logger.info(
            "Plugin ditemukan.",
            count=len(discovered),
            names=[p.name for p in discovered],
        )

        sorted_plugins = self._resolve_load_order(discovered)
        await self._setup_plugins(sorted_plugins, ctx)

    def _discover_plugins(self) -> list[BasePlugin]:
        """Temukan semua plugin dengan auto-discovery."""
        import guardian.plugins as plugins_package

        discovered: list[BasePlugin] = []

        for _, module_name, is_pkg in pkgutil.iter_modules(plugins_package.__path__):
            if not is_pkg or module_name in self._disabled:
                if module_name in self._disabled:
                    logger.info("Plugin dinonaktifkan.", name=module_name)
                continue

            try:
                module = importlib.import_module(f"guardian.plugins.{module_name}.plugin")
                plugin_class = self._find_plugin_class(module)
                if plugin_class:
                    plugin = plugin_class()
                    discovered.append(plugin)
                    logger.debug("Plugin ditemukan.", name=plugin.name)
            except ImportError as e:
                raise PluginLoadError(
                    f"Gagal mengimport plugin '{module_name}': {e}",
                    detail=str(e),
                ) from e
            except Exception as e:
                raise PluginLoadError(
                    f"Gagal memuat plugin '{module_name}': {e}",
                    detail=str(e),
                ) from e

        return discovered

    def _find_plugin_class(self, module: object) -> type[BasePlugin] | None:
        """Temukan class plugin di dalam module."""
        import inspect
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BasePlugin)
                and obj is not BasePlugin
                and not getattr(obj, "__abstractmethods__", None)
            ):
                return obj
        return None

    def _resolve_load_order(self, plugins: list[BasePlugin]) -> list[BasePlugin]:
        """Urutkan plugin berdasarkan dependency (topological sort).

        Args:
            plugins: List plugin yang belum diurutkan.

        Returns:
            List plugin yang sudah diurutkan.

        Raises:
            PluginDependencyError: Jika ada dependensi yang tidak terpenuhi.
        """
        plugin_map = {p.name: p for p in plugins}

        for plugin in plugins:
            for dep in plugin.dependencies:
                if dep not in plugin_map:
                    raise PluginDependencyError(
                        f"Plugin '{plugin.name}' memerlukan '{dep}' yang tidak tersedia."
                    )

        visited: set[str] = set()
        sorted_list: list[BasePlugin] = []
        visiting: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                raise PluginDependencyError(f"Circular dependency terdeteksi di plugin '{name}'.")
            if name in visited:
                return
            visiting.add(name)
            plugin = plugin_map[name]
            for dep in plugin.dependencies:
                visit(dep)
            visiting.remove(name)
            visited.add(name)
            sorted_list.append(plugin)

        for p in plugins:
            visit(p.name)

        return sorted_list

    async def _setup_plugins(
        self, plugins: list[BasePlugin], ctx: "ApplicationContext"
    ) -> None:
        """Panggil setup() untuk setiap plugin secara berurutan."""
        for plugin in plugins:
            try:
                logger.info("Memuat plugin...", name=plugin.name, version=plugin.version)
                await plugin.setup(ctx)
                self._plugins[plugin.name] = plugin
                self._load_order.append(plugin.name)
                logger.info("Plugin berhasil dimuat.", name=plugin.name)

                await ctx.event_bus.publish(
                    "system.plugin_loaded", {"plugin_name": plugin.name}
                )
            except Exception as e:
                logger.exception("Plugin gagal dimuat. Dilewati.", name=plugin.name, error=str(e))
                await ctx.event_bus.publish(
                    "system.plugin_error",
                    {"plugin_name": plugin.name, "error": str(e)},
                )

    async def teardown_all(self) -> None:
        """Hentikan semua plugin dalam urutan terbalik."""
        for name in reversed(self._load_order):
            plugin = self._plugins.get(name)
            if plugin:
                try:
                    await plugin.teardown()
                    logger.info("Plugin dihentikan.", name=name)
                except Exception:
                    logger.exception("Error saat menghentikan plugin.", name=name)

    @property
    def loaded_plugins(self) -> list[str]:
        """Nama plugin yang berhasil dimuat."""
        return list(self._load_order)
