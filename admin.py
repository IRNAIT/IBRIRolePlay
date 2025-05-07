from typing import Dict, List, Optional, Any
import discord
from discord import app_commands

class AdminSystem:
    def __init__(self, db: Any):
        self.db = db
        self.players = db.rpg_bot.players
        self.settings = db.rpg_bot.settings
        self.items = db.rpg_bot.items
        self.roles = db.rpg_bot.roles

    async def setup_server(self, guild_id: int, settings: Dict) -> bool:
        """Настройка сервера"""
        try:
            # Базовые настройки
            await self.settings.update_one(
                {"guild_id": guild_id},
                {"$set": settings},
                upsert=True
            )
            
            # Настройка ролей
            default_roles = {
                "admin": {
                    "name": "Администратор",
                    "permissions": ["all"]
                },
                "technician": {
                    "name": "Техник",
                    "permissions": [
                        "manage_items",
                        "manage_players",
                        "manage_economy",
                        "manage_combat",
                        "view_logs"
                    ]
                },
                "leader": {
                    "name": "Ведущий",
                    "permissions": [
                        "manage_items",
                        "manage_players",
                        "manage_economy",
                        "manage_combat",
                        "view_logs"
                    ]
                }
            }
            
            await self.roles.update_one(
                {"guild_id": guild_id},
                {"$set": {"roles": default_roles}},
                upsert=True
            )
            
            return True
        except Exception as e:
            print(f"Ошибка при настройке сервера: {e}")
            return False

    async def check_permission(self, guild_id: int, role_name: str, permission: str) -> bool:
        """Проверка прав роли"""
        role_data = await self.roles.find_one({"guild_id": guild_id})
        if not role_data:
            return False
            
        role = role_data.get("roles", {}).get(role_name)
        if not role:
            return False
            
        permissions = role.get("permissions", [])
        return "all" in permissions or permission in permissions

    async def get_role_permissions(self, guild_id: int, role_name: str) -> List[str]:
        """Получение списка прав роли"""
        role_data = await self.roles.find_one({"guild_id": guild_id})
        if not role_data:
            return []
            
        role = role_data.get("roles", {}).get(role_name)
        return role.get("permissions", []) if role else []

    async def add_role(self, guild_id: int, role_name: str, permissions: List[str]) -> bool:
        """Добавление новой роли"""
        try:
            await self.roles.update_one(
                {"guild_id": guild_id},
                {"$set": {f"roles.{role_name}": {"name": role_name, "permissions": permissions}}},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Ошибка при добавлении роли: {e}")
            return False

    async def remove_role(self, guild_id: int, role_name: str) -> bool:
        """Удаление роли"""
        try:
            await self.roles.update_one(
                {"guild_id": guild_id},
                {"$unset": {f"roles.{role_name}": ""}}
            )
            return True
        except Exception as e:
            print(f"Ошибка при удалении роли: {e}")
            return False

    async def get_server_settings(self, guild_id: int) -> Optional[Dict]:
        """Получение настроек сервера"""
        return await self.settings.find_one({"guild_id": guild_id})

    async def reset_server(self, guild_id: int) -> bool:
        """Сброс всех данных сервера"""
        try:
            await self.settings.delete_one({"guild_id": guild_id})
            await self.players.delete_many({"guild_id": guild_id})
            await self.items.delete_many({"guild_id": guild_id})
            return True
        except Exception as e:
            print(f"Ошибка при сбросе сервера: {e}")
            return False

    async def create_npc(self, guild_id: int, npc_data: Dict) -> bool:
        """Создание NPC"""
        try:
            npc_data["guild_id"] = guild_id
            npc_data["type"] = "npc"
            await self.players.insert_one(npc_data)
            return True
        except Exception as e:
            print(f"Ошибка при создании NPC: {e}")
            return False

    async def load_items_from_file(self, guild_id: int, items_data: List[Dict]) -> bool:
        """Загрузка предметов из файла"""
        try:
            for item in items_data:
                item["guild_id"] = guild_id
                await self.items.update_one(
                    {"guild_id": guild_id, "name": item["name"]},
                    {"$set": item},
                    upsert=True
                )
            return True
        except Exception as e:
            print(f"Ошибка при загрузке предметов: {e}")
            return False

def create_settings_embed(settings: Dict) -> discord.Embed:
    """Создание embed-сообщения для отображения настроек"""
    embed = discord.Embed(title="Настройки сервера", color=discord.Color.blue())
    
    embed.add_field(
        name="Основные настройки",
        value=f"Название валюты: {settings.get('currency_name', 'монет')}\n"
              f"Макс. слотов инвентаря: {settings.get('max_inventory_slots', 20)}\n"
              f"Длительность защиты: {settings.get('defense_duration', 3)} ходов",
        inline=False
    )
    
    return embed

def create_npc_embed(npc: Dict) -> discord.Embed:
    """Создание embed-сообщения для отображения NPC"""
    embed = discord.Embed(title=f"NPC: {npc['name']}", color=discord.Color.purple())
    
    embed.add_field(
        name="Характеристики",
        value=f"Здоровье: {npc['stats']['health']}\n"
              f"Атака: {npc['stats']['attack']}\n"
              f"Защита: {npc['stats']['defense']}",
        inline=True
    )
    
    if "description" in npc:
        embed.add_field(
            name="Описание",
            value=npc["description"],
            inline=False
        )
    
    return embed 