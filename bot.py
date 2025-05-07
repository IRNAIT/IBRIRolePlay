import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import motor.motor_asyncio
import json
import logging
from inventory import InventoryManager, create_inventory_embed
from combat import CombatSystem, create_combat_embed
from economy import EconomySystem, create_balance_embed, create_transaction_embed
from admin import AdminSystem, create_settings_embed, create_npc_embed
from typing import Dict

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Настройка интентов бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Инициализация бота
bot = commands.Bot(command_prefix='/', intents=intents)

# Подключение к MongoDB
client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
db = client.rpg_bot

# Инициализация систем
inventory_manager = InventoryManager(db)
combat_system = CombatSystem(db)
economy_system = EconomySystem(db)
admin_system = AdminSystem(client)

# Класс для работы с данными игроков
class PlayerData:
    def __init__(self, db):
        self.db = db
        self.players = db.players
        self.items = db.items
        self.settings = db.settings

    async def create_player(self, user_id: int, name: str):
        player_data = {
            "user_id": user_id,
            "name": name,
            "balance": 0,
            "inventory": [],
            "equipment": {
                "weapon": None,
                "armor": None
            },
            "stats": {
                "base_health": 10,
                "current_health": 10,
                "defense": 0,
                "attack": 10
            },
            "effects": []
        }
        await self.players.insert_one(player_data)
        return player_data

    async def get_player(self, user_id: int):
        return await self.players.find_one({"user_id": user_id})

# Инициализация менеджера данных
player_data = PlayerData(db)

@bot.event
async def on_ready():
    logger.info(f'{bot.user} подключен к Discord!')
    try:
        synced = await bot.tree.sync()
        logger.info(f"Синхронизировано {len(synced)} команд")
    except Exception as e:
        logger.error(f"Ошибка при синхронизации команд: {e}")

@bot.tree.command(name="старт", description="Запуск бота после настройки")
async def start(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("У вас нет прав для использования этой команды!", ephemeral=True)
        return
    
    # Проверка настроек сервера
    settings = await player_data.settings.find_one({"guild_id": interaction.guild_id})
    if not settings:
        await interaction.response.send_message("Сначала необходимо настроить бота через команду /настройка!", ephemeral=True)
        return
    
    await interaction.response.send_message("Бот успешно запущен и готов к работе!")

@bot.tree.command(name="регистрация", description="Регистрация нового игрока")
async def register(interaction: discord.Interaction):
    player = await player_data.get_player(interaction.user.id)
    if player:
        await interaction.response.send_message("Вы уже зарегистрированы!", ephemeral=True)
        return
    
    await player_data.create_player(interaction.user.id, interaction.user.name)
    await interaction.response.send_message("Регистрация успешно завершена!", ephemeral=True)

@bot.tree.command(name="профиль", description="Просмотр профиля игрока")
async def profile(interaction: discord.Interaction):
    player = await player_data.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("Вы не зарегистрированы! Используйте /регистрация", ephemeral=True)
        return
    
    embed = discord.Embed(title=f"Профиль игрока {player['name']}", color=discord.Color.blue())
    embed.add_field(name="Баланс", value=f"{player['balance']} монет", inline=True)
    embed.add_field(name="Здоровье", value=f"{player['stats']['current_health']}/{player['stats']['base_health'] + player['equipment']['armor']['bonus_health'] if player['equipment']['armor'] else player['stats']['base_health']}", inline=True)
    embed.add_field(name="Атака", value=f"{player['stats']['attack']}", inline=True)
    embed.add_field(name="Защита", value=f"{player['stats']['defense']}%", inline=True)
    
    # Отображение активных эффектов
    if player.get("effects"):
        effects_text = "\n".join([f"• {effect['name']} ({effect['duration']} ходов)" for effect in player["effects"]])
        embed.add_field(name="Активные эффекты", value=effects_text, inline=False)
    
    await interaction.response.send_message(embed=embed)

# Команды инвентаря
@bot.tree.command(name="инвентарь", description="Просмотр инвентаря")
async def inventory(interaction: discord.Interaction):
    player = await inventory_manager.get_inventory(interaction.user.id)
    if not player:
        await interaction.response.send_message("Вы не зарегистрированы! Используйте /регистрация", ephemeral=True)
        return
    
    embed = create_inventory_embed(player["inventory"], player["equipment"])
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="экипировать", description="Экипировка предмета")
async def equip(interaction: discord.Interaction, item_id: str):
    success, message = await inventory_manager.equip_item(interaction.user.id, item_id)
    await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="снять", description="Снятие предмета")
async def unequip(interaction: discord.Interaction, item_type: str):
    success, message = await inventory_manager.unequip_item(interaction.user.id, item_type)
    await interaction.response.send_message(message, ephemeral=True)

# Боевые команды
@bot.tree.command(name="атака", description="Атака цели")
async def attack(interaction: discord.Interaction, target: discord.Member):
    damage, message = await combat_system.calculate_damage(interaction.user.id, target.id)
    if damage > 0:
        await combat_system.apply_damage(target.id, damage)
        
        attacker = await db.players.find_one({"user_id": interaction.user.id})
        target_player = await db.players.find_one({"user_id": target.id})
        
        embed = create_combat_embed(attacker, target_player, damage, message)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="защита", description="Активация защиты")
async def defense(interaction: discord.Interaction):
    success, message = await combat_system.use_defense(interaction.user.id)
    await interaction.response.send_message(message, ephemeral=True)

# Экономические команды
@bot.tree.command(name="баланс", description="Просмотр баланса")
async def balance(interaction: discord.Interaction):
    player = await db.players.find_one({"user_id": interaction.user.id})
    if not player:
        await interaction.response.send_message("Вы не зарегистрированы! Используйте /регистрация", ephemeral=True)
        return
    
    currency_name = await economy_system.get_currency_name(interaction.guild_id)
    embed = create_balance_embed(player, currency_name)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="перевод", description="Перевод денег другому игроку")
async def transfer(interaction: discord.Interaction, target: discord.Member, amount: int):
    success, message = await economy_system.transfer_money(interaction.user.id, target.id, amount)
    if success:
        from_player = await db.players.find_one({"user_id": interaction.user.id})
        to_player = await db.players.find_one({"user_id": target.id})
        currency_name = await economy_system.get_currency_name(interaction.guild_id)
        
        embed = create_transaction_embed(from_player, to_player, amount, currency_name)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(message, ephemeral=True)

# Административные команды
@bot.tree.command(name="настройка", description="Настройка бота")
async def setup(interaction: discord.Interaction):
    # Проверка прав (админ или техник)
    if not (interaction.user.guild_permissions.administrator or 
            await admin_system.check_permission(interaction.guild_id, "technician", "manage_settings")):
        await interaction.response.send_message("У вас нет прав для использования этой команды!", ephemeral=True)
        return
    
    # Создание модального окна для настроек
    class SettingsModal(discord.ui.Modal, title="Настройки бота"):
        currency_name = discord.ui.TextInput(
            label="Название валюты",
            placeholder="монет",
            required=True
        )
        max_slots = discord.ui.TextInput(
            label="Макс. слотов инвентаря",
            placeholder="20",
            required=True
        )
        defense_duration = discord.ui.TextInput(
            label="Длительность защиты (ходы)",
            placeholder="3",
            required=True
        )
        max_equipped = discord.ui.TextInput(
            label="Макс. экипируемых предметов",
            placeholder="5",
            required=True
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            settings = {
                "guild_id": interaction.guild_id,
                "currency_name": self.currency_name.value,
                "max_inventory_slots": int(self.max_slots.value),
                "defense_duration": int(self.defense_duration.value),
                "max_equipped_items": int(self.max_equipped.value)
            }
            
            success = await admin_system.setup_server(interaction.guild_id, settings)
            if success:
                embed = create_settings_embed(settings)
                await interaction.response.send_message("Настройки сохранены!", embed=embed)
            else:
                await interaction.response.send_message("Ошибка при сохранении настроек!", ephemeral=True)
    
    await interaction.response.send_modal(SettingsModal())

@bot.tree.command(name="сброс", description="Сброс всех данных")
async def reset(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("У вас нет прав для использования этой команды!", ephemeral=True)
        return
    
    success = await admin_system.reset_server(interaction.guild_id)
    if success:
        await interaction.response.send_message("Все данные успешно сброшены!")
    else:
        await interaction.response.send_message("Ошибка при сбросе данных!", ephemeral=True)

@bot.tree.command(name="выдать", description="Выдача предметов игроку")
async def give_item(interaction: discord.Interaction, target: discord.Member, item_name: str, quantity: int = 1):
    # Проверка прав (админ, техник или ведущий)
    if not (interaction.user.guild_permissions.administrator or 
            await admin_system.check_permission(interaction.guild_id, "technician", "manage_items") or
            await admin_system.check_permission(interaction.guild_id, "leader", "manage_items")):
        await interaction.response.send_message("У вас нет прав для использования этой команды!", ephemeral=True)
        return
    
    item = await db.items.find_one({"name": item_name, "guild_id": interaction.guild_id})
    if not item:
        await interaction.response.send_message("Предмет не найден!", ephemeral=True)
        return
    
    success, message = await inventory_manager.add_item(target.id, item)
    await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="выдать_деньги", description="Выдача денег игроку")
async def give_money(interaction: discord.Interaction, target: discord.Member, amount: int):
    # Проверка прав (админ, техник или ведущий)
    if not (interaction.user.guild_permissions.administrator or 
            await admin_system.check_permission(interaction.guild_id, "technician", "manage_economy") or
            await admin_system.check_permission(interaction.guild_id, "leader", "manage_economy")):
        await interaction.response.send_message("У вас нет прав для использования этой команды!", ephemeral=True)
        return
    
    success, message = await economy_system.add_money(target.id, amount)
    await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="статы", description="Просмотр характеристик персонажа")
async def stats(interaction: discord.Interaction):
    player = await player_data.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("Вы не зарегистрированы! Используйте /регистрация", ephemeral=True)
        return
    
    # Расчет общего здоровья с учетом брони
    armor = player.get("equipment", {}).get("armor", {})
    bonus_health = armor.get("bonus_health", 0) if armor else 0
    total_health = player["stats"]["base_health"] + bonus_health
    
    embed = discord.Embed(title=f"Характеристики {player['name']}", color=discord.Color.blue())
    embed.add_field(name="Здоровье", value=f"{player['stats']['current_health']}/{total_health}", inline=True)
    embed.add_field(name="Атака", value=f"{player['stats']['attack']}", inline=True)
    embed.add_field(name="Защита", value=f"{player['stats']['defense']}%", inline=True)
    
    # Отображение активных эффектов
    if player.get("effects"):
        effects_text = "\n".join([f"• {effect['name']} ({effect['duration']} ходов)" for effect in player["effects"]])
        embed.add_field(name="Активные эффекты", value=effects_text, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="использовать", description="Использование предмета")
async def use_item(interaction: discord.Interaction, item_name: str):
    player = await player_data.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("Вы не зарегистрированы! Используйте /регистрация", ephemeral=True)
        return
    
    # Поиск предмета в инвентаре
    item = next((i for i in player["inventory"] if i["name"].lower() == item_name.lower()), None)
    if not item:
        await interaction.response.send_message("Предмет не найден в инвентаре!", ephemeral=True)
        return
    
    if item["type"] != "consumable":
        await interaction.response.send_message("Этот предмет нельзя использовать!", ephemeral=True)
        return
    
    # Применение эффекта
    effect = item.get("effect")
    value = item.get("value", 0)
    
    if effect == "heal":
        max_health = player["stats"]["base_health"]
        if player["equipment"].get("armor"):
            max_health += player["equipment"]["armor"].get("bonus_health", 0)
        
        new_health = min(player["stats"]["current_health"] + value, max_health)
        await player_data.players.update_one(
            {"user_id": interaction.user.id},
            {"$set": {"stats.current_health": new_health}}
        )
        await interaction.response.send_message(f"Восстановлено {new_health - player['stats']['current_health']} HP!")
    
    # Удаление использованного предмета
    await player_data.players.update_one(
        {"user_id": interaction.user.id},
        {"$pull": {"inventory": {"name": item["name"]}}}
    )

def create_settings_embed(settings: Dict) -> discord.Embed:
    """Создание embed-сообщения с настройками"""
    embed = discord.Embed(
        title="Настройки сервера",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Валюта",
        value=settings.get("currency_name", "монет"),
        inline=True
    )
    
    embed.add_field(
        name="Макс. слотов инвентаря",
        value=str(settings.get("max_inventory_slots", 20)),
        inline=True
    )
    
    embed.add_field(
        name="Длительность защиты",
        value=f"{settings.get('defense_duration', 3)} ходов",
        inline=True
    )
    
    embed.add_field(
        name="Макс. экипируемых предметов",
        value=str(settings.get("max_equipped_items", 5)),
        inline=True
    )
    
    return embed

# Запуск бота
if __name__ == "__main__":
    bot.run(TOKEN) 