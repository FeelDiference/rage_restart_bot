# Настройка развертывания для приватного репозитория

Инструкции по настройке GitHub Actions для автоматического развертывания на сервер `81.177.220.187:22`.

## 🔑 Настройка SSH ключей

### 1. Генерация SSH ключей

На вашей локальной машине:

```bash
# Генерируем SSH ключ специально для развертывания
ssh-keygen -t rsa -b 4096 -C "deploy@rage-bot" -f ~/.ssh/rage_bot_deploy

# Создается два файла:
# ~/.ssh/rage_bot_deploy      (приватный ключ)
# ~/.ssh/rage_bot_deploy.pub  (публичный ключ)
```

### 2. Настройка сервера

Скопируйте публичный ключ на сервер:

```bash
# Отправляем публичный ключ на сервер
ssh-copy-id -i ~/.ssh/rage_bot_deploy.pub -p 22 username@81.177.220.187

# Или вручную:
cat ~/.ssh/rage_bot_deploy.pub | ssh -p 22 username@81.177.220.187 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### 3. Тестирование подключения

```bash
# Проверяем что SSH подключение работает
ssh -i ~/.ssh/rage_bot_deploy -p 22 username@81.177.220.187

# Если подключение успешно, вы попадете на сервер
```

## 🔒 Настройка GitHub Secrets

В настройках вашего приватного репозитория добавьте следующие секреты:

### 1. Переходим в настройки репозитория

```
GitHub → Ваш репозиторий → Settings → Secrets and variables → Actions
```

### 2. Добавляем секреты

| Название | Значение | Описание |
|----------|----------|----------|
| `SERVER_USER` | `username` | Имя пользователя на сервере |
| `SERVER_SSH_KEY` | Содержимое `~/.ssh/rage_bot_deploy` | Приватный SSH ключ |

**Получение приватного ключа:**
```bash
cat ~/.ssh/rage_bot_deploy
```

Скопируйте весь вывод (включая `-----BEGIN OPENSSH PRIVATE KEY-----` и `-----END OPENSSH PRIVATE KEY-----`) и вставьте в секрет `SERVER_SSH_KEY`.

## 🔐 Настройка Deploy ключа для Git

Для клонирования приватного репозитория на сервере создайте отдельный Deploy Key:

### 1. Генерация Deploy ключа

```bash
# Генерируем ключ для Git
ssh-keygen -t rsa -b 4096 -C "git-deploy@rage-bot" -f ~/.ssh/rage_bot_git_deploy
```

### 2. Добавление Deploy Key в GitHub

1. Идем в: `GitHub → Ваш репозиторий → Settings → Deploy keys`
2. Нажимаем **Add deploy key**
3. Title: `Production Server Deploy`
4. Key: Содержимое файла `~/.ssh/rage_bot_git_deploy.pub`
5. ✅ Allow write access (если нужно)
6. Нажимаем **Add key**

### 3. Настройка Git на сервере

На сервере `81.177.220.187` создайте SSH конфигурацию:

```bash
# Подключаемся к серверу
ssh -i ~/.ssh/rage_bot_deploy -p 22 username@81.177.220.187

# Создаем SSH конфигурацию
mkdir -p ~/.ssh
cat > ~/.ssh/config << 'EOF'
Host github.com-rage-bot
    HostName github.com
    User git
    IdentityFile ~/.ssh/rage_bot_git_deploy
    IdentitiesOnly yes
EOF

# Копируем Deploy ключ на сервер (делается при развертывании)
```

### 4. Обновление GitHub Actions

В файле `.github/workflows/deploy.yml` уже настроено клонирование с правильными ключами.

## 🚀 Первоначальное развертывание

### 1. Ручная настройка сервера

Подключитесь к серверу и выполните первоначальную настройку:

```bash
# Подключаемся к серверу
ssh -i ~/.ssh/rage_bot_deploy -p 22 username@81.177.220.187

# Устанавливаем Docker (если не установлен)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Создаем директорию проекта
sudo mkdir -p /opt/rage-restart-bot
sudo chown $USER:$USER /opt/rage-restart-bot

# Перелогиниваемся для применения группы docker
exit
```

### 2. Копирование Git Deploy ключа

```bash
# С локальной машины копируем Deploy ключ на сервер
scp -i ~/.ssh/rage_bot_deploy -P 22 ~/.ssh/rage_bot_git_deploy username@81.177.220.187:~/.ssh/
scp -i ~/.ssh/rage_bot_deploy -P 22 ~/.ssh/rage_bot_git_deploy.pub username@81.177.220.187:~/.ssh/

# Устанавливаем правильные права
ssh -i ~/.ssh/rage_bot_deploy -p 22 username@81.177.220.187 "chmod 600 ~/.ssh/rage_bot_git_deploy && chmod 644 ~/.ssh/rage_bot_git_deploy.pub"
```

### 3. Первое развертывание

После push в ветку `main` GitHub Actions автоматически:

1. Соберет Docker образ
2. Подключится к серверу по SSH
3. Склонирует репозиторий
4. Запустит контейнеры

## 🔧 Настройка конфигурации на сервере

После первого развертывания необходимо настроить конфигурацию:

```bash
# Подключаемся к серверу
ssh -i ~/.ssh/rage_bot_deploy -p 22 username@81.177.220.187

# Переходим в директорию проекта
cd /opt/rage-restart-bot

# Копируем и редактируем конфигурацию
cp config/config.yaml.example config/config.yaml
nano config/config.yaml

# Основные параметры для изменения:
# - telegram.token: ваш токен бота
# - telegram.allowed_groups: ID ваших групп
# - telegram.admin_users: ваш Telegram ID
# - docker.container_name: имя Rage контейнера

# Перезапускаем бот с новой конфигурацией
docker-compose restart rage-bot
```

## 📊 Проверка развертывания

### 1. Проверка статуса контейнера

```bash
# На сервере
cd /opt/rage-restart-bot
docker-compose ps
docker-compose logs rage-bot
```

### 2. Проверка работы бота

1. В Telegram группе выполните `/start`
2. Проверьте ответ бота
3. Выполните `/status` для проверки мониторинга

## 🔄 Обновления

После каждого push в `main`:

1. GitHub Actions автоматически соберет новый образ
2. Развернет на сервер
3. Перезапустит контейнер

Логи развертывания можно посмотреть в разделе **Actions** репозитория.

## 🆘 Устранение неполадок

### SSH подключение не работает

```bash
# Проверка SSH подключения с отладкой
ssh -v -i ~/.ssh/rage_bot_deploy -p 22 username@81.177.220.187

# Проверка прав на ключи
ls -la ~/.ssh/rage_bot_deploy*
chmod 600 ~/.ssh/rage_bot_deploy
chmod 644 ~/.ssh/rage_bot_deploy.pub
```

### Git клонирование не работает

```bash
# На сервере проверяем Git SSH
ssh -T git@github.com-rage-bot

# Должно вывести: Hi USERNAME! You've successfully authenticated
```

### Docker не запускается

```bash
# Проверка Docker
sudo systemctl status docker
sudo systemctl start docker

# Проверка прав пользователя
groups $USER
# Должна быть группа docker
```

### Бот не отвечает

```bash
# Проверка логов
cd /opt/rage-restart-bot
docker-compose logs rage-bot

# Проверка конфигурации
cat config/config.yaml

# Перезапуск
docker-compose restart rage-bot
```