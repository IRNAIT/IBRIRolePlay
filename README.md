# Discord RPG Bot

Бот для ролевых игр в Discord с системой инвентаря, экономики и боевой системой.

## Требования

- Python 3.8 или выше
- MongoDB
- Discord Bot Token

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/discord-rpg-bot.git
cd discord-rpg-bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` в корневой директории и добавьте в него токен бота:
```
DISCORD_TOKEN=your_bot_token_here
```

4. Запустите MongoDB:
```bash
mongod
```

5. Запустите бота:
```bash
python bot.py
```

## Основные команды

### Общие команды
- `/регистрация` - регистрация нового игрока
- `/профиль` - просмотр профиля игрока
- `/инвентарь` - просмотр инвентаря
- `/баланс` - просмотр баланса

### Боевые команды
- `/атака [цель]` - атака цели
- `/защита` - активация защиты

### Экономические команды
- `/перевод [игрок] [сумма]` - перевод денег другому игроку
- `/магазин` - просмотр магазина

### Административные команды
- `/настройка` - настройка бота
- `/старт` - запуск бота
- `/сброс` - сброс всех данных
- `/выдать [игрок] [предмет] [количество]` - выдача предметов
- `/выдать_деньги [игрок] [сумма]` - выдача денег

## Настройка сервера

1. Пригласите бота на сервер
2. Используйте команду `/настройка` для настройки параметров:
   - Название валюты
   - Максимальное количество слотов инвентаря
   - Длительность эффекта защиты
3. Загрузите предметы из файлов с помощью команды `/загрузить`
4. Запустите бота командой `/старт`

## Форматы файлов

### Оружие
```
[Название]
Тип: [тип оружия]
Урон: [базовый урон]
Разброс: [минимальный урон] - [максимальный урон]
Критический шанс: [шанс в %]
Критический множитель: [множитель]
Описание: [текстовое описание]
```

### Броня
```
[Название]
Тип: [тип брони]
Защита: [значение защиты в %]
Дополнительное здоровье: [количество HP]
Слот: [слот экипировки]
Описание: [текстовое описание]
```

### Расходники
```
[Название]
Тип: consumable
Эффект: [тип эффекта]
Значение: [значение эффекта]
Описание: [текстовое описание]
```

## Лицензия

MIT 