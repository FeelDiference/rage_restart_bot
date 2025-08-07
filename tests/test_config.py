"""
Тесты для модуля конфигурации.
"""

import pytest
import tempfile
import os
from unittest.mock import patch
import yaml

from src.utils.config import ConfigManager


class TestConfigManager:
    """
    Тесты для класса ConfigManager.
    """
    
    def test_config_manager_initialization(self):
        """
        Тест инициализации менеджера конфигурации.
        """
        # Создаем временный файл конфигурации
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            test_config = {
                'telegram': {
                    'token': 'test_token',
                    'allowed_groups': ['-123456789'],
                    'admin_users': ['123456789']
                },
                'docker': {
                    'container_name': 'test-rage-server'
                }
            }
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            # Инициализируем менеджер с тестовым файлом
            manager = ConfigManager(config_path)
            
            # Проверяем что конфигурация загружена
            assert manager.config is not None
            assert manager.get_telegram_config()['token'] == 'test_token'
            assert manager.get_container_name() == 'test-rage-server'
            
        finally:
            # Удаляем временный файл
            os.unlink(config_path)
    
    def test_missing_config_file(self):
        """
        Тест обработки отсутствующего файла конфигурации.
        """
        with pytest.raises(FileNotFoundError):
            ConfigManager('/nonexistent/config.yaml')
    
    def test_telegram_token_validation(self):
        """
        Тест валидации токена Telegram.
        """
        # Создаем конфигурацию без токена
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            test_config = {
                'telegram': {
                    'token': 'YOUR_BOT_TOKEN_HERE'  # Невалидный токен
                }
            }
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            
            # Должно вызвать ошибку при попытке получить токен
            with pytest.raises(ValueError):
                manager.get_telegram_token()
                
        finally:
            os.unlink(config_path)
    
    def test_chat_authorization_groups(self):
        """
        Тест авторизации для групп.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            test_config = {
                'telegram': {
                    'allowed_groups': ['-1001234567890', '-1009876543210'],
                    'admin_users': ['123456789']
                }
            }
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            
            # Тест авторизации группы
            assert manager.is_chat_allowed('-1001234567890') == True
            assert manager.is_chat_allowed('-1001111111111') == False
            
            # Тест авторизации личных сообщений от админа
            assert manager.is_chat_allowed('123456789', '123456789') == True
            assert manager.is_chat_allowed('987654321', '987654321') == False
            
        finally:
            os.unlink(config_path)
    
    def test_default_values(self):
        """
        Тест значений по умолчанию.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            test_config = {}  # Пустая конфигурация
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            
            # Проверяем значения по умолчанию
            assert manager.get_allowed_groups() == []
            assert manager.get_admin_users() == []
            assert manager.get_container_name() == 'rage-server'
            
        finally:
            os.unlink(config_path)