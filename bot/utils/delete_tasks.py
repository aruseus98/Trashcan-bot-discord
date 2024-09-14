import asyncio
import discord
import logging
import os
from datetime import datetime, timedelta
import pytz
from utils.file_storage import save_tasks, load_tasks
import uuid

logger = logging.getLogger()

# Définir la liste des suppressions actives globalement
active_deletions = []

# Définir le chemin vers le fichier JSON (comme dans bot.py)
TASKS_FILE = os.path.join('conf', 'deletion_tasks.json')

async def bulk_delete_messages(channel):
    """Supprime en bloc les messages de moins de 14 jours."""
    while True:
        messages = [msg async for msg in channel.history(limit=100)]
        if len(messages) == 0:
            break
        now = datetime.now(pytz.UTC)
        messages_to_delete = [msg for msg in messages if (now - msg.created_at).days < 14]
        if len(messages_to_delete) == 0:
            break
        await channel.delete_messages(messages_to_delete)
        logger.info(f"Bulk deleted {len(messages_to_delete)} messages. Sleeping for 5 seconds.")
        await asyncio.sleep(5)

async def delete_old_messages(channel):
    """Supprime individuellement les messages plus anciens que 14 jours."""
    while True:
        messages = [msg async for msg in channel.history(limit=100)]
        if len(messages) == 0:
            break
        now = datetime.now(pytz.UTC)
        messages_to_delete = [msg for msg in messages if (now - msg.created_at).days >= 14]
        if len(messages_to_delete) == 0:
            break
        for msg in messages_to_delete:
            await msg.delete()
            logger.info(f"Individually deleted message {msg.id}. Sleeping for 2 seconds.")
            await asyncio.sleep(2)

async def schedule_weekly_deletion(channel, start_time, day_of_week, timezone):
    """Programme la suppression hebdomadaire."""
    day_of_week_index = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(day_of_week)
    
    while True:
        now = datetime.now(timezone)
        today_index = now.weekday()
        days_until_deletion = (day_of_week_index - today_index) % 7
        if days_until_deletion == 0 and now.time() >= start_time.time():
            days_until_deletion = 7
        next_deletion_datetime = (now + timedelta(days=days_until_deletion)).replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
        
        seconds_until_next_deletion = (next_deletion_datetime - now).total_seconds()
        logger.info(f"Next deletion datetime for {channel.name}: {next_deletion_datetime}")
        
        await asyncio.sleep(seconds_until_next_deletion)
        await delete_messages_in_batches(channel, batch_size=100)
        logger.info(f"Weekly deletion performed for {channel.name}. Waiting for next week.")
        await asyncio.sleep(7 * 24 * 3600)

async def delete_messages_in_batches(channel, batch_size=100):
    """Supprime les messages en lots avec gestion des limites API Discord."""
    logger.info(f"Starting batch deletion for channel {channel.name}.")
    while True:
        try:
            await bulk_delete_messages(channel)
            await delete_old_messages(channel)
            break
        except discord.HTTPException as e:
            if e.status == 429:
                retry_after = e.retry_after / 1000
                logger.warning(f"Rate limited. Sleeping for {retry_after} seconds.")
                await asyncio.sleep(retry_after)
            else:
                logger.error(f"HTTPException: {e}. Retrying in 5 seconds.")
                await asyncio.sleep(5)
    logger.info(f"Completed batch deletion for channel {channel.name}.")

async def check_and_schedule_deletions(bot):
    """Vérifie périodiquement le fichier JSON pour les tâches actives et planifie les suppressions."""
    while True:
        tasks = load_tasks()
        for task in tasks:
            # Vérifier si la tâche est active
            if task['status'] == 'active':
                channel = discord.utils.get(bot.get_all_channels(), id=int(task['channel_id']))
                if channel:
                    try:
                        start_time = datetime.strptime(task['start_time'], "%H:%M")
                        timezone = pytz.timezone(task['timezone'])
                        if task['day_of_week'] == 'Daily':
                            await schedule_daily_deletion(channel, start_time, timezone)
                        else:
                            await schedule_weekly_deletion(channel, start_time, task['day_of_week'], timezone)
                    except Exception as e:
                        logger.error(f"Erreur lors de la planification de la suppression pour {channel.name}: {e}")
                else:
                    logger.warning(f"Le canal avec l'ID {task['channel_id']} est introuvable.")
            else:
                logger.info(f"Tâche pour le canal {task['channel_name']} est inactive.")

        # Attendre un certain temps avant de vérifier à nouveau
        await asyncio.sleep(60 * 5)  # Vérifie toutes les 5 minutes

async def schedule_daily_deletion(channel, start_time, timezone):
    """Programme la suppression quotidienne."""
    while True:
        now = datetime.now(timezone)
        next_deletion_datetime = now.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
        if now > next_deletion_datetime:
            next_deletion_datetime += timedelta(days=1)
        
        seconds_until_next_deletion = (next_deletion_datetime - now).total_seconds()
        logger.info(f"Next daily deletion for {channel.name} at {next_deletion_datetime}")
        
        await asyncio.sleep(seconds_until_next_deletion)
        await delete_messages_in_batches(channel, batch_size=100)
        logger.info(f"Daily deletion performed for {channel.name}.")
        await asyncio.sleep(24 * 3600)

def reload_tasks(bot):
    """Recharge les tâches programmées à partir du fichier JSON."""
    # Cette fonction est maintenant déclenchée au démarrage pour initialiser la vérification
    asyncio.create_task(check_and_schedule_deletions(bot))
    logger.info(f"Reloaded and scheduled tasks from {TASKS_FILE}")

