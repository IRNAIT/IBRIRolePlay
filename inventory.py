import discord
from typing import List, Dict, Optional, Tuple

class InventoryManager:
    def __init__(self, db):
        self.db = db
        self.items = db.items
        self.players = db.players

    async def add_item(self, user_id: int, item: Dict):
        """Добавление предмета в инвентарь игрока"""
        player = await self.players.find_one({"user_id": user_id})
        if not player:
            return False, "Игрок не найден"

        # Проверка на ограничение слотов
        settings = await self.db.settings.find_one({"guild_id": player.get("guild_id")})
        max_slots = settings.get("max_inventory_slots", 20)
        
        if len(player["inventory"]) >= max_slots:
            return False, "Инвентарь полон"

        await self.players.update_one(
            {"user_id": user_id},
            {"$push": {"inventory": item}}
        )
        return True, "Предмет добавлен в инвентарь"

    async def remove_item(self, user_id: int, item_id: str):
        """Удаление предмета из инвентаря"""
        result = await self.players.update_one(
            {"user_id": user_id},
            {"$pull": {"inventory": {"id": item_id}}}
        )
        return result.modified_count > 0

    async def get_inventory(self, user_id: int) -> List[Dict]:
        """Получение инвентаря игрока"""
        player = await self.players.find_one({"user_id": user_id})
        return player.get("inventory", []) if player else []

    async def equip_item(self, user_id: int, item_name: str) -> Tuple[bool, str]:
        """Экипировка предмета"""
        player = await self.players.find_one({"user_id": user_id})
        if not player:
            return False, "Игрок не найден"
            
        # Получение настроек сервера
        settings = await self.db.settings.find_one({"guild_id": player.get("guild_id")})
        max_equipped = settings.get("max_equipped_items", 5)  # По умолчанию 5 предметов
        
        # Проверка количества экипированных предметов
        current_equipped = len(player.get("equipment", {}))
        if current_equipped >= max_equipped:
            return False, f"Достигнут лимит экипированных предметов ({max_equipped})"
            
        # Поиск предмета в инвентаре
        inventory = player.get("inventory", [])
        item = next((i for i in inventory if i["name"].lower() == item_name.lower()), None)
        
        if not item:
            return False, "Предмет не найден в инвентаре"
            
        if item["type"] not in ["weapon", "armor"]:
            return False, "Этот предмет нельзя экипировать"
            
        # Проверка слота для брони
        if item["type"] == "armor":
            slot = item.get("slot")
            if not slot:
                return False, "У предмета не указан слот"
                
            # Проверка, не занят ли слот
            if player.get("equipment", {}).get(slot):
                return False, f"Слот {slot} уже занят"
                
            # Экипировка брони
            await self.players.update_one(
                {"user_id": user_id},
                {
                    "$set": {f"equipment.{slot}": item},
                    "$pull": {"inventory": {"name": item["name"]}}
                }
            )
            return True, f"Экипирована броня: {item['name']}"
            
        # Экипировка оружия
        if player.get("equipment", {}).get("weapon"):
            return False, "У вас уже экипировано оружие"
            
        await self.players.update_one(
            {"user_id": user_id},
            {
                "$set": {"equipment.weapon": item},
                "$pull": {"inventory": {"name": item["name"]}}
            }
        )
        return True, f"Экипировано оружие: {item['name']}"

    async def unequip_item(self, user_id: int, item_type: str):
        """Снятие предмета"""
        player = await self.players.find_one({"user_id": user_id})
        if not player:
            return False, "Игрок не найден"

        equipment = player.get("equipment", {})
        if item_type not in equipment or not equipment[item_type]:
            return False, "Нет экипированного предмета этого типа"

        item = equipment[item_type]
        equipment[item_type] = None

        # Добавление предмета обратно в инвентарь
        await self.players.update_one(
            {"user_id": user_id},
            {
                "$set": {"equipment": equipment},
                "$push": {"inventory": item}
            }
        )
        return True, f"Предмет {item['name']} снят"

def create_inventory_embed(inventory: List[Dict], equipment: Dict) -> discord.Embed:
    """Создание embed-сообщения для отображения инвентаря"""
    embed = discord.Embed(title="Инвентарь", color=discord.Color.green())
    
    # Отображение экипировки
    embed.add_field(
        name="Экипировка",
        value=f"Оружие: {equipment.get('weapon', {}).get('name', 'Нет')}\n"
              f"Броня: {equipment.get('armor', {}).get('name', 'Нет')}",
        inline=False
    )
    
    # Отображение инвентаря
    if inventory:
        items_text = "\n".join([f"• {item['name']} (x{item.get('quantity', 1)})" for item in inventory])
        embed.add_field(name="Предметы", value=items_text, inline=False)
    else:
        embed.add_field(name="Предметы", value="Инвентарь пуст", inline=False)
    
    return embed 