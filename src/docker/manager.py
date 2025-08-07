"""
Модуль для управления Docker контейнером с Rage сервером.
Обеспечивает операции запуска, остановки, рестарта и мониторинга.
"""

import docker
import time
from typing import Dict, Any, Optional, List
from enum import Enum
from loguru import logger
from docker.errors import DockerException, NotFound, APIError


class ContainerStatus(Enum):
    """
    Статусы контейнера.
    """
    RUNNING = "running"           # Контейнер работает
    STOPPED = "stopped"           # Контейнер остановлен
    STARTING = "starting"         # Контейнер запускается
    STOPPING = "stopping"        # Контейнер останавливается
    RESTARTING = "restarting"     # Контейнер перезапускается
    NOT_FOUND = "not_found"       # Контейнер не найден
    ERROR = "error"               # Ошибка


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
                'running': ContainerStatus.RUNNING,
                'exited': ContainerStatus.STOPPED,
                'created': ContainerStatus.STOPPED,
                'restarting': ContainerStatus.RESTARTING,
                'removing': ContainerStatus.STOPPING,
                'paused': ContainerStatus.STOPPED,
                'dead': ContainerStatus.ERROR
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
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else 'unknown',
                'created': container.attrs['Created'],
                'started_at': container.attrs['State'].get('StartedAt'),
                'finished_at': container.attrs['State'].get('FinishedAt'),
                'restart_count': container.attrs['RestartCount'],
                'ports': container.ports,
                'cpu_usage': self._calculate_cpu_usage(stats),
                'memory_usage': self._calculate_memory_usage(stats)
            }
            
            return info
            
        except NotFound:
            return {'error': 'Контейнер не найден'}
        except DockerException as e:
            logger.error(f"Ошибка получения информации о контейнере: {e}")
            return {'error': str(e)}
    
    def start_container(self) -> bool:
        """
        Запускает контейнер.
        
        Returns:
            bool: True если контейнер успешно запущен
        """
        try:
            container = self.client.containers.get(self.container_name)
            
            if container.status == 'running':
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
            
            if container.status != 'running':
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
            return self._wait_for_status(ContainerStatus.RUNNING, self.restart_timeout * 2)
            
        except NotFound:
            logger.error(f"Контейнер {self.container_name} не найден")
            return False
        except DockerException as e:
            logger.error(f"Ошибка перезапуска контейнера: {e}")
            return False
    
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
            logs = container.logs(tail=lines, timestamps=True).decode('utf-8')
            return logs
            
        except NotFound:
            return "Контейнер не найден"
        except DockerException as e:
            logger.error(f"Ошибка получения логов: {e}")
            return f"Ошибка получения логов: {e}"
    
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
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            
            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * \
                             len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100
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
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            
            # Конвертируем в мегабайты
            usage_mb = round(memory_usage / 1024 / 1024, 2)
            limit_mb = round(memory_limit / 1024 / 1024, 2)
            percentage = round((memory_usage / memory_limit) * 100, 2)
            
            return {
                'usage': f"{usage_mb} MB",
                'limit': f"{limit_mb} MB",
                'percentage': f"{percentage}%"
            }
        except KeyError:
            return {
                'usage': "N/A",
                'limit': "N/A", 
                'percentage': "N/A"
            }