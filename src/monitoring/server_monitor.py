"""
Модуль мониторинга Rage сервера.
Отслеживает доступность сервера, состояние портов и здоровье приложения.
"""

import socket
import time
from enum import Enum
from typing import Any, Dict, List, Tuple

import requests
from loguru import logger

from src.utils.config import config_manager


class ServerHealth(Enum):
    """
    Состояния здоровья сервера.
    """

    HEALTHY = "healthy"  # Сервер работает нормально
    DEGRADED = "degraded"  # Сервер работает с проблемами
    UNHEALTHY = "unhealthy"  # Сервер не работает
    STARTING = "starting"  # Сервер запускается
    UNKNOWN = "unknown"  # Состояние неизвестно


class ServerMonitor:
    """
    Монитор для отслеживания состояния Rage сервера.

    Attributes:
        config: Конфигурация мониторинга
        host (str): Хост для проверки портов
        tcp_ports (List[int]): Список TCP портов для проверки
        health_url (str): URL для проверки здоровья
        request_timeout (int): Таймаут для HTTP запросов
    """

    def __init__(self):
        """
        Инициализация монитора сервера.
        """
        self.config = config_manager.get_monitoring_config()
        self.host = self.config.get("host", "localhost")
        self.tcp_ports = self.config.get("tcp_ports", [30120])
        self.health_url = self.config.get("health_check_url")
        self.request_timeout = self.config.get("request_timeout", 10)

        logger.info("Монитор сервера инициализирован")

    def check_server_health(self) -> Tuple[ServerHealth, Dict[str, Any]]:
        """
        Проверяет общее состояние здоровья сервера.

        Returns:
            Tuple[ServerHealth, Dict[str, Any]]: Состояние и детальная информация
        """
        logger.debug("Начало проверки здоровья сервера")

        # Результаты проверок
        port_results = self._check_tcp_ports()
        http_result = self._check_http_health()

        # Подсчет доступных портов
        available_ports = sum(
            1 for result in port_results.values() if result["available"]
        )
        total_ports = len(port_results)

        # Определение общего состояния
        health_status = self._determine_health_status(
            available_ports, total_ports, http_result["healthy"]
        )

        # Формирование детального отчета
        details = {
            "timestamp": time.time(),
            "overall_status": health_status.value,
            "ports": port_results,
            "http_health": http_result,
            "summary": {
                "available_ports": f"{available_ports}/{total_ports}",
                "http_accessible": http_result["healthy"],
            },
        }

        logger.info(f"Проверка завершена. Статус: {health_status.value}")
        return health_status, details

    def _check_tcp_ports(self) -> Dict[int, Dict[str, Any]]:
        """
        Проверяет доступность TCP портов.

        Returns:
            Dict[int, Dict[str, Any]]: Результаты проверки портов
        """
        results = {}

        for port in self.tcp_ports:
            try:
                start_time = time.time()

                # Попытка подключения к порту
                with socket.create_connection((self.host, port), timeout=5) as sock:
                    response_time = round((time.time() - start_time) * 1000, 2)

                    results[port] = {
                        "available": True,
                        "response_time_ms": response_time,
                        "error": None,
                    }

                logger.debug(f"Порт {port} доступен ({response_time}ms)")

            except socket.timeout:
                results[port] = {
                    "available": False,
                    "response_time_ms": None,
                    "error": "Таймаут подключения",
                }
                logger.warning(f"Таймаут подключения к порту {port}")

            except ConnectionRefusedError:
                results[port] = {
                    "available": False,
                    "response_time_ms": None,
                    "error": "Подключение отклонено",
                }
                logger.warning(f"Подключение к порту {port} отклонено")

            except Exception as e:
                results[port] = {
                    "available": False,
                    "response_time_ms": None,
                    "error": str(e),
                }
                logger.error(f"Ошибка проверки порта {port}: {e}")

        return results

    def _check_http_health(self) -> Dict[str, Any]:
        """
        Проверяет HTTP endpoint здоровья с расширенной информацией.

        Returns:
            Dict[str, Any]: Результат HTTP проверки
        """
        if not self.health_url:
            return {
                "healthy": False,
                "error": "URL для проверки здоровья не настроен",
                "response_time_ms": None,
                "status_code": None,
                "server_data": None,
            }

        try:
            start_time = time.time()

            response = requests.get(
                self.health_url,
                timeout=self.request_timeout,
                headers={"User-Agent": "RageBot-Monitor/1.0"},
            )

            response_time = round((time.time() - start_time) * 1000, 2)

            # Считаем здоровым, если статус код 2xx
            is_healthy = 200 <= response.status_code < 300

            # Пытаемся получить данные от сервера
            server_data = None
            if is_healthy:
                try:
                    server_data = response.json()
                except:
                    logger.warning("Не удалось парсить JSON ответ от сервера")

            result = {
                "healthy": is_healthy,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "error": None if is_healthy else f"HTTP {response.status_code}",
                "server_data": server_data,
            }

            logger.debug(f"HTTP проверка: {response.status_code} ({response_time}ms)")
            return result

        except requests.exceptions.Timeout:
            logger.warning("HTTP таймаут при проверке здоровья")
            return {
                "healthy": False,
                "error": "HTTP таймаут",
                "response_time_ms": None,
                "status_code": None,
            }

        except requests.exceptions.ConnectionError:
            logger.warning("Ошибка подключения при HTTP проверке")
            return {
                "healthy": False,
                "error": "Ошибка подключения",
                "response_time_ms": None,
                "status_code": None,
            }

        except Exception as e:
            logger.error(f"Ошибка HTTP проверки: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "response_time_ms": None,
                "status_code": None,
            }

    def _determine_health_status(
        self, available_ports: int, total_ports: int, http_healthy: bool
    ) -> ServerHealth:
        """
        Определяет общее состояние здоровья на основе проверок.

        Args:
            available_ports (int): Количество доступных портов
            total_ports (int): Общее количество портов
            http_healthy (bool): Результат HTTP проверки

        Returns:
            ServerHealth: Общее состояние здоровья
        """
        # Если все порты недоступны - сервер не работает
        if available_ports == 0:
            return ServerHealth.UNHEALTHY

        # Если все порты доступны и HTTP работает - все хорошо
        if available_ports == total_ports and http_healthy:
            return ServerHealth.HEALTHY

        # Если основной порт (30120) доступен, но есть проблемы - деградация
        main_port_available = any(
            port == 30120
            for port in self.tcp_ports
            if self._is_port_available(port)
        )

        if main_port_available:
            return ServerHealth.DEGRADED

        # В остальных случаях - проблемы
        return ServerHealth.UNHEALTHY

    def _is_port_available(self, port: int) -> bool:
        """
        Быстрая проверка доступности порта.

        Args:
            port (int): Порт для проверки

        Returns:
            bool: True если порт доступен
        """
        try:
            with socket.create_connection((self.host, port), timeout=2):
                return True
        except:
            return False

    def get_server_players(self) -> Dict[str, Any]:
        """
        Получает информацию об игроках с сервера.

        Returns:
            Dict[str, Any]: Информация об игроках
        """
        api_endpoints = self.config.get("api_endpoints", {})
        players_url = api_endpoints.get("players")

        if not players_url:
            return {
                "success": False,
                "error": "API endpoint для игроков не настроен",
                "players": [],
            }

        try:
            response = requests.get(
                players_url,
                timeout=self.request_timeout,
                headers={"User-Agent": "RageBot-Monitor/1.0"},
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "players": [],
                }

        except Exception as e:
            logger.error(f"Ошибка получения списка игроков: {e}")
            return {"success": False, "error": str(e), "players": []}

    def get_server_info(self) -> Dict[str, Any]:
        """
        Получает подробную информацию о сервере.

        Returns:
            Dict[str, Any]: Информация о сервере
        """
        api_endpoints = self.config.get("api_endpoints", {})
        info_url = api_endpoints.get("info")

        if not info_url:
            return {
                "success": False,
                "error": "API endpoint для информации не настроен",
            }

        try:
            response = requests.get(
                info_url,
                timeout=self.request_timeout,
                headers={"User-Agent": "RageBot-Monitor/1.0"},
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"Ошибка получения информации о сервере: {e}")
            return {"success": False, "error": str(e)}

    def get_server_uptime(self) -> Dict[str, Any]:
        """
        Получает информацию о времени работы сервера из API.

        Returns:
            Dict[str, Any]: Информация о времени работы
        """
        # Пытаемся получить от HTTP API
        health_result = self._check_http_health()

        if health_result.get("healthy") and health_result.get("server_data"):
            server_data = health_result["server_data"]
            server_info = server_data.get("server", {})

            return {
                "uptime_seconds": server_info.get("uptime", 0) // 1000,
                "uptime_formatted": server_info.get("uptime_formatted", "Неизвестно"),
                "error": None,
            }
        else:
            return {
                "uptime_seconds": None,
                "uptime_formatted": "Недоступно",
                "error": "Сервер недоступен или API не отвечает",
            }

    def format_health_report(
        self, health: ServerHealth, details: Dict[str, Any]
    ) -> str:
        """
        Форматирует отчет о здоровье для отображения в Telegram.

        Args:
            health (ServerHealth): Состояние здоровья
            details (Dict[str, Any]): Детальная информация

        Returns:
            str: Отформатированный отчет
        """
        # Эмодзи для статусов
        status_emoji = {
            ServerHealth.HEALTHY: "✅",
            ServerHealth.DEGRADED: "⚠️",
            ServerHealth.UNHEALTHY: "❌",
            ServerHealth.STARTING: "🔄",
            ServerHealth.UNKNOWN: "❓",
        }

        emoji = status_emoji.get(health, "❓")

        # Формируем отчет
        report = f"{emoji} **Статус сервера: {health.value.upper()}**\n\n"

        # Информация от Rage сервера (если доступна)
        http_info = details["http_health"]
        server_data = http_info.get("server_data")

        if server_data and server_data.get("success"):
            server_info = server_data.get("server", {})
            players_info = server_data.get("players", {})

            # Информация о сервере
            report += f"🎮 **Сервер:** {server_info.get('name', 'Неизвестно')}\n"
            report += (
                f"⏱️ **Uptime:** {server_info.get('uptime_formatted', 'Неизвестно')}\n"
            )

            # Информация об игроках
            online = players_info.get("online", 0)
            max_players = players_info.get("max", 100)
            report += f"👥 **Игроки:** {online}/{max_players}\n\n"

        # Информация о портах
        report += "🔌 **Порты:**\n"
        for port, info in details["ports"].items():
            port_emoji = "✅" if info["available"] else "❌"
            response_time = (
                f" ({info['response_time_ms']}ms)" if info["response_time_ms"] else ""
            )
            error_info = f" - {info['error']}" if info["error"] else ""
            report += f"  {port_emoji} {port}{response_time}{error_info}\n"

        # HTTP API проверка
        http_emoji = "✅" if http_info["healthy"] else "❌"
        http_time = (
            f" ({http_info['response_time_ms']}ms)"
            if http_info["response_time_ms"]
            else ""
        )
        http_error = f" - {http_info['error']}" if http_info["error"] else ""
        report += f"\n🌐 **API:** {http_emoji}{http_time}{http_error}\n"

        # Сводка
        summary = details["summary"]
        report += "\n📊 **Сводка:**\n"
        report += f"  • Доступные порты: {summary['available_ports']}\n"
        report += f"  • API доступен: {'Да' if summary['http_accessible'] else 'Нет'}\n"

        # Время проверки
        check_time = time.strftime("%H:%M:%S", time.localtime(details["timestamp"]))
        report += f"\n🕒 Проверено в {check_time}"

        return report
