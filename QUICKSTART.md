# Быстрый старт Rage Restart Bot

## 🚀 За 5 минут до работы

### 1. Создание бота в Telegram

```
1. Найдите @BotFather в Telegram
2. Отправьте /newbot
3. Введите имя бота: "Rage Server Bot"
4. Введите username: "your_rage_server_bot"
5. Сохраните токен: 1234567890:AAEhBP0dvZbTHasdlol1xZTNDK...
```

### 2. Получение ID группы

```
1. Создайте группу в Telegram
2. Добавьте в неё своего бота
3. Добавьте @userinfobot
4. Выполните команду /id
5. Скопируйте ID группы: -1001234567890
```

### 3. Установка на сервере

```bash
# 1. Клонируем репозиторий
git clone https://github.com/YOUR_USERNAME/rage-restart-bot.git
cd rage-restart-bot

# 2. Автоматическая установка
sudo ./scripts/setup.sh

# 3. Настройка конфигурации
cp config/config.yaml.example config/config.yaml
nano config/config.yaml
```

### 4. Минимальная конфигурация

Отредактируйте только эти строки в `config/config.yaml`:

```yaml
telegram:
  token: "1234567890:AAEhBP0dvZbTHasdlol1xZTNDK..."  # Ваш токен
  allowed_groups: 
    - "-1001234567890"  # ID вашей группы
  admin_users:
    - "123456789"  # Ваш Telegram ID

docker:
  container_name: "rage-server"  # Имя вашего Rage контейнера
```

### 5. Запуск

```bash
# Запуск
sudo systemctl start rage-bot

# Проверка
sudo systemctl status rage-bot

# Логи
docker-compose logs -f rage-bot
```

## ✅ Проверка работы

1. Зайдите в группу Telegram
2. Выполните команду `/start`
3. Выполните команду `/status`
4. Если все работает - бот ответит статусом сервера

## 🔧 Основные команды

- `/status` - Статус сервера
- `/restart` - Перезапуск сервера  
- `/stop` - Остановка сервера
- `/start_server` - Запуск сервера
- `/logs` - Последние логи
- `/help` - Справка

## 🆘 Если что-то не работает

```bash
# Проверка логов
docker-compose logs rage-bot

# Проверка конфигурации
python3 -c "from src.utils.config import config_manager; print('OK')"

# Перезапуск
sudo systemctl restart rage-bot
```

## 📱 Получение вашего Telegram ID

1. Найдите @userinfobot
2. Отправьте ему любое сообщение
3. Скопируйте ваш ID из ответа

---

**Полная документация**: [INSTALL.md](INSTALL.md)