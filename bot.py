import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
from views.selects import TimezoneSelect, AutomatedeleteView, DailyDeleteView, DeleteButton
from utils.delete_tasks import bulk_delete_messages, delete_old_messages, start_deletion_task, schedule_weekly_deletion, delete_messages_in_batches, active_deletions
# Configurez le logging pour afficher les messages dans la console
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger()

# Désactivez le logging de discord pour obtenir des journaux plus propres
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.WARNING)

# Charger les variables d'environnement depuis .env
load_dotenv()

# Utiliser le token depuis les variables d'environnement
token = os.getenv("DISCORD_TOKEN")

# Définir les intents nécessaires pour le bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Initialiser le bot avec les intents spécifiés
bot = commands.Bot(command_prefix='!', intents=intents)

class ConfirmDeleteView(discord.ui.View):
    def __init__(self, channel):
        super().__init__()
        self.channel = channel
        self.confirmed = False

    @discord.ui.button(label="OUI", style=discord.ButtonStyle.green)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Vous devez être administrateur pour effectuer cette action.", ephemeral=True)
            return
        
        self.confirmed = True
        await interaction.response.defer()
        await self.delete_messages_in_batches(self.channel)
        await interaction.followup.send("Tous les messages ont été supprimés.", ephemeral=True)
        self.stop()

    async def delete_messages_in_batches(self, channel, batch_size=100):
        logger.info("Starting batch deletion")
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

    @discord.ui.button(label="NON", style=discord.ButtonStyle.red)
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Vous devez être administrateur pour effectuer cette action.", ephemeral=True)
            return
        
        await interaction.response.defer()
        await interaction.followup.send("Suppression annulée.", ephemeral=True)
        self.stop()

@bot.command()
async def dailydelete(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Vous devez être administrateur pour exécuter cette commande.")
        return
    view = DailyDeleteView()
    await ctx.send("Sélectionnez le fuseau horaire pour la suppression quotidienne des messages :", view=view, ephemeral=True)

@bot.command()
async def deleteall(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Vous devez être administrateur pour effectuer cette action.", delete_after=10)
        return

    view = ConfirmDeleteView(ctx.channel)
    await ctx.send("Voulez-vous supprimer tous les messages du canal actuel ?", view=view)

@bot.command()
async def automatedelete(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Vous devez être administrateur pour exécuter cette commande.")
        return
    view = AutomatedeleteView()
    await ctx.send("Sélectionnez le fuseau horaire pour la suppression automatique des messages :", view=view, ephemeral=True)

@bot.command()
async def list_deletions(ctx):
    logger.info("Commande !list_deletions appelée.")
    logger.info(f"Contenu de active_deletions: {active_deletions}")

    if not active_deletions:
        await ctx.send("Aucune suppression automatique programmée.", delete_after=10)
        return

    for index, deletion in enumerate(active_deletions):
        logger.info(f"Suppression trouvée: {deletion}")
        if deletion['task'].done():
            status = "Completed or Cancelled"
        else:
            status = "Active"
        view = discord.ui.View()
        view.add_item(DeleteButton(index))
        message = (f"Canal: {deletion['channel_name']}, Heure de début: {deletion['start_time']}, "
                   f"Jour: {deletion['day_of_week']}, Fuseau horaire: {deletion['timezone']}, Status: {status}")
        await ctx.send(message, view=view, delete_after=60)

    logger.info("Commande !list_deletions exécutée avec succès.")

# Lancer le bot avec le token
bot.run(token)
