const express = require('express');
const path = require('path');
const app = express();
const port = process.env.PORT || 3000;

// Раздача статических файлов
app.use(express.static('./'));

// Маршрут для главной страницы
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Запуск сервера
app.listen(port, '0.0.0.0', () => {
    console.log(`Сервер запущен на порту ${port}`);
}); 