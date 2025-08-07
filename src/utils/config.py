"""
Модуль для загрузки и управления конфигурацией бота.
Обеспечивает централизованное управление настройками приложения.
"""

import os
import yaml
from typing import Dict, Any, List
from loguru import logger


class ConfigManager:
    """
    Менеджер конфигурации для загрузки и управления настройками бота.
    
    Attributes:
        config (Dict[str, Any]): Загруженная конфигурация
        config_path (str): Путь к файлу конфигурации
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Инициализация менеджера конфигурации.
        
        Args:
            config_path (str): Путь к файлу конфигурации
        """
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Загружает конфигурацию из YAML файла.
        
        Returns:
            Dict[str, Any]: Загруженная конфигурация
            
        Raises:
            FileNotFoundError: Если файл конфигурации не найден
            yaml.YAMLError: Если файл содержит некорректный YAML
        """
        try:
            if not os.path.exists(self.config_path):
                logger.error(f"Файл конфигурации не найден: {self.config_path}")
                raise FileNotFoundError(f"Конфигурационный файл не найден: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                
            logger.info("Конфигурация успешно загружена")
            return config
            
        except yaml.YAMLError as e:
            logger.error(f"Ошибка парсинга YAML: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            raise
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """
        Получает конфигурацию Telegram бота.
        
        Returns:
            Dict[str, Any]: Конфигурация Telegram
        """
        return self.config.get('telegram', {})
    
    def get_docker_config(self) -> Dict[str, Any]:
        """
        Получает конфигурацию Docker.
        
        Returns:
            Dict[str, Any]: Конфигурация Docker
        """
        return self.config.get('docker', {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """
        Получает конфигурацию мониторинга.
        
        Returns:
            Dict[str, Any]: Конфигурация мониторинга
        """
        return self.config.get('monitoring', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Получает конфигурацию логирования.
        
        Returns:
            Dict[str, Any]: Конфигурация логирования
        """
        return self.config.get('logging', {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """
        Получает конфигурацию безопасности.
        
        Returns:
            Dict[str, Any]: Конфигурация безопасности
        """
        return self.config.get('security', {})
    
    def get_telegram_token(self) -> str:
        """
        Получает токен Telegram бота.
        
        Returns:
            str: Токен бота
            
        Raises:
            ValueError: Если токен не настроен
        """
        token = self.get_telegram_config().get('token')
        if not token or token == "YOUR_BOT_TOKEN_HERE":
            raise ValueError("Токен Telegram бота не настроен в конфигурации")
        return token
    
    def get_allowed_groups(self) -> List[str]:
        """
        Получает список разрешенных групп.
        
        Returns:
            List[str]: Список ID групп
        """
        return self.get_telegram_config().get('allowed_groups', [])
    
    def get_admin_users(self) -> List[str]:
        """
        Получает список администраторов (для личных сообщений).
        
        Returns:
            List[str]: Список ID администраторов
        """
        return self.get_telegram_config().get('admin_users', [])
    
    def get_container_name(self) -> str:
        """
        Получает имя Docker контейнера.
        
        Returns:
            str: Имя контейнера
        """
        return self.get_docker_config().get('container_name', 'rage-server')
    
    def is_chat_allowed(self, chat_id: str, user_id: str = None) -> bool:
        """
        Проверяет, разрешен ли чат или пользователь.
        
        Args:
            chat_id (str): ID чата (группы или личного чата)
            user_id (str, optional): ID пользователя для проверки админских прав
            
        Returns:
            bool: True если чат разрешен
        """
        chat_id_str = str(chat_id)
        
        # Проверяем группы (ID начинается с -)
        if chat_id_str.startswith('-'):
            allowed_groups = self.get_allowed_groups()
            return chat_id_str in allowed_groups
        
        # Проверяем личные сообщения от админов
        if user_id:
            admin_users = self.get_admin_users()
            return str(user_id) in admin_users
            
        return False
    
    def reload_config(self) -> None:
        """
        Перезагружает конфигурацию из файла.
        """
        logger.info("Перезагрузка конфигурации")
        self.config = self._load_config()


# Глобальный экземпляр конфигурации
config_manager = ConfigManager() 