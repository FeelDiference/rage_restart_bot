# Rage MP Server Status API Addon

HTTP API аддон для получения статуса Rage MP сервера. Предоставляет REST API endpoints для мониторинга сервера ботом.

## 🚀 Возможности

- **Статус сервера**: Получение общей информации о сервере
- **Список игроков**: Актуальная информация об онлайн игроках  
- **Проверка здоровья**: Health check endpoint для мониторинга
- **Безопасность**: IP-фильтрация для ограничения доступа
- **Совместимость**: Работает с ES modules и Rage MP environment

## 📦 Установка

### 1. Копирование файлов
```bash
# Скопируйте папку server-status в папку packages/ вашего Rage MP сервера
cp -r server-status /path/to/ragemp-server/packages/
```

### 2. Установка зависимостей
```bash
cd /path/to/ragemp-server/packages/server-status
npm install
```

### 3. Конфигурация
Отредактируйте настройки в `index.mjs`:

```javascript
const CONFIG = {
    PORT: 30120,                    // Порт для API
    API_PATH: '/api/status',        // Базовый путь API
    ALLOWED_IPS: [                  // Разрешенные IP
        '127.0.0.1',
        '::1',
        'YOUR_BOT_IP'               // IP вашего бота
    ],
    STATS_UPDATE_INTERVAL: 5000     // Интервал обновления (мс)
};
```

### 4. Перезапуск сервера
Перезапустите Rage MP сервер для загрузки аддона.

## 🔗 API Endpoints

### GET /api/status
Основная информация о сервере
```json
{
    "success": true,
    "timestamp": 1640995200000,
    "server": {
        "name": "My Rage Server",
        "gamemode": "RageMP", 
        "version": "1.0.0",
        "uptime": 3600000,
        "uptime_formatted": "1ч 0м",
        "status": "running"
    },
    "players": {
        "online": 15,
        "max": 100,
        "list": [...]
    },
    "performance": {
        "memoryUsage": 256.5,
        "ticksPerSecond": 60
    }
}
```

### GET /api/players
Подробный список игроков
```json
{
    "success": true,
    "count": 15,
    "max": 100,
    "players": [
        {
            "id": 1,
            "name": "Player1",
            "ping": 50,
            "ip": "127.0.0.1"
        }
    ],
    "timestamp": 1640995200000
}
```

### GET /api/health
Проверка работоспособности
```json
{
    "status": "ok",
    "timestamp": 1640995200000,
    "uptime": 3600000
}
```

### GET /api/info
Информация об API
```json
{
    "success": true,
    "server": {
        "name": "My Rage Server",
        "version": "1.0.0",
        "gamemode": "RageMP",
        "maxPlayers": 100,
        "startTime": 1640991600000
    },
    "api": {
        "version": "1.0",
        "endpoints": [
            "/api/status",
            "/api/players",
            "/api/health", 
            "/api/info"
        ]
    }
}
```

## 🔧 Особенности реализации

### Безопасный доступ к Rage MP API
Аддон проверяет доступность глобальных объектов `mp.*` и корректно обрабатывает случаи, когда они недоступны:

```javascript
function isMpAvailable() {
    return typeof mp !== 'undefined' && mp !== null;
}
```

### Кэширование данных
Статистика сервера обновляется периодически и кэшируется для быстрого доступа:

```javascript
setInterval(updateServerStats, CONFIG.STATS_UPDATE_INTERVAL);
```

### Обработка событий
Автоматическое обновление статистики при подключении/отключении игроков:

```javascript
mp.events.add('playerJoin', updateServerStats);
mp.events.add('playerQuit', updateServerStats);
```

## 🛡️ Безопасность

1. **IP-фильтрация**: Настройте `ALLOWED_IPS` для ограничения доступа
2. **Отдельный порт**: API работает на отдельном порту от игрового сервера
3. **Валидация входных данных**: Все входящие запросы проверяются
4. **Error handling**: Все ошибки перехватываются и логируются

## 🐛 Troubleshooting

### Ошибка "Cannot find package 'express'"
```bash
cd packages/server-status
npm install
```

### Порт уже используется
Измените `CONFIG.PORT` на свободный порт в `index.mjs`.

### API недоступен извне
1. Проверьте настройки firewall
2. Убедитесь, что порт открыт
3. Добавьте IP бота в `ALLOWED_IPS`

### Отсутствуют данные игроков
Убедитесь, что аддон загружен в Rage MP environment, а не как standalone Node.js приложение.

## 📝 Логи

Аддон выводит подробные логи для отладки:

```
[Status API] Аддон успешно загружен!
[Status API] Сервер запущен на порту 30120
[Status API] Серверная информация инициализирована из mp.config
[Status API] События игроков успешно зарегистрированы
```

## 🔄 Версионность

- **v1.0**: Базовая функциональность
  - REST API endpoints
  - Мониторинг игроков
  - Health checks
  - IP-фильтрация

## 📄 Лицензия

MIT License - см. файл LICENSE для деталей.