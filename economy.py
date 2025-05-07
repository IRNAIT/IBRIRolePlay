from typing import Dict, Tuple
import discord

class EconomySystem:
    def __init__(self, db):
        self.db = db
        self.players = db.players
        self.settings = db.settings

    async def get_balance(self, user_id: int) -> int:
        """Получение баланса игрока"""
        player = await self.players.find_one({"user_id": user_id})
        return player.get("balance", 0) if player else 0

    async def add_money(self, user_id: int, amount: int) -> Tuple[bool, str]:
        """Добавление денег игроку"""
        if amount <= 0:
            return False, "Сумма должна быть положительной"
            
        result = await self.players.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": amount}}
        )
        
        if result.modified_count > 0:
            return True, f"Добавлено {amount} монет"
        return False, "Игрок не найден"

    async def remove_money(self, user_id: int, amount: int) -> Tuple[bool, str]:
        """Снятие денег у игрока"""
        if amount <= 0:
            return False, "Сумма должна быть положительной"
            
        player = await self.players.find_one({"user_id": user_id})
        if not player:
            return False, "Игрок не найден"
            
        if player.get("balance", 0) < amount:
            return False, "Недостаточно средств"
            
        await self.players.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": -amount}}
        )
        return True, f"Снято {amount} монет"

    async def transfer_money(self, from_id: int, to_id: int, amount: int) -> Tuple[bool, str]:
        """Перевод денег между игроками"""
        if amount <= 0:
            return False, "Сумма должна быть положительной"
            
        # Проверка наличия средств
        from_player = await self.players.find_one({"user_id": from_id})
        if not from_player:
            return False, "Отправитель не найден"
            
        if from_player.get("balance", 0) < amount:
            return False, "Недостаточно средств"
            
        # Проверка получателя
        to_player = await self.players.find_one({"user_id": to_id})
        if not to_player:
            return False, "Получатель не найден"
            
        # Выполнение перевода
        await self.players.update_one(
            {"user_id": from_id},
            {"$inc": {"balance": -amount}}
        )
        
        await self.players.update_one(
            {"user_id": to_id},
            {"$inc": {"balance": amount}}
        )
        
        return True, f"Переведено {amount} монет"

    async def get_currency_name(self, guild_id: int) -> str:
        """Получение названия валюты для сервера"""
        settings = await self.settings.find_one({"guild_id": guild_id})
        return settings.get("currency_name", "монет") if settings else "монет"

def create_balance_embed(player: Dict, currency_name: str) -> discord.Embed:
    """Создание embed-сообщения для отображения баланса"""
    embed = discord.Embed(title="Баланс игрока", color=discord.Color.gold())
    
    embed.add_field(
        name=player["name"],
        value=f"Баланс: {player['balance']} {currency_name}",
        inline=False
    )
    
    return embed

def create_transaction_embed(from_player: Dict, to_player: Dict, amount: int, currency_name: str) -> discord.Embed:
    """Создание embed-сообщения для отображения транзакции"""
    embed = discord.Embed(title="Перевод средств", color=discord.Color.green())
    
    embed.add_field(
        name="Отправитель",
        value=f"{from_player['name']}\nБаланс: {from_player['balance']} {currency_name}",
        inline=True
    )
    
    embed.add_field(
        name="Получатель",
        value=f"{to_player['name']}\nБаланс: {to_player['balance']} {currency_name}",
        inline=True
    )
    
    embed.add_field(
        name="Сумма перевода",
        value=f"{amount} {currency_name}",
        inline=False
    )
    
    return embed 