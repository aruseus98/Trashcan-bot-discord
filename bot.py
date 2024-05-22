import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio  # Importer asyncio pour gérer les tâches asynchrones
from discord.ui import View, Modal, TextInput, Select
import pytz
from datetime import datetime, timedelta  # Importer datetime pour accéder à l'heure et la date

# Charger les variables d'environnement depuis .env
load_dotenv()

# Utiliser le token depuis les variables d'environnement
token = os.getenv("DISCORD_TOKEN")

# Définir les intents nécessaires pour le bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Activer l'intent de contenu des messages

# Initialiser le bot avec les intents spécifiés
bot = commands.Bot(command_prefix='!', intents=intents)
active_deletions = []

class TimezoneSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Europe/London", description="GMT/BST - UK (London)"),
            discord.SelectOption(label="Europe/Paris", description="CET/CEST - Central Europe (Paris)"),
            discord.SelectOption(label="Europe/Moscow", description="MSK - Moscow Standard Time"),
            discord.SelectOption(label="Asia/Tokyo", description="JST - Japan Standard Time"),
            discord.SelectOption(label="Asia/Shanghai", description="CST - China Standard Time"),
            discord.SelectOption(label="Asia/Calcutta", description="IST - Indian Standard Time"),
            discord.SelectOption(label="America/New_York", description="EST/EDT - Eastern Standard Time"),
            discord.SelectOption(label="America/Chicago", description="CST/CDT - Central Standard Time"),
            discord.SelectOption(label="America/Los_Angeles", description="PST/PDT - Pacific Standard Time"),
            discord.SelectOption(label="America/Sao_Paulo", description="BRT/BRST - Brazil Time")
        ]
        super().__init__(placeholder='Choisissez un fuseau horaire', min_values=1, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        # Stocke seulement le nom du fuseau horaire, pas l'objet
        self.view.timezone = self.values[0]  # Stocke le nom du fuseau horaire comme une chaîne
        modal = StartTimeModal(self.view)
        await interaction.response.send_modal(modal)  # Ouvre la modalité et laisse la modalité guider l'utilisateur

class DayOfWeekSelect(Select):
    def __init__(self, custom_view):
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        options = [
            discord.SelectOption(label=day, description=f"Every {day}") for day in days_of_week
        ]
        super().__init__(placeholder="Choose a day of the week", min_values=1, max_values=1, options=options)
        self.custom_view = custom_view  # Utiliser un nouvel attribut pour stocker la vue

    async def callback(self, interaction: discord.Interaction):
        self.custom_view.day_of_week = self.values[0]
        await interaction.response.send_message(f"Day of week set to {self.values[0]}.", ephemeral=True)
        # Appel pour démarrer la tâche de suppression
        start_deletion_task(
            interaction.channel,
            self.custom_view.start_time,
            self.custom_view.day_of_week,
            self.custom_view.timezone
        )
        await interaction.followup.send(f"Automated deletion scheduled every {self.values[0]} at {self.custom_view.start_time}.", ephemeral=True)
        
class FrequencySelect(Select):
    def __init__(self, view):
        super().__init__(placeholder="Choisissez la fréquence de suppression", min_values=1, max_values=1, options=[
            discord.SelectOption(label=f"{i} heure(s)", value=str(i)) for i in range(1, 25)
        ])
        self.my_view = view

    async def callback(self, interaction: discord.Interaction):
        self.my_view.frequency = int(self.values[0])
        try:
            tz = pytz.timezone(self.my_view.timezone)
            start_time_str = self.my_view.start_time
            start_deletion_task(interaction.channel, start_time_str, self.my_view.frequency, self.my_view.timezone)
            await interaction.response.send_message(f"Suppression configurée toutes les {self.values[0]} heures à partir de {self.my_view.start_time}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Erreur: {str(e)}", ephemeral=True)  # Utilise interaction.response ici

class AutomatedeleteView(View):
    def __init__(self):
        super().__init__()
        self.timezone = None
        self.start_time = None
        self.frequency = None
        self.add_item(TimezoneSelect())

class DeleteButton(discord.ui.Button):
    def __init__(self, index):
        super().__init__(label="Annuler", style=discord.ButtonStyle.red)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        task_info = active_deletions.pop(self.index)  # Retirer la tâche de la liste
        task_info['task'].cancel()  # Annuler la tâche asyncio
        await interaction.response.send_message("Automatisation de suppression annulée.", ephemeral=True)

class StartTimeModal(Modal):
    def __init__(self, view):
        super().__init__(title="Define the start time (HH:MM)")
        self.add_item(TextInput(label="Start Time", style=discord.TextStyle.short, placeholder="16:00", min_length=5, max_length=5))
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        time_input = self.children[0].value
        try:
            datetime.strptime(time_input, "%H:%M")
            self.view.start_time = time_input
            day_of_week_select = DayOfWeekSelect(self.view)
            view = View()
            view.add_item(day_of_week_select)
            await interaction.response.send_message("Please choose a day of the week for the message deletion.", view=view, ephemeral=True)
        except ValueError:
            await interaction.followup.send("Please use the format HH:MM.", ephemeral=True)

class ConfirmDeleteView(discord.ui.View):
    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    @discord.ui.button(label="OUI", style=discord.ButtonStyle.green)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Vous devez être administrateur pour effectuer cette action.", ephemeral=True)
            return
        
        await interaction.response.defer()
        await self.delete_messages_in_batches(self.channel)
        await interaction.followup.send("Tous les messages ont été supprimés.", ephemeral=True)
        self.stop()

    async def delete_messages_in_batches(self, channel, batch_size=100):
        while True:
            deleted = await channel.purge(limit=batch_size)
            if len(deleted) < batch_size:
                break

    @discord.ui.button(label="NON", style=discord.ButtonStyle.red)
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Vous devez être administrateur pour effectuer cette action.", ephemeral=True)
            return
        
        await interaction.response.defer()
        await interaction.followup.send("Suppression annulée.", ephemeral=True)
        self.stop()

async def schedule_weekly_deletion(channel, start_time, day_of_week, timezone):
    day_of_week_index = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(day_of_week)
    while True:
        now = datetime.now(timezone)
        today_index = now.weekday()  # Monday is 0 and Sunday is 6
        days_until_deletion = (day_of_week_index - today_index) % 7
        if days_until_deletion == 0 and now.time() >= start_time.time():
            days_until_deletion = 7  # Wait until next week if today is the day but time has passed
        next_deletion_datetime = (now + timedelta(days=days_until_deletion)).replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
        
        seconds_until_next_deletion = (next_deletion_datetime - now).total_seconds()
        print(f"Current time: {now}")
        print(f"Next deletion datetime: {next_deletion_datetime}")
        print(f"Seconds until deletion: {seconds_until_next_deletion}")
        print("Starting deletion process.")
        
        await asyncio.sleep(seconds_until_next_deletion)
        await channel.purge(limit=100)  # Make sure this action does not throw an exception
        print("Deletion performed. Waiting for next week.")
        await asyncio.sleep(7 * 24 * 3600)  # Wait a week before next deletion


def start_deletion_task(channel, time_str, day_of_week, timezone_str):
    timezone = pytz.timezone(timezone_str)
    start_time = datetime.strptime(time_str, "%H:%M")  # Assumant que time_str est "HH:MM"
    start_time = timezone.localize(datetime.combine(datetime.today(), start_time.time()))

    task_info = {
        'channel_name': channel.name,
        'channel_id': channel.id,
        'start_time': time_str,
        'day_of_week': day_of_week,
        'timezone': timezone_str,
        'task': None
    }
    task = asyncio.create_task(schedule_weekly_deletion(channel, start_time, day_of_week, timezone))
    task_info['task'] = task
    active_deletions.append(task_info)

@bot.command()
async def deleteall(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Vous devez être administrateur pour effectuer cette action.", delete_after=10)
        return

    view = ConfirmDeleteView(ctx.channel)
    confirm_message = await ctx.send("Voulez-vous supprimer tous les messages du canal actuel ?", view=view)

    # Attente pour la confirmation avec un gestionnaire de temps
    await asyncio.sleep(60)  # Attendre 1 minute pour la confirmation
    if not view.is_finished():
        # Assurez-vous d'éditer le message après un délai pour éviter les réponses non traitées
        await confirm_message.edit(content="Temps de confirmation expiré, aucune action n'a été prise.", view=None)

@bot.command()
async def automatedelete(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Vous devez être administrateur pour exécuter cette commande.")
        return
    view = AutomatedeleteView()
    await ctx.send("Sélectionnez le fuseau horaire pour la suppression automatique des messages :", view=view, ephemeral=True)

@bot.command()
async def list_deletions(ctx):
    if not active_deletions:
        await ctx.send("Aucune suppression automatique programmée.", ephemeral=True)
        return

    for index, deletion in enumerate(active_deletions):
        if deletion['task'].done():
            status = "Completed or Cancelled"
        else:
            status = "Active"
        view = discord.ui.View()
        view.add_item(DeleteButton(index))
        message = (f"Canal: {deletion['channel_name']}, Heure de début: {deletion['start_time']}, "
                   f"Jour: {deletion['day_of_week']}, Fuseau horaire: {deletion['timezone']}, Status: {status}")
        await ctx.send(message, view=view, ephemeral=True)

# Lancer le bot avec le token
bot.run(token)
