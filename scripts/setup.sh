#!/bin/bash

# Скрипт первоначальной настройки Rage Restart Bot на сервере
# Запускать с правами sudo

set -e  # Остановка при ошибке

echo "🚀 Начало настройки Rage Restart Bot"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка прав root
if [[ $EUID -eq 0 ]]; then
   log_error "Не запускайте этот скрипт под root!"
   log_info "Используйте: sudo ./scripts/setup.sh"
   exit 1
fi

# Установка Docker если не установлен
install_docker() {
    if command -v docker &> /dev/null; then
        log_info "Docker уже установлен"
    else
        log_info "Установка Docker..."
        
        # Обновляем систему
        sudo apt-get update
        
        # Устанавливаем зависимости
        sudo apt-get install -y \
            apt-transport-https \
            ca-certificates \
            curl \
            gnupg \
            lsb-release
        
        # Добавляем GPG ключ Docker
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        
        # Добавляем репозиторий Docker
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Устанавливаем Docker
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io
        
        # Добавляем пользователя в группу docker
        sudo usermod -aG docker $USER
        
        log_info "Docker установлен успешно"
    fi
}

# Установка Docker Compose если не установлен
install_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        log_info "Docker Compose уже установлен"
    else
        log_info "Установка Docker Compose..."
        
        # Скачиваем последнюю версию
        DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
        sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        
        # Делаем исполняемым
        sudo chmod +x /usr/local/bin/docker-compose
        
        log_info "Docker Compose установлен успешно"
    fi
}

# Создание структуры директорий
setup_directories() {
    log_info "Создание структуры директорий..."
    
    # Основная директория проекта
    PROJECT_DIR="/opt/rage-restart-bot"
    sudo mkdir -p $PROJECT_DIR
    sudo chown $USER:$USER $PROJECT_DIR
    
    # Переходим в директорию проекта
    cd $PROJECT_DIR
    
    # Создаем поддиректории
    mkdir -p {logs,config,data,scripts}
    
    log_info "Структура директорий создана: $PROJECT_DIR"
}

# Клонирование репозитория
clone_repository() {
    log_info "Клонирование репозитория..."
    
    if [ -d ".git" ]; then
        log_info "Репозиторий уже склонирован, обновляем..."
        git pull
    else
        # Замените на ваш URL репозитория
        REPO_URL="https://github.com/YOUR_USERNAME/rage-restart-bot.git"
        log_warn "Измените REPO_URL в скрипте на ваш репозиторий!"
        log_info "Клонирование из: $REPO_URL"
        
        git clone $REPO_URL .
    fi
}

# Настройка конфигурации
setup_config() {
    log_info "Настройка конфигурации..."
    
    # Копируем пример конфигурации если нет основной
    if [ ! -f "config/config.yaml" ]; then
        cp config/config.yaml config/config.yaml.example
        log_warn "Необходимо настроить config/config.yaml!"
        log_info "Пример конфигурации создан: config/config.yaml.example"
    fi
    
    # Создаем .env файл для docker-compose
    if [ ! -f ".env" ]; then
        cat > .env << EOL
# Переменные окружения для Rage Restart Bot

# Timezone
TZ=Europe/Moscow

# Docker network
COMPOSE_PROJECT_NAME=rage-bot

# Ресурсы
BOT_MEMORY_LIMIT=256m
BOT_CPU_LIMIT=0.5

EOL
        log_info "Файл .env создан"
    fi
}

# Настройка systemd сервиса
setup_systemd() {
    log_info "Настройка systemd сервиса..."
    
    sudo tee /etc/systemd/system/rage-bot.service > /dev/null << EOL
[Unit]
Description=Rage Restart Bot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/rage-restart-bot
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
ExecReload=/usr/local/bin/docker-compose restart
TimeoutStartSec=0
User=$USER
Group=$USER

[Install]
WantedBy=multi-user.target
EOL

    # Перезагружаем systemd и включаем сервис
    sudo systemctl daemon-reload
    sudo systemctl enable rage-bot.service
    
    log_info "Systemd сервис настроен и включен"
}

# Настройка логротации
setup_logrotate() {
    log_info "Настройка ротации логов..."
    
    sudo tee /etc/logrotate.d/rage-bot > /dev/null << EOL
/opt/rage-restart-bot/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 $USER $USER
    postrotate
        /usr/local/bin/docker-compose -f /opt/rage-restart-bot/docker-compose.yml restart rage-bot > /dev/null 2>&1 || true
    endscript
}
EOL

    log_info "Ротация логов настроена"
}

# Основная функция
main() {
    log_info "Начало установки..."
    
    # Проверяем ОС
    if [[ ! -f /etc/os-release ]]; then
        log_error "Неподдерживаемая операционная система"
        exit 1
    fi
    
    . /etc/os-release
    if [[ $ID != "ubuntu" && $ID != "debian" ]]; then
        log_warn "Скрипт протестирован только на Ubuntu/Debian"
    fi
    
    # Выполняем установку
    install_docker
    install_docker_compose
    setup_directories
    clone_repository
    setup_config
    setup_systemd
    setup_logrotate
    
    log_info "✅ Установка завершена!"
    log_warn "Не забудьте:"
    log_warn "1. Настроить config/config.yaml с вашими данными"
    log_warn "2. Запустить сервис: sudo systemctl start rage-bot"
    log_warn "3. Проверить статус: sudo systemctl status rage-bot"
    log_warn "4. Просмотреть логи: docker-compose logs -f"
    
    if groups $USER | grep &>/dev/null '\bdocker\b'; then
        log_info "Пользователь уже в группе docker"
    else
        log_warn "Необходимо перелогиниться для применения группы docker"
    fi
}

# Запуск основной функции
main "$@"