"""
Менеджер для взаимодействия с Docker контейнером Rage сервера.
"""

import asyncio
from enum import Enum
from typing import Optional

import docker
from docker.errors import APIError, DockerException, NotFound
from loguru import logger


class ContainerStatus(Enum):
    """
    Статус Docker контейнера.
    """
    RUNNING = "running"
    STOPPED = "stopped"
    NOT_FOUND = "not_found"
    ERROR = "error"


class DockerManager:
    """
    Управляет Docker контейнером: старт, стоп, рестарт, проверка статуса.
    """

    def __init__(self, container_name: str, restart_timeout: int = 30):
        """
        Инициализация DockerManager.

        Args:
            container_name (str): Имя Docker контейнера.
            restart_timeout (int): Таймаут для рестарта в секундах.
        """
        self.container_name = container_name
        self.restart_timeout = restart_timeout
        try:
            self.client = docker.from_env()
            logger.info("Успешное подключение к Docker API.")
        except DockerException as e:
            logger.error(f"Не удалось подключиться к Docker API: {e}")
            logger.error(
                "Убедитесь, что Docker запущен и сокет доступен по пути /var/run/docker.sock"
            )
            self.client = None

    async def _get_container(self):
        """
        Получает объект контейнера по имени.

        Returns:
            Container: Объект контейнера или None, если не найден.
        """
        if not self.client:
            logger.warning("Клиент Docker не инициализирован.")
            return None
        
        logger.info(f"Попытка найти контейнер по имени: '{self.container_name}'")
        try:
            return self.client.containers.get(self.container_name)
        except NotFound:
            logger.warning(f"Контейнер с именем '{self.container_name}' не найден.")
            
            # Альтернативный метод: ищем среди всех контейнеров
            logger.info("Поиск среди всех доступных контейнеров...")
            try:
                containers = self.client.containers.list(all=True)
                if not containers:
                    logger.warning("Не найдено ни одного контейнера в системе.")
                    return None
                
                logger.info(f"Найдено {len(containers)} контейнеров. Проверка имен:")
                for container in containers:
                    logger.info(f" - Найден контейнер: ID={container.short_id}, Имя='{container.name}'")
                    if container.name == self.container_name:
                        logger.info(f"✅ Контейнер '{self.container_name}' найден по имени среди всех контейнеров.")
                        return container
                
                logger.warning(f"Контейнер '{self.container_name}' так и не был найден по имени.")
                return None

            except APIError as e:
                logger.error(f"Ошибка Docker API при получении списка всех контейнеров: {e}")
                return None
        except APIError as e:
            logger.error(f"Ошибка Docker API при поиске контейнера: {e}")
            return None

    async def get_status(self) -> ContainerStatus:
        """
        Получает статус контейнера.

        Returns:
            ContainerStatus: Текущий статус контейнера.
        """
        logger.info(f"Запрос статуса для контейнера '{self.container_name}'")
        try:
            container = await self._get_container()
            if container:
                logger.info(f"Статус контейнера '{self.container_name}': {container.status}")
                if container.status == "running":
                    return ContainerStatus.RUNNING
                else:
                    return ContainerStatus.STOPPED
            return ContainerStatus.NOT_FOUND
        except Exception as e:
            logger.error(f"Ошибка при получении статуса контейнера: {e}")
            return ContainerStatus.ERROR

    async def start(self) -> bool:
        """
        Запускает контейнер.

        Returns:
            bool: True, если контейнер успешно запущен, иначе False.
        """
        logger.info(f"Попытка запуска контейнера '{self.container_name}'")
        try:
            container = await self._get_container()
            if not container:
                logger.error("Не удалось запустить: контейнер не найден.")
                return False
            if container.status == "running":
                logger.warning("Контейнер уже запущен.")
                return True
            container.start()
            logger.info("Контейнер успешно запущен.")
            return True
        except APIError as e:
            logger.error(f"Ошибка Docker API при запуске контейнера: {e}")
            return False
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при запуске контейнера: {e}")
            return False

    async def stop(self) -> bool:
        """
        Останавливает контейнер.

        Returns:
            bool: True, если контейнер успешно остановлен, иначе False.
        """
        logger.info(f"Попытка остановки контейнера '{self.container_name}'")
        try:
            container = await self._get_container()
            if not container:
                logger.error("Не удалось остановить: контейнер не найден.")
                return False
            if container.status != "running":
                logger.warning("Контейнер уже остановлен.")
                return True
            container.stop()
            logger.info("Контейнер успешно остановлен.")
            return True
        except APIError as e:
            logger.error(f"Ошибка Docker API при остановке контейнера: {e}")
            return False
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при остановке контейнера: {e}")
            return False

    async def restart(self) -> bool:
        """
        Перезапускает контейнер.

        Returns:
            bool: True, если контейнер успешно перезапущен, иначе False.
        """
        logger.info(f"Попытка перезапуска контейнера '{self.container_name}'")
        try:
            container = await self._get_container()
            if not container:
                logger.error("Не удалось перезапустить: контейнер не найден.")
                return False
            container.restart(timeout=self.restart_timeout)
            logger.info("Контейнер успешно перезапущен.")
            return True
        except APIError as e:
            logger.error(f"Ошибка Docker API при перезапуске контейнера: {e}")
            return False
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при перезапуске контейнера: {e}")
            return False
