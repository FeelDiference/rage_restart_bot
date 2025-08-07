"""
Основной модуль Telegram бота для управления Rage сервером.
Обрабатывает команды пользователей и взаимодействует с Docker контейнером.
"""

import asyncio
import time
from typing import Dict, Any
from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, CallbackContext
)
from telegram.constants import ParseMode
from loguru import logger

from src.utils.config import config_manager
from src.docker.manager import DockerManager, ContainerStatus
from src.monitoring.server_monitor import ServerMonitor, ServerHealth


class RageBot:
    """
    Telegram бот для управления Rage сервером в Docker контейнере.
    
    Attributes:
        application: Telegram bot application
        docker_manager: Менеджер Docker контейнера
        server_monitor: Монитор состояния сервера
        restart_limit: Лимит рестартов в час
        restart_history: История рестартов для контроля лимитов
    """
    
    def __init__(self):
        """
        Инициализация бота.
        """
        # Получаем конфигурацию
        self.telegram_config = config_manager.get_telegram_config()
        self.docker_config = config_manager.get_docker_config()
        self.security_config = config_manager.get_security_config()
        
        # Инициализируем компоненты
        self.docker_manager = DockerManager(
            container_name=config_manager.get_container_name(),
            restart_timeout=self.docker_config.get('restart_timeout', 30)
        )
        self.server_monitor = ServerMonitor()
        
        # Безопасность - лимиты рестартов
        self.restart_limit = self.security_config.get('max_restarts_per_hour', 10)
        self.restart_history: Dict[str, list] = {}  # user_id: [timestamps]
        
        # Создаем приложение
        self.application = Application.builder().token(
            config_manager.get_telegram_token()
        ).build()
        
        # Регистрируем обработчики
        self._register_handlers()
        
        logger.info("RageBot инициализирован")
    
    def _register_handlers(self):
        """
        Регистрирует обработчики команд и сообщений.
        """
        # Команды
        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(CommandHandler("help", self._cmd_help))
        self.application.add_handler(CommandHandler("status", self._cmd_status))
        self.application.add_handler(CommandHandler("restart", self._cmd_restart))
        self.application.add_handler(CommandHandler("stop", self._cmd_stop))
        self.application.add_handler(CommandHandler("start_server", self._cmd_start_server))
        self.application.add_handler(CommandHandler("logs", self._cmd_logs))
        self.application.add_handler(CommandHandler("info", self._cmd_info))
        self.application.add_handler(CommandHandler("players", self._cmd_players))
        
        # Фильтр для проверки авторизации
        self.application.add_handler(
            MessageHandler(filters.ALL, self._check_authorization),
            group=0  # Выполняется первым
        )
        
        logger.info("Обработчики команд зарегистрированы")
    
    async def _check_authorization(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Проверяет авторизацию пользователя/группы.
        
        Args:
            update: Обновление от Telegram
            context: Контекст бота
        """
        if not update.effective_chat or not update.effective_user:
            return
        
        chat_id = str(update.effective_chat.id)
        user_id = str(update.effective_user.id)
        
        # Проверяем авторизацию
        if not config_manager.is_chat_allowed(chat_id, user_id):
            await update.message.reply_text(
                "❌ У вас нет доступа к этому боту.\n"
                "Обратитесь к администратору для получения доступа."
            )
            logger.warning(f"Неавторизованный доступ: пользователь {user_id} в чате {chat_id}")
            return
    
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /start.
        """
        welcome_text = (
            "🤖 **Rage Server Bot**\n\n"
            "Я помогу вам управлять Rage сервером в Docker контейнере.\n\n"
            "**Доступные команды:**\n"
            "• /status - Проверить статус сервера\n"
            "• /restart - Перезапустить сервер\n"
            "• /stop - Остановить сервер\n"
            "• /start_server - Запустить сервер\n"
            "• /logs - Показать логи сервера\n"
            "• /info - Подробная информация о контейнере\n"
            "• /help - Показать справку\n\n"
            "🔒 Бот работает только в авторизованных группах."
        )
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"Команда /start от пользователя {update.effective_user.id}")
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /help.
        """
        help_text = (
            "🆘 **Справка по командам**\n\n"
            "**Управление сервером:**\n"
            "• `/status` - Проверить статус и доступность сервера\n"
            "• `/restart` - Перезапустить сервер (лимит: {}/час)\n"
            "• `/stop` - Остановить сервер\n"
            "• `/start_server` - Запустить остановленный сервер\n\n"
            "**Мониторинг:**\n"
            "• `/logs [строки]` - Показать последние логи (по умолчанию 20)\n"
            "• `/info` - Подробная информация о контейнере\n"
            "• `/players` - Список игроков онлайн\n\n"
            "**Статусы сервера:**\n"
            "• ✅ HEALTHY - Сервер работает нормально\n"
            "• ⚠️ DEGRADED - Сервер работает с проблемами\n"
            "• ❌ UNHEALTHY - Сервер не работает\n"
            "• 🔄 STARTING - Сервер запускается\n\n"
            "**Безопасность:**\n"
            "• Команды доступны только в авторизованных группах\n"
            "• Ограничение на количество рестартов в час\n"
            "• Все действия логируются"
        ).format(self.restart_limit)
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /status.
        """
        # Отправляем сообщение о начале проверки
        status_msg = await update.message.reply_text("🔍 Проверяю статус сервера...")
        
        try:
            # Проверяем статус контейнера
            container_status = self.docker_manager.get_container_status()
            
            # Проверяем здоровье сервера
            server_health, health_details = self.server_monitor.check_server_health()
            
            # Формируем отчет
            status_text = self._format_status_report(container_status, server_health, health_details)
            
            # Обновляем сообщение
            await status_msg.edit_text(
                status_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            error_text = f"❌ Ошибка при проверке статуса: {str(e)}"
            await status_msg.edit_text(error_text)
            logger.error(f"Ошибка команды /status: {e}")
    
    async def _cmd_restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /restart.
        """
        user_id = str(update.effective_user.id)
        
        # Проверяем лимит рестартов
        if not self._check_restart_limit(user_id):
            await update.message.reply_text(
                f"❌ Превышен лимит рестартов ({self.restart_limit}/час).\n"
                f"Попробуйте позже."
            )
            return
        
        # Отправляем сообщение о начале рестарта
        restart_msg = await update.message.reply_text("🔄 Перезапускаю сервер...")
        
        try:
            # Добавляем рестарт в историю
            self._add_restart_to_history(user_id)
            
            # Выполняем рестарт
            success = self.docker_manager.restart_container()
            
            if success:
                # Проверяем статус после рестарта
                await asyncio.sleep(5)  # Даем время на запуск
                server_health, _ = self.server_monitor.check_server_health()
                
                result_text = (
                    "✅ **Сервер успешно перезапущен!**\n\n"
                    f"🔍 Статус после рестарта: {server_health.value.upper()}\n"
                    f"👤 Инициатор: {update.effective_user.first_name}"
                )
                
                logger.info(f"Успешный рестарт сервера пользователем {user_id}")
            else:
                result_text = (
                    "❌ **Ошибка при перезапуске сервера!**\n\n"
                    "Проверьте логи для получения подробной информации."
                )
                
                logger.error(f"Ошибка рестарта сервера пользователем {user_id}")
            
            await restart_msg.edit_text(
                result_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            error_text = f"❌ Критическая ошибка при рестарте: {str(e)}"
            await restart_msg.edit_text(error_text)
            logger.error(f"Критическая ошибка рестарта: {e}")
    
    async def _cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /stop.
        """
        stop_msg = await update.message.reply_text("⏹️ Останавливаю сервер...")
        
        try:
            success = self.docker_manager.stop_container()
            
            if success:
                result_text = (
                    "⏹️ **Сервер успешно остановлен!**\n\n"
                    f"👤 Инициатор: {update.effective_user.first_name}"
                )
                logger.info(f"Сервер остановлен пользователем {update.effective_user.id}")
            else:
                result_text = "❌ **Ошибка при остановке сервера!**"
                logger.error(f"Ошибка остановки сервера пользователем {update.effective_user.id}")
            
            await stop_msg.edit_text(
                result_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            error_text = f"❌ Ошибка при остановке: {str(e)}"
            await stop_msg.edit_text(error_text)
            logger.error(f"Ошибка команды /stop: {e}")
    
    async def _cmd_start_server(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /start_server.
        """
        start_msg = await update.message.reply_text("▶️ Запускаю сервер...")
        
        try:
            success = self.docker_manager.start_container()
            
            if success:
                # Проверяем статус после запуска
                await asyncio.sleep(5)
                server_health, _ = self.server_monitor.check_server_health()
                
                result_text = (
                    "▶️ **Сервер успешно запущен!**\n\n"
                    f"🔍 Статус: {server_health.value.upper()}\n"
                    f"👤 Инициатор: {update.effective_user.first_name}"
                )
                logger.info(f"Сервер запущен пользователем {update.effective_user.id}")
            else:
                result_text = "❌ **Ошибка при запуске сервера!**"
                logger.error(f"Ошибка запуска сервера пользователем {update.effective_user.id}")
            
            await start_msg.edit_text(
                result_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            error_text = f"❌ Ошибка при запуске: {str(e)}"
            await start_msg.edit_text(error_text)
            logger.error(f"Ошибка команды /start_server: {e}")
    
    async def _cmd_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /logs.
        """
        # Получаем количество строк из аргументов
        lines = 20  # По умолчанию
        if context.args and len(context.args) > 0:
            try:
                lines = min(int(context.args[0]), 100)  # Максимум 100 строк
            except ValueError:
                await update.message.reply_text("❌ Некорректное количество строк")
                return
        
        logs_msg = await update.message.reply_text(f"📋 Получаю последние {lines} строк логов...")
        
        try:
            logs = self.docker_manager.get_container_logs(lines)
            
            # Ограничиваем длину сообщения (Telegram лимит ~4096 символов)
            if len(logs) > 3800:
                logs = "...(обрезано)...\n" + logs[-3800:]
            
            if logs.strip():
                logs_text = f"📋 **Логи контейнера (последние {lines} строк):**\n\n```\n{logs}\n```"
            else:
                logs_text = "📋 Логи пусты или недоступны"
            
            await logs_msg.edit_text(
                logs_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            error_text = f"❌ Ошибка получения логов: {str(e)}"
            await logs_msg.edit_text(error_text)
            logger.error(f"Ошибка команды /logs: {e}")
    
    async def _cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /info.
        """
        info_msg = await update.message.reply_text("📊 Собираю информацию о контейнере...")
        
        try:
            container_info = self.docker_manager.get_container_info()
            
            if 'error' in container_info:
                await info_msg.edit_text(f"❌ {container_info['error']}")
                return
            
            # Форматируем информацию
            info_text = self._format_container_info(container_info)
            
            await info_msg.edit_text(
                info_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            error_text = f"❌ Ошибка получения информации: {str(e)}"
            await info_msg.edit_text(error_text)
            logger.error(f"Ошибка команды /info: {e}")
    
    async def _cmd_players(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /players.
        """
        players_msg = await update.message.reply_text("👥 Получаю список игроков...")
        
        try:
            # Получаем информацию об игроках
            players_info = self.server_monitor.get_server_players()
            
            if not players_info.get('success'):
                await players_msg.edit_text(
                    f"❌ Ошибка получения списка игроков:\n{players_info.get('error', 'Неизвестная ошибка')}"
                )
                return
            
            # Форматируем список игроков
            players_text = self._format_players_list(players_info)
            
            await players_msg.edit_text(
                players_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            error_text = f"❌ Ошибка получения списка игроков: {str(e)}"
            await players_msg.edit_text(error_text)
            logger.error(f"Ошибка команды /players: {e}")
    
    def _format_status_report(self, container_status: ContainerStatus, 
                            server_health: ServerHealth, health_details: Dict[str, Any]) -> str:
        """
        Форматирует отчет о статусе для отображения.
        """
        # Эмодзи для статусов контейнера
        container_emoji = {
            ContainerStatus.RUNNING: "🟢",
            ContainerStatus.STOPPED: "🔴",
            ContainerStatus.STARTING: "🟡",
            ContainerStatus.STOPPING: "🟡",
            ContainerStatus.RESTARTING: "🟡",
            ContainerStatus.NOT_FOUND: "❓",
            ContainerStatus.ERROR: "❌"
        }
        
        emoji = container_emoji.get(container_status, "❓")
        
        # Основная информация
        report = f"{emoji} **Контейнер: {container_status.value.upper()}**\n\n"
        
        # Добавляем отчет о здоровье сервера
        health_report = self.server_monitor.format_health_report(server_health, health_details)
        report += health_report
        
        return report
    
    def _format_container_info(self, info: Dict[str, Any]) -> str:
        """
        Форматирует подробную информацию о контейнере.
        """
        text = f"📊 **Информация о контейнере {info['name']}**\n\n"
        
        text += f"🔍 **Статус:** {info['status']}\n"
        text += f"🖼️ **Образ:** {info['image']}\n"
        text += f"🔄 **Перезапуски:** {info['restart_count']}\n\n"
        
        # Время
        if info.get('started_at'):
            started = info['started_at'][:19].replace('T', ' ')
            text += f"▶️ **Запущен:** {started} UTC\n"
        
        # Ресурсы
        if info.get('cpu_usage') is not None:
            text += f"🖥️ **CPU:** {info['cpu_usage']}%\n"
        
        if info.get('memory_usage'):
            mem = info['memory_usage']
            text += f"💾 **Память:** {mem['usage']} / {mem['limit']} ({mem['percentage']})\n"
        
        # Порты
        if info.get('ports'):
            text += f"\n🔌 **Порты:**\n"
            for container_port, host_bindings in info['ports'].items():
                if host_bindings:
                    for binding in host_bindings:
                        text += f"  • {container_port} → {binding['HostIp']}:{binding['HostPort']}\n"
                else:
                    text += f"  • {container_port} (не привязан)\n"
        
        return text
    
    def _format_players_list(self, players_info: Dict[str, Any]) -> str:
        """
        Форматирует список игроков для отображения.
        """
        count = players_info.get('count', 0)
        max_players = players_info.get('max', 100)
        players = players_info.get('players', [])
        
        text = f"👥 **Игроки онлайн: {count}/{max_players}**\n\n"
        
        if count == 0:
            text += "😴 На сервере никого нет"
        else:
            # Сортируем игроков по ID
            players_sorted = sorted(players, key=lambda p: p.get('id', 0))
            
            # Ограничиваем количество показываемых игроков (чтобы не превысить лимит сообщения)
            max_display = 20
            displayed_players = players_sorted[:max_display]
            
            for i, player in enumerate(displayed_players, 1):
                player_id = player.get('id', '?')
                player_name = player.get('name', 'Unknown')
                ping = player.get('ping', 0)
                
                # Эмодзи для пинга
                if ping < 50:
                    ping_emoji = "🟢"
                elif ping < 100:
                    ping_emoji = "🟡"
                else:
                    ping_emoji = "🔴"
                
                text += f"{i}. **{player_name}** (ID: {player_id}) {ping_emoji} {ping}ms\n"
            
            # Если игроков больше чем показываем
            if count > max_display:
                text += f"\n... и ещё {count - max_display} игроков"
        
        # Добавляем время проверки
        check_time = time.strftime('%H:%M:%S')
        text += f"\n\n🕒 Обновлено в {check_time}"
        
        return text
    
    def _check_restart_limit(self, user_id: str) -> bool:
        """
        Проверяет лимит рестартов для пользователя.
        """
        current_time = time.time()
        hour_ago = current_time - 3600  # 1 час назад
        
        # Получаем историю рестартов пользователя
        user_restarts = self.restart_history.get(user_id, [])
        
        # Удаляем старые записи (старше часа)
        recent_restarts = [t for t in user_restarts if t > hour_ago]
        self.restart_history[user_id] = recent_restarts
        
        # Проверяем лимит
        return len(recent_restarts) < self.restart_limit
    
    def _add_restart_to_history(self, user_id: str):
        """
        Добавляет рестарт в историю пользователя.
        """
        if user_id not in self.restart_history:
            self.restart_history[user_id] = []
        
        self.restart_history[user_id].append(time.time())
    
    async def set_bot_commands(self):
        """
        Устанавливает список команд бота в Telegram.
        """
        commands = [
            BotCommand("start", "Запустить бота"),
            BotCommand("status", "Проверить статус сервера"),
            BotCommand("restart", "Перезапустить сервер"),
            BotCommand("stop", "Остановить сервер"),
            BotCommand("start_server", "Запустить сервер"),
            BotCommand("logs", "Показать логи сервера"),
            BotCommand("info", "Информация о контейнере"),
            BotCommand("players", "Список игроков онлайн"),
            BotCommand("help", "Показать справку")
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("Команды бота установлены")
    
    async def start(self):
        """
        Запускает бота.
        """
        logger.info("Запуск Rage Bot...")
        
        # Устанавливаем команды
        await self.set_bot_commands()
        
        # Запускаем бота
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
        logger.info("Rage Bot успешно запущен и готов к работе!")
    
    async def stop(self):
        """
        Останавливает бота.
        """
        logger.info("Остановка Rage Bot...")
        
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        
        logger.info("Rage Bot остановлен")