# Rage MP Server Status API Addon

Простой HTTP API аддон для Rage MP сервера, который предоставляет информацию о статусе сервера для Telegram бота.

## 📁 Установка

### 1. Копирование файлов

```bash
# Скопируйте папку server-status в директорию packages вашего Rage сервера
cp -r rage-server-addon/server-status /path/to/your/ragemp/server/packages/
```

### 2. Установка зависимостей

```bash
# Перейдите в папку аддона
cd /path/to/your/ragemp/server/packages/server-status

# Установите зависимости
npm install
```

### 3. Перезапуск сервера

Перезапустите ваш Rage MP сервер. Аддон автоматически загрузится.

## 🔌 API Endpoints

После установки API будет доступен на основном порту сервера (обычно 30120):

### `/api/status` - Основной статус сервера

```bash
curl http://your-server:30120/api/status
```

**Ответ:**
```json
{
  "success": true,
  "timestamp": 1703123456789,
  "server": {
    "name": "My Rage Server",
    "gamemode": "RageMP",
    "version": "1.0",
    "uptime": 3600000,
    "uptime_formatted": "1ч 0м",
    "status": "running"
  },
  "players": {
    "online": 15,
    "max": 100,
    "list": [
      {"id": 1, "name": "Player1"},
      {"id": 2, "name": "Player2"}
    ]
  },
  "performance": {
    "memoryUsage": 256.5,
    "ticksPerSecond": 60
  }
}
```

### `/api/players` - Список игроков

```bash
curl http://your-server:30120/api/players
```

### `/api/health` - Проверка здоровья

```bash
curl http://your-server:30120/api/health
```

### `/api/info` - Информация о сервере

```bash
curl http://your-server:30120/api/info
```

## ⚙️ Конфигурация

Отредактируйте переменную `CONFIG` в файле `index.mjs`:

```javascript
const CONFIG = {
    PORT: 30120,                    // Порт API
    API_PATH: '/api/status',        // Путь к основному API
    ALLOWED_IPS: [                  // Разрешенные IP
        '127.0.0.1',
        '81.177.220.187'              // IP вашего бота
    ],
    STATS_UPDATE_INTERVAL: 5000     // Интервал обновления (мс)
};
```

## 🔒 Безопасность

### IP фильтрация

По умолчанию доступ разрешен с любых IP. Для продакшн среды раскомментируйте блок проверки IP:

```javascript
if (!CONFIG.ALLOWED_IPS.includes(clientIP)) {
    return res.status(403).json({ error: 'Доступ запрещен' });
}
```

### Firewall

Рекомендуется настроить firewall для ограничения доступа к API:

```bash
# Разрешить доступ только с IP бота
sudo ufw allow from 81.177.220.187 to any port 30120
```

## 🐛 Отладка

### Проверка работы аддона

1. **Проверьте логи сервера** на наличие сообщений:
   ```
   [Status API] Аддон успешно загружен!
   [Status API] Сервер запущен на порту 30120
   ```

2. **Тест API локально:**
   ```bash
   curl http://localhost:30120/api/health
   ```

3. **Проверка из бота:**
   Убедитесь что URL в конфигурации бота указывает правильно:
   ```yaml
   monitoring:
     health_check_url: "http://81.177.220.187:30120/api/status"
   ```

### Типичные проблемы

1. **Порт занят** - измените порт в CONFIG или убедитесь что основной сервер не использует другой порт

2. **Express не найден** - установите зависимости: `npm install`

3. **API не отвечает** - проверьте что аддон загружен и нет ошибок в логах сервера

## 📊 Мониторинг

Аддон автоматически:
- Обновляет статистику каждые 5 секунд
- Отслеживает подключения/отключения игроков
- Логирует все запросы к API

## 🔄 Интеграция с ботом

Убедитесь что в конфигурации бота указан правильный URL:

```yaml
# config/config.yaml
monitoring:
  health_check_url: "http://81.177.220.187:30120/api/status"
  host: "81.177.220.187"
  tcp_ports:
    - 30120
    - 30121
    - 30122
```

## 📈 Расширение функциональности

Для добавления новых endpoints создайте их в `index.mjs`:

```javascript
// Пример: получение экономической статистики
app.get('/api/economy', (req, res) => {
    res.json({
        success: true,
        economy: {
            totalMoney: getTotalServerMoney(),
            activeBusiness: getActiveBusinessCount()
        }
    });
});
```

## 🆘 Поддержка

При проблемах:
1. Проверьте логи Rage MP сервера
2. Убедитесь что зависимости установлены
3. Проверьте доступность порта
4. Создайте issue в репозитории с логами