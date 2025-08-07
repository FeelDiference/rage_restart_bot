# Установка и настройка Rage Restart Bot

Этот документ содержит пошаговые инструкции по установке и настройке Telegram бота для управления Rage сервером.

## Требования

- Ubuntu/Debian сервер
- Docker и Docker Compose
- Git
- Минимум 512MB RAM и 1GB свободного места

## Быстрая установка

### 1. Подготовка сервера

```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Git
sudo apt install -y git

# Клонируем репозиторий
git clone https://github.com/YOUR_USERNAME/rage-restart-bot.git
cd rage-restart-bot
```

### 2. Автоматическая установка

```bash
# Запускаем скрипт установки (НЕ под root!)
sudo ./scripts/setup.sh
```

Скрипт автоматически:
- Установит Docker и Docker Compose
- Создаст структуру директорий
- Настроит systemd сервис
- Настроит ротацию логов

### 3. Настройка конфигурации

#### Получение токена бота

1. Найдите @BotFather в Telegram
2. Выполните команду `/newbot`
3. Следуйте инструкциям и получите токен
4. Сохраните токен - он понадобится для конфигурации

#### Получение ID группы

1. Добавьте бота в вашу группу
2. Дайте боту права администратора
3. Найдите @userinfobot в Telegram
4. Добавьте его в группу и выполните `/id`
5. Скопируйте ID группы (начинается с `-100`)

#### Настройка config.yaml

```bash
# Копируем пример конфигурации
cp config/config.yaml.example config/config.yaml

# Редактируем конфигурацию
nano config/config.yaml
```

Обязательные параметры для изменения:

```yaml
telegram:
  token: "ВАША_ТОКЕН_ОТ_BOTFATHER"
  allowed_groups: 
    - "-1001234567890"  # ID вашей группы
  admin_users:
    - "123456789"  # Ваш Telegram ID

docker:
  container_name: "rage-server"  # Имя вашего Rage контейнера

monitoring:
  host: "IP_ВАШЕГО_СЕРВЕРА"  # IP сервера с Rage
```

### 4. Запуск бота

```bash
# Запускаем сервис
sudo systemctl start rage-bot

# Проверяем статус
sudo systemctl status rage-bot

# Смотрим логи
docker-compose logs -f rage-bot
```

## Ручная установка

### 1. Установка Docker

```bash
# Обновляем пакеты
sudo apt update

# Устанавливаем зависимости
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Добавляем GPG ключ Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавляем репозиторий
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Устанавливаем Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER

# Перелогиниваемся для применения изменений
```

### 2. Установка Docker Compose

```bash
# Скачиваем Docker Compose
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Делаем исполняемым
sudo chmod +x /usr/local/bin/docker-compose
```

### 3. Настройка проекта

```bash
# Создаем директорию проекта
sudo mkdir -p /opt/rage-restart-bot
sudo chown $USER:$USER /opt/rage-restart-bot
cd /opt/rage-restart-bot

# Клонируем репозиторий
git clone https://github.com/YOUR_USERNAME/rage-restart-bot.git .

# Настраиваем конфигурацию
cp config/config.yaml.example config/config.yaml
nano config/config.yaml
```

### 4. Запуск

```bash
# Собираем и запускаем контейнер
docker-compose up -d

# Проверяем логи
docker-compose logs -f
```

## Настройка CI/CD

### 1. Настройка GitHub Secrets

В настройках репозитория добавьте следующие секреты:

- `SERVER_HOST` - IP адрес вашего сервера
- `SERVER_USER` - имя пользователя для SSH
- `SERVER_SSH_KEY` - приватный SSH ключ
- `SERVER_PORT` - порт SSH (опционально, по умолчанию 22)

### 2. Настройка SSH ключей

```bash
# На локальной машине генерируем SSH ключ
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# Копируем публичный ключ на сервер
ssh-copy-id user@your-server-ip

# Приватный ключ добавляем в GitHub Secrets
```

### 3. Автоматическое развертывание

После настройки секретов, каждый push в ветку `main` будет автоматически:

1. Тестировать код
2. Собирать Docker образ
3. Развертывать на сервере

## Управление ботом

### Команды бота

- `/start` - Запустить бота
- `/status` - Проверить статус сервера
- `/restart` - Перезапустить сервер
- `/stop` - Остановить сервер
- `/start_server` - Запустить сервер
- `/logs` - Показать логи сервера
- `/info` - Информация о контейнере
- `/help` - Справка

### Системные команды

```bash
# Статус сервиса
sudo systemctl status rage-bot

# Перезапуск
sudo systemctl restart rage-bot

# Остановка
sudo systemctl stop rage-bot

# Логи
journalctl -u rage-bot -f

# Логи Docker
docker-compose logs -f rage-bot

# Обновление
cd /opt/rage-restart-bot
git pull
docker-compose pull
docker-compose up -d
```

## Безопасность

### Рекомендации

1. **Брандмауэр**: Настройте ufw или iptables
2. **SSH**: Отключите парольную аутентификацию
3. **Обновления**: Регулярно обновляйте систему
4. **Мониторинг**: Следите за логами
5. **Бэкапы**: Регулярно создавайте резервные копии конфигурации

### Настройка брандмауэра

```bash
# Включаем ufw
sudo ufw enable

# Разрешаем SSH
sudo ufw allow ssh

# Разрешаем порты Rage сервера (если нужно)
sudo ufw allow 30120
sudo ufw allow 30121/udp

# Проверяем статус
sudo ufw status
```

## Устранение неполадок

### Проблемы с Docker

```bash
# Проверка прав доступа к Docker socket
ls -la /var/run/docker.sock

# Перезапуск Docker
sudo systemctl restart docker

# Очистка Docker
docker system prune -f
```

### Проблемы с ботом

```bash
# Проверка конфигурации
python -c "from src.utils.config import config_manager; print('Config OK')"

# Проверка логов
docker-compose logs rage-bot

# Перезапуск контейнера
docker-compose restart rage-bot
```

### Проблемы с авторизацией

1. Проверьте ID группы в конфигурации
2. Убедитесь что бот добавлен в группу
3. Проверьте права бота в группе
4. Проверьте токен бота

## Обновление

### Автоматическое через CI/CD

Просто выполните push в ветку main - обновление произойдет автоматически.

### Ручное обновление

```bash
cd /opt/rage-restart-bot
git pull
docker-compose pull
docker-compose up -d
```

## Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs rage-bot`
2. Проверьте статус: `sudo systemctl status rage-bot`
3. Проверьте конфигурацию
4. Создайте issue в репозитории с описанием проблемы и логами