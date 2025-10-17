"""
Модуль для управления Docker контейнером с Rage сервером.
Обеспечивает операции запуска, остановки, рестарта и мониторинга.
"""

import time
from enum import Enum
from typing import Any, Dict, List

import docker
from docker.errors import APIError, DockerException, NotFound
from loguru import logger


class ContainerStatus(Enum):
    """
    Статусы контейнера.
    """

    RUNNING = "running"  # Контейнер работает
    STOPPED = "stopped"  # Контейнер остановлен
    STARTING = "starting"  # Контейнер запускается
    STOPPING = "stopping"  # Контейнер останавливается
    RESTARTING = "restarting"  # Контейнер перезапускается
    NOT_FOUND = "not_found"  # Контейнер не найден
    ERROR = "error"  # Ошибка


class DockerManager:
    """
    Менеджер для управления Docker контейнером с Rage сервером.

    Attributes:
        client: Docker клиент
        container_name (str): Имя управляемого контейнера
        restart_timeout (int): Таймаут для операций рестарта
    """

    def __init__(self, container_name: str, restart_timeout: int = 30):
        """
        Инициализация Docker менеджера.

        Args:
            container_name (str): Имя контейнера для управления
            restart_timeout (int): Таймаут в секундах для операций
        """
        self.container_name = container_name
        self.restart_timeout = restart_timeout

        try:
            # Инициализация Docker клиента
            self.client = docker.from_env()
            logger.info("Docker клиент успешно инициализирован")
        except DockerException as e:
            logger.error(f"Ошибка подключения к Docker: {e}")
            raise

    def get_container_status(self) -> ContainerStatus:
        """
        Получает текущий статус контейнера.

        Returns:
            ContainerStatus: Текущий статус контейнера
        """
        try:
            container = self.client.containers.get(self.container_name)
            status = container.status.lower()

            # Маппинг статусов Docker в наши статусы
            status_mapping = {
                "running": ContainerStatus.RUNNING,
                "exited": ContainerStatus.STOPPED,
                "created": ContainerStatus.STOPPED,
                "restarting": ContainerStatus.RESTARTING,
                "removing": ContainerStatus.STOPPING,
                "paused": ContainerStatus.STOPPED,
                "dead": ContainerStatus.ERROR,
            }

            return status_mapping.get(status, ContainerStatus.ERROR)

        except NotFound:
            logger.warning(f"Контейнер {self.container_name} не найден")
            return ContainerStatus.NOT_FOUND
        except DockerException as e:
            logger.error(f"Ошибка получения статуса контейнера: {e}")
            return ContainerStatus.ERROR

    def get_container_info(self) -> Dict[str, Any]:
        """
        Получает подробную информацию о контейнере.

        Returns:
            Dict[str, Any]: Информация о контейнере
        """
        try:
            container = self.client.containers.get(self.container_name)

            # Получаем статистику контейнера
            stats = container.stats(stream=False)

            info = {
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs["Created"],
                "started_at": container.attrs["State"].get("StartedAt"),
                "finished_at": container.attrs["State"].get("FinishedAt"),
                "restart_count": container.attrs["RestartCount"],
                "ports": container.ports,
                "cpu_usage": self._calculate_cpu_usage(stats),
                "memory_usage": self._calculate_memory_usage(stats),
            }

            return info

        except NotFound:
            return {"error": "Контейнер не найден"}
        except DockerException as e:
            logger.error(f"Ошибка получения информации о контейнере: {e}")
            return {"error": str(e)}

    def start_container(self) -> bool:
        """
        Запускает контейнер.

        Returns:
            bool: True если контейнер успешно запущен
        """
        try:
            container = self.client.containers.get(self.container_name)

            if container.status == "running":
                logger.info(f"Контейнер {self.container_name} уже запущен")
                return True

            logger.info(f"Запуск контейнера {self.container_name}")
            container.start()

            # Ждем запуска
            return self._wait_for_status(ContainerStatus.RUNNING, self.restart_timeout)

        except NotFound:
            logger.error(f"Контейнер {self.container_name} не найден")
            return False
        except DockerException as e:
            logger.error(f"Ошибка запуска контейнера: {e}")
            return False

    def stop_container(self) -> bool:
        """
        Останавливает контейнер.

        Returns:
            bool: True если контейнер успешно остановлен
        """
        try:
            container = self.client.containers.get(self.container_name)

            if container.status != "running":
                logger.info(f"Контейнер {self.container_name} уже остановлен")
                return True

            logger.info(f"Остановка контейнера {self.container_name}")
            container.stop(timeout=self.restart_timeout)

            # Ждем остановки
            return self._wait_for_status(ContainerStatus.STOPPED, self.restart_timeout)

        except NotFound:
            logger.error(f"Контейнер {self.container_name} не найден")
            return False
        except DockerException as e:
            logger.error(f"Ошибка остановки контейнера: {e}")
            return False

    def restart_container(self) -> bool:
        """
        Перезапускает контейнер.

        Returns:
            bool: True если контейнер успешно перезапущен
        """
        try:
            container = self.client.containers.get(self.container_name)

            logger.info(f"Перезапуск контейнера {self.container_name}")
            container.restart(timeout=self.restart_timeout)

            # Ждем успешного перезапуска
            return self._wait_for_status(
                ContainerStatus.RUNNING, self.restart_timeout * 2
            )

        except NotFound:
            logger.error(f"Контейнер {self.container_name} не найден")
            return False
        except DockerException as e:
            logger.error(f"Ошибка перезапуска контейнера: {e}")
            return False

    def restart_any_container(self, container_name: str) -> Dict[str, Any]:
        """
        Перезапускает любой контейнер по имени.

        Args:
            container_name (str): Имя контейнера для перезапуска

        Returns:
            Dict[str, Any]: Результат операции с информацией о статусе
        """
        result = {
            "success": False,
            "message": "",
            "container_name": container_name,
            "status_before": None,
            "status_after": None
        }
        
        try:
            container = self.client.containers.get(container_name)
            
            # Сохраняем статус до перезапуска
            result["status_before"] = container.status
            
            logger.info(f"Перезапуск контейнера {container_name}")
            container.restart(timeout=self.restart_timeout)

            # Ждем успешного перезапуска
            start_time = time.time()
            timeout = self.restart_timeout * 2
            
            while time.time() - start_time < timeout:
                try:
                    container.reload()
                    if container.status == "running":
                        result["status_after"] = container.status
                        result["success"] = True
                        result["message"] = f"Контейнер {container_name} успешно перезапущен"
                        logger.info(f"Контейнер {container_name} успешно перезапущен")
                        return result
                except Exception:
                    pass
                
                time.sleep(2)  # Проверяем каждые 2 секунды
            
            # Если не удалось дождаться запуска
            try:
                container.reload()
                result["status_after"] = container.status
            except Exception:
                result["status_after"] = "unknown"
                
            result["message"] = f"Контейнер {container_name} перезапущен, но не удалось подтвердить статус 'running' в течение {timeout}с"
            logger.warning(result["message"])

        except NotFound:
            result["message"] = f"Контейнер '{container_name}' не найден"
            logger.error(result["message"])
        except DockerException as e:
            result["message"] = f"Ошибка при перезапуске контейнера '{container_name}': {str(e)}"
            logger.error(result["message"])
        except Exception as e:
            result["message"] = f"Неожиданная ошибка при перезапуске контейнера '{container_name}': {str(e)}"
            logger.error(result["message"])

        return result

    def get_container_logs(self, lines: int = 50) -> str:
        """
        Получает логи контейнера.

        Args:
            lines (int): Количество последних строк логов

        Returns:
            str: Логи контейнера
        """
        try:
            container = self.client.containers.get(self.container_name)
            logs = container.logs(tail=lines, timestamps=True).decode("utf-8")
            return logs

        except NotFound:
            return "Контейнер не найден"
        except DockerException as e:
            logger.error(f"Ошибка получения логов: {e}")
            return f"Ошибка получения логов: {e}"

    def list_all_containers(self) -> List[Dict[str, str]]:
        """
        Получает список всех контейнеров для диагностики.

        Returns:
            List[Dict[str, str]]: Список контейнеров с их именами и статусами
        """
        try:
            containers = self.client.containers.list(all=True)
            result = []
            
            for container in containers:
                result.append({
                    "name": container.name,
                    "status": container.status,
                    "image": container.image.tags[0] if container.image.tags else "unknown",
                    "id": container.short_id
                })
            
            logger.info(f"Найдено {len(result)} контейнеров")
            return result
            
        except DockerException as e:
            logger.error(f"Ошибка получения списка контейнеров: {e}")
            return []

    def diagnose_container_detection(self) -> Dict[str, Any]:
        """
        Диагностическая функция для отладки поиска контейнера.

        Returns:
            Dict[str, Any]: Диагностическая информация
        """
        diagnosis = {
            "target_container_name": self.container_name,
            "docker_connected": False,
            "all_containers": [],
            "target_found": False,
            "target_status": None,
            "similar_names": []
        }

        try:
            # Проверяем подключение к Docker
            self.client.ping()
            diagnosis["docker_connected"] = True
            logger.info("✅ Docker подключение активно")

            # Получаем все контейнеры
            all_containers = self.list_all_containers()
            diagnosis["all_containers"] = all_containers

            # Ищем точное совпадение
            for container in all_containers:
                if container["name"] == self.container_name:
                    diagnosis["target_found"] = True
                    diagnosis["target_status"] = container["status"]
                    logger.info(f"✅ Целевой контейнер найден: {container['name']} ({container['status']})")
                    break

            # Ищем похожие имена
            for container in all_containers:
                if self.container_name.lower() in container["name"].lower() or container["name"].lower() in self.container_name.lower():
                    diagnosis["similar_names"].append(container)

            if not diagnosis["target_found"]:
                logger.warning(f"❌ Контейнер '{self.container_name}' не найден!")
                if diagnosis["similar_names"]:
                    logger.info(f"🔍 Найдены похожие контейнеры: {[c['name'] for c in diagnosis['similar_names']]}")

        except DockerException as e:
            logger.error(f"❌ Ошибка подключения к Docker: {e}")
            diagnosis["error"] = str(e)

        return diagnosis

    def _wait_for_status(self, target_status: ContainerStatus, timeout: int) -> bool:
        """
        Ожидает достижения контейнером определенного статуса.

        Args:
            target_status (ContainerStatus): Ожидаемый статус
            timeout (int): Таймаут ожидания в секундах

        Returns:
            bool: True если статус достигнут в пределах таймаута
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            current_status = self.get_container_status()

            if current_status == target_status:
                logger.info(f"Контейнер достиг статуса {target_status.value}")
                return True

            if current_status == ContainerStatus.ERROR:
                logger.error("Контейнер в состоянии ошибки")
                return False

            time.sleep(2)  # Проверяем каждые 2 секунды

        logger.warning(f"Таймаут ожидания статуса {target_status.value}")
        return False

    def _calculate_cpu_usage(self, stats: Dict[str, Any]) -> float:
        """
        Вычисляет использование CPU в процентах.

        Args:
            stats (Dict[str, Any]): Статистика контейнера

        Returns:
            float: Процент использования CPU
        """
        try:
            cpu_delta = (
                stats["cpu_stats"]["cpu_usage"]["total_usage"]
                - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            )
            system_delta = (
                stats["cpu_stats"]["system_cpu_usage"]
                - stats["precpu_stats"]["system_cpu_usage"]
            )

            if system_delta > 0:
                cpu_percent = (
                    (cpu_delta / system_delta)
                    * len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
                    * 100
                )
                return round(cpu_percent, 2)
        except (KeyError, ZeroDivisionError):
            pass

        return 0.0

    def _calculate_memory_usage(self, stats: Dict[str, Any]) -> Dict[str, str]:
        """
        Вычисляет использование памяти.

        Args:
            stats (Dict[str, Any]): Статистика контейнера

        Returns:
            Dict[str, str]: Информация об использовании памяти
        """
        try:
            memory_usage = stats["memory_stats"]["usage"]
            memory_limit = stats["memory_stats"]["limit"]

            # Конвертируем в мегабайты
            usage_mb = round(memory_usage / 1024 / 1024, 2)
            limit_mb = round(memory_limit / 1024 / 1024, 2)
            percentage = round((memory_usage / memory_limit) * 100, 2)

            return {
                "usage": f"{usage_mb} MB",
                "limit": f"{limit_mb} MB",
                "percentage": f"{percentage}%",
            }
        except KeyError:
            return {"usage": "N/A", "limit": "N/A", "percentage": "N/A"}
