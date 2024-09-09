import asyncio
import discord
import logging
from datetime import datetime, timedelta
import pytz
from utils.file_storage import save_tasks, load_tasks
import uuid

logger = logging.getLogger()

# Définir la liste des suppressions actives globalement
active_deletions = []

async def bulk_delete_messages(channel):
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
    day_of_week_index = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(day_of_week)
    while True:
        now = datetime.now(timezone)
        today_index = now.weekday()
        days_until_deletion = (day_of_week_index - today_index) % 7
        if days_until_deletion == 0 and now.time() >= start_time.time():
            days_until_deletion = 7
        next_deletion_datetime = (now + timedelta(days=days_until_deletion)).replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
        
        seconds_until_next_deletion = (next_deletion_datetime - now).total_seconds()
        logger.info(f"Current time: {now}")
        logger.info(f"Next deletion datetime: {next_deletion_datetime}")
        logger.info(f"Seconds until deletion: {seconds_until_next_deletion}")
        logger.info("Starting deletion process.")
        
        await asyncio.sleep(seconds_until_next_deletion)
        await delete_messages_in_batches(channel, batch_size=100)
        logger.info("Deletion performed. Waiting for next week.")
        await asyncio.sleep(7 * 24 * 3600)

async def delete_messages_in_batches(channel, batch_size=100):
    logger.info("Starting batch deletion in scheduled task")
    while True:
        try:
            # Bulk delete recent messages
            await bulk_delete_messages(channel)
            # Individually delete older messages
            await delete_old_messages(channel)
            break
        except discord.HTTPException as e:
            if e.status == 429:
                retry_after = e.retry_after / 1000
                logger.warning(f"Rate limited. Sleeping for {retry_after} seconds.")
                await asyncio.sleep(retry_after)
            else:
                logger.error(f"HTTPException encountered: {e}. Sleeping for 5 seconds before retry.")
                await asyncio.sleep(5)
    logger.info("Completed deletion of messages.")

def start_deletion_task(channel, time_str, day_of_week, timezone_str):
    timezone = pytz.timezone(timezone_str)
    start_time = datetime.strptime(time_str, "%H:%M")
    start_time = timezone.localize(datetime.combine(datetime.today(), start_time.time()))

    task_id = str(uuid.uuid4())

    task_info = {
        'id': task_id,
        'channel_name': channel.name,
        'channel_id': channel.id,
        'start_time': time_str,
        'day_of_week': day_of_week,
        'timezone': timezone_str,
        'status': 'active', 
        'task': None
    }
    task = asyncio.create_task(schedule_weekly_deletion(channel, start_time, day_of_week, timezone))
    task_info['task'] = task
    active_deletions.append(task_info)
    save_tasks(active_deletions) 
    logger.info(f"Tâche de suppression ajoutée: {task_info}")


async def schedule_daily_deletion(channel, start_time, timezone):
    while True:
        task_info = next((t for t in active_deletions if t['channel_id'] == channel.id and t['day_of_week'] == day_of_week), None)
        if task_info and task_info['status'] == 'inactive':
            logger.info(f"Tâche de suppression pour {channel.name} est inactive. Aucune action effectuée.")
            break
            
        now = datetime.now(timezone)
        next_deletion_datetime = now.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
        if now > next_deletion_datetime:
            next_deletion_datetime += timedelta(days=1)
        
        seconds_until_next_deletion = (next_deletion_datetime - now).total_seconds()
        logger.info(f"Current time: {now}")
        logger.info(f"Next deletion datetime: {next_deletion_datetime}")
        logger.info(f"Seconds until deletion: {seconds_until_next_deletion}")
        logger.info("Starting daily deletion process.")
        
        await asyncio.sleep(seconds_until_next_deletion)
        await delete_messages_in_batches(channel, batch_size=100)
        logger.info("Daily deletion performed. Waiting for next day.")
        await asyncio.sleep(24 * 3600)

def start_daily_deletion_task(channel, time_str, timezone_str):
    timezone = pytz.timezone(timezone_str)
    start_time = datetime.strptime(time_str, "%H:%M")
    start_time = timezone.localize(datetime.combine(datetime.today(), start_time.time()))

    task_id = str(uuid.uuid4()) 

    task_info = {
        'id': task_id,
        'channel_name': channel.name,
        'channel_id': channel.id,
        'start_time': time_str,
        'day_of_week': 'Daily',
        'timezone': timezone_str,
        'status': 'active',
        'task': None
    }
    task = asyncio.create_task(schedule_daily_deletion(channel, start_time, timezone))
    task_info['task'] = task
    active_deletions.append(task_info)
    save_tasks(active_deletions)
    logger.info(f"Tâche de suppression quotidienne ajoutée: {task_info}")

def reload_tasks(bot):
    tasks = load_tasks()
    for task in tasks:
        channel = discord.utils.get(bot.get_all_channels(), id=task['channel_id'])
        if channel is not None:
            try:
                if task['day_of_week'] == 'Daily':
                    logger.info(f"Rechargement de la tâche quotidienne pour le canal {channel.name}")
                    start_daily_deletion_task(channel, task['start_time'], task['timezone'])
                else:
                    logger.info(f"Rechargement de la tâche hebdomadaire pour le canal {channel.name}")
                    start_deletion_task(channel, task['start_time'], task['day_of_week'], task['timezone'])
            except Exception as e:
                logger.error(f"Erreur lors du rechargement de la tâche pour le canal {channel.name}: {e}")
        else:
            logger.warning(f"Le canal avec l'ID {task['channel_id']} est introuvable.")

