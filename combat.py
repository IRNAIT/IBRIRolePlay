import random
from typing import Dict, Tuple
import discord

class CombatSystem:
    def __init__(self, db):
        self.db = db
        self.players = db.players

    async def calculate_damage(self, attacker_id: int, target_id: int) -> Tuple[int, str]:
        """Расчет урона при атаке"""
        attacker = await self.players.find_one({"user_id": attacker_id})
        target = await self.players.find_one({"user_id": target_id})
        
        if not attacker or not target:
            return 0, "Игрок не найден"

        # Получение экипированного оружия
        weapon = attacker.get("equipment", {}).get("weapon")
        if not weapon:
            return 0, "У вас нет экипированного оружия"

        # Базовый урон с разбросом
        base_damage = weapon.get("damage", 0)
        damage_range = weapon.get("damage_range", [base_damage, base_damage])
        base_damage = random.randint(damage_range[0], damage_range[1])
        
        # Модификаторы атаки
        attack_mod = attacker.get("stats", {}).get("attack", 0)
        
        # Расчет защиты цели
        target_defense = target.get("stats", {}).get("defense", 0)
        target_armor = target.get("equipment", {}).get("armor", {})
        armor_defense = target_armor.get("defense", 0) if target_armor else 0
        
        total_defense = min(90, target_defense + armor_defense)  # Максимум 90% защиты
        
        # Шанс критического удара
        crit_chance = weapon.get("crit_chance", 5)
        crit_multiplier = weapon.get("crit_multiplier", 1.5)
        
        # Расчет финального урона
        is_crit = random.randint(1, 100) <= crit_chance
        damage_multiplier = crit_multiplier if is_crit else 1.0
        
        # Рандомизация урона (±10%)
        random_factor = random.uniform(0.9, 1.1)
        
        final_damage = int((base_damage + attack_mod) * damage_multiplier * random_factor)
        # Применение защиты в процентах
        final_damage = int(final_damage * (1 - total_defense / 100))
        final_damage = max(1, final_damage)  # Минимальный урон - 1
        
        # Формирование сообщения о результате
        message = f"Атака нанесла {final_damage} урона"
        if is_crit:
            message += " (КРИТ!)"
            
        return final_damage, message

    async def apply_damage(self, target_id: int, damage: int) -> bool:
        """Применение урона к цели"""
        result = await self.players.update_one(
            {"user_id": target_id},
            {"$inc": {"stats.current_health": -damage}}
        )
        return result.modified_count > 0

    async def use_defense(self, user_id: int) -> Tuple[bool, str]:
        """Использование защиты"""
        player = await self.players.find_one({"user_id": user_id})
        if not player:
            return False, "Игрок не найден"

        # Получение настроек сервера
        settings = await self.db.settings.find_one({"guild_id": player.get("guild_id")})
        defense_duration = settings.get("defense_duration", 3)  # По умолчанию 3 хода
        
        # Увеличение защиты
        defense_boost = 50  # +50% к защите
        
        # Добавление эффекта защиты
        effect = {
            "name": "Защита",
            "type": "defense",
            "value": defense_boost,
            "duration": defense_duration
        }
        
        await self.players.update_one(
            {"user_id": user_id},
            {
                "$push": {"effects": effect}
            }
        )
        
        return True, f"Защита активирована на {defense_duration} ходов (+{defense_boost}% к защите)"

def create_combat_embed(attacker: Dict, target: Dict, damage: int, message: str) -> discord.Embed:
    """Создание embed-сообщения для отображения результата боя"""
    embed = discord.Embed(title="Боевой отчет", color=discord.Color.red())
    
    # Расчет максимального здоровья с учетом брони
    attacker_max_hp = attacker["stats"]["base_health"]
    if attacker["equipment"].get("armor"):
        attacker_max_hp += attacker["equipment"]["armor"].get("bonus_health", 0)
    
    target_max_hp = target["stats"]["base_health"]
    if target["equipment"].get("armor"):
        target_max_hp += target["equipment"]["armor"].get("bonus_health", 0)
    
    embed.add_field(
        name="Атакующий",
        value=f"{attacker['name']}\nЗдоровье: {attacker['stats']['current_health']}/{attacker_max_hp}",
        inline=True
    )
    
    embed.add_field(
        name="Цель",
        value=f"{target['name']}\nЗдоровье: {target['stats']['current_health']}/{target_max_hp}",
        inline=True
    )
    
    embed.add_field(
        name="Результат",
        value=message,
        inline=False
    )
    
    return embed 