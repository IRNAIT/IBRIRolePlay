const express = require('express');
const path = require('path');
const app = express();
const port = process.env.PORT || 3000;

// Раздача статических файлов
app.use(express.static(path.join(__dirname, '..')));

// Маршрут для главной страницы
app.get('/', (req, res) => {
    try {
        const indexPath = path.join(__dirname, '..', 'index.html');
        console.log('Attempting to serve index.html from:', indexPath);
        res.sendFile(indexPath);
    } catch (error) {
        console.error('Error serving index.html:', error);
        res.status(500).send('Internal Server Error');
    }
});

// Обработка ошибок
app.use((err, req, res, next) => {
    console.error('Server error:', err);
    res.status(500).send('Something broke!');
});

// Запуск сервера
app.listen(port, '0.0.0.0', () => {
    console.log(`Сервер запущен на http://localhost:${port}`);
    console.log('Текущая директория:', __dirname);
    console.log('Путь к index.html:', path.join(__dirname, '..', 'index.html'));
}); 