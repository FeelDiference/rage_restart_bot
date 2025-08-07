/**
 * Rage MP Server Status API Addon
 * Простой HTTP сервер для предоставления информации о статусе сервера боту
 * 
 * Установка:
 * 1. Поместите эту папку в packages/ вашего Rage сервера
 * 2. Перезапустите сервер
 * 3. API будет доступен по адресу: http://server-ip:30120/api/status
 */

import express from 'express';

// Конфигурация
const CONFIG = {
    // Порт для HTTP API (обычно основной порт сервера)
    PORT: 30120,
    
    // Путь для API
    API_PATH: '/api/status',
    
    // Разрешенные IP для доступа к API (для безопасности)
    ALLOWED_IPS: [
        '127.0.0.1',
        '::1',
        '78.37.40.131',  // IP вашего бота
        // Добавьте другие IP если нужно
    ],
    
    // Интервал обновления статистики (мс)
    STATS_UPDATE_INTERVAL: 5000
};

// Глобальные переменные для хранения статистики
let serverStats = {
    startTime: Date.now(),
    players: {
        online: 0,
        max: mp.config.maxplayers || 100,
        list: []
    },
    server: {
        name: mp.config.name || 'Rage MP Server',
        gamemode: 'RageMP',
        version: mp.version || 'Unknown',
        uptime: 0,
        status: 'running'
    },
    performance: {
        memoryUsage: 0,
        ticksPerSecond: 60
    },
    lastUpdate: Date.now()
};

// Создаем Express приложение
const app = express();

// Middleware для логирования
app.use((req, res, next) => {
    console.log(`[Status API] ${req.method} ${req.path} от ${req.ip}`);
    next();
});

// Middleware для проверки IP (базовая безопасность)
app.use((req, res, next) => {
    const clientIP = req.ip || req.connection.remoteAddress;
    
    // В продакшн можно раскомментировать для строгой проверки IP
    // if (!CONFIG.ALLOWED_IPS.includes(clientIP)) {
    //     console.log(`[Status API] Отклонен доступ с IP: ${clientIP}`);
    //     return res.status(403).json({ error: 'Доступ запрещен' });
    // }
    
    next();
});

// Middleware для JSON
app.use(express.json());

/**
 * Основной endpoint для получения статуса сервера
 * GET /api/status
 */
app.get(CONFIG.API_PATH, (req, res) => {
    try {
        // Обновляем uptime
        serverStats.server.uptime = Date.now() - serverStats.startTime;
        serverStats.lastUpdate = Date.now();
        
        // Формируем ответ
        const response = {
            success: true,
            timestamp: Date.now(),
            server: {
                ...serverStats.server,
                uptime_formatted: formatUptime(serverStats.server.uptime)
            },
            players: serverStats.players,
            performance: serverStats.performance
        };
        
        res.json(response);
        
    } catch (error) {
        console.error('[Status API] Ошибка при получении статуса:', error);
        res.status(500).json({
            success: false,
            error: 'Внутренняя ошибка сервера',
            timestamp: Date.now()
        });
    }
});

/**
 * Endpoint для получения списка игроков
 * GET /api/players
 */
app.get('/api/players', (req, res) => {
    try {
        const players = mp.players.toArray().map(player => ({
            id: player.id,
            name: player.name || 'Unknown',
            ping: player.ping || 0,
            ip: player.ip || 'Unknown'
        }));
        
        res.json({
            success: true,
            count: players.length,
            max: serverStats.players.max,
            players: players,
            timestamp: Date.now()
        });
        
    } catch (error) {
        console.error('[Status API] Ошибка при получении списка игроков:', error);
        res.status(500).json({
            success: false,
            error: 'Ошибка получения списка игроков'
        });
    }
});

/**
 * Endpoint для базовой проверки здоровья
 * GET /api/health
 */
app.get('/api/health', (req, res) => {
    res.json({
        status: 'ok',
        timestamp: Date.now(),
        uptime: Date.now() - serverStats.startTime
    });
});

/**
 * Endpoint для получения информации о сервере
 * GET /api/info
 */
app.get('/api/info', (req, res) => {
    res.json({
        success: true,
        server: {
            name: serverStats.server.name,
            version: serverStats.server.version,
            gamemode: serverStats.server.gamemode,
            maxPlayers: serverStats.players.max,
            startTime: serverStats.startTime
        },
        api: {
            version: '1.0',
            endpoints: [
                '/api/status',
                '/api/players', 
                '/api/health',
                '/api/info'
            ]
        }
    });
});

/**
 * Форматирует время работы в читаемый вид
 */
function formatUptime(uptimeMs) {
    const seconds = Math.floor(uptimeMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) {
        return `${days}д ${hours % 24}ч ${minutes % 60}м`;
    } else if (hours > 0) {
        return `${hours}ч ${minutes % 60}м`;
    } else if (minutes > 0) {
        return `${minutes}м ${seconds % 60}с`;
    } else {
        return `${seconds}с`;
    }
}

/**
 * Обновляет статистику сервера
 */
function updateServerStats() {
    try {
        // Обновляем информацию об игроках
        const players = mp.players.toArray();
        serverStats.players.online = players.length;
        serverStats.players.list = players.map(p => ({
            id: p.id,
            name: p.name || 'Unknown'
        }));
        
        // Обновляем производительность (базовая информация)
        serverStats.performance.memoryUsage = process.memoryUsage().heapUsed / 1024 / 1024; // MB
        
        // Обновляем время последнего обновления
        serverStats.lastUpdate = Date.now();
        
    } catch (error) {
        console.error('[Status API] Ошибка обновления статистики:', error);
    }
}

// Запускаем HTTP сервер
app.listen(CONFIG.PORT, '0.0.0.0', () => {
    console.log(`[Status API] Сервер запущен на порту ${CONFIG.PORT}`);
    console.log(`[Status API] Доступные endpoints:`);
    console.log(`  - GET http://localhost:${CONFIG.PORT}${CONFIG.API_PATH}`);
    console.log(`  - GET http://localhost:${CONFIG.PORT}/api/players`);
    console.log(`  - GET http://localhost:${CONFIG.PORT}/api/health`);
    console.log(`  - GET http://localhost:${CONFIG.PORT}/api/info`);
});

// Периодическое обновление статистики
setInterval(updateServerStats, CONFIG.STATS_UPDATE_INTERVAL);

// События игроков для обновления статистики в реальном времени
mp.events.add('playerJoin', (player) => {
    console.log(`[Status API] Игрок подключился: ${player.name} (${player.id})`);
    updateServerStats();
});

mp.events.add('playerQuit', (player, exitType, reason) => {
    console.log(`[Status API] Игрок отключился: ${player.name} (${player.id})`);
    updateServerStats();
});

// Инициализация при загрузке
updateServerStats();

console.log('[Status API] Аддон успешно загружен!');
console.log('[Status API] Версия: 1.0');
console.log('[Status API] Статус: Активен');