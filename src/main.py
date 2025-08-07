"""
Точка входа для Rage Restart Bot.
Инициализирует логирование и запускает Telegram бота.
"""

import asyncio
import os
import sys
from pathlib import Path
from loguru import logger

# Добавляем корневую директорию в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import config_manager
from src.bot.rage_bot import RageBot


def setup_logging():
    """
    Настраивает систему логирования.
    """
    # Получаем конфигурацию логирования
    logging_config = config_manager.get_logging_config()
    
    # Удаляем стандартный handler
    logger.remove()
    
    # Добавляем консольный вывод
    logger.add(
        sys.stdout,
        level=logging_config.get('level', 'INFO'),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True
    )
    
    # Добавляем файловый вывод
    log_file = logging_config.get('file', 'logs/bot.log')
    log_dir = os.path.dirname(log_file)
    
    # Создаем директорию для логов если её нет
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    logger.add(
        log_file,
        level=logging_config.get('level', 'INFO'),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation=logging_config.get('max_size', '10 MB'),
        retention=logging_config.get('rotation', 5),
        compression="zip"
    )
    
    logger.info("Система логирования настроена")


async def main():
    """
    Основная функция приложения.
    """
    try:
        # Настраиваем логирование
        setup_logging()
        
        logger.info("=" * 50)
        logger.info("🚀 Запуск Rage Restart Bot")
        logger.info("=" * 50)
        
        # Проверяем конфигурацию
        try:
            token = config_manager.get_telegram_token()
            container_name = config_manager.get_container_name()
            allowed_groups = config_manager.get_allowed_groups()
            
            logger.info(f"Контейнер для управления: {container_name}")
            logger.info(f"Количество разрешенных групп: {len(allowed_groups)}")
            
        except ValueError as e:
            logger.error(f"Ошибка конфигурации: {e}")
            logger.error("Проверьте файл config/config.yaml")
            return
        
        # Создаем и запускаем бота
        bot = RageBot()
        
        try:
            await bot.start()
            
            # Бот работает до получения сигнала остановки
            logger.info("Бот работает. Нажмите Ctrl+C для остановки.")
            
            # Ожидаем бесконечно
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки (Ctrl+C)")
        except Exception as e:
            logger.error(f"Неожиданная ошибка в работе бота: {e}")
            raise
        finally:
            await bot.stop()
    
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """
    Точка входа приложения.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение завершено пользователем")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")
        sys.exit(1)