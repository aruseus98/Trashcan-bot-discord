import os
import discord
import requests
from discord.ext import commands
from dotenv import load_dotenv
import logging
from flask import Flask, jsonify
import asyncio
import json
from utils.delete_tasks import reload_tasks
from utils.file_storage import load_tasks, save_tasks

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
headers = {
    "Authorization": f"Bot {token}"
}

# Définir les intents nécessaires pour le bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True  # Pour récupérer les informations des serveurs

# Initialiser le bot avec les intents spécifiés
bot = commands.Bot(command_prefix='!', intents=intents)

# Flask API pour exposer les données
app = Flask(__name__)

# Chemin vers le fichier JSON où les tâches sont stockées
TASKS_FILE = os.path.join('conf', 'deletion_tasks.json')

# Fonction pour charger les tâches depuis le fichier JSON
def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, 'r') as f:
        return json.load(f)

# Fonction pour recharger les tâches et les exécuter dans le bot
def reload_tasks_from_file():
    tasks = load_tasks()  # Charger les tâches depuis le fichier
    logger.info(f"Tâches rechargées depuis {TASKS_FILE}: {tasks}")
    reload_tasks(bot)  # Fonction qui programme les tâches dans le bot (suppression, etc.)

# Route API pour récupérer les serveurs (guilds)
@app.route('/guilds', methods=['GET'])
def get_guilds():
    guilds_data = []
    for guild in bot.guilds:
        guilds_data.append({
            "id": guild.id,
            "name": guild.name
        })
    return jsonify(guilds_data)

# Route API pour récupérer les canaux d'un serveur spécifique
@app.route('/guilds/<guild_id>/channels', methods=['GET'])
def get_guild_channels(guild_id):
    url = f"https://discord.com/api/v10/guilds/{guild_id}/channels"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        channels = response.json()
        text_channels = [channel for channel in channels if channel['type'] == 0]  # Filtrer uniquement les canaux textuels
        return jsonify(text_channels)  # Renvoi des données au format JSON
    else:
        return jsonify({"error": f"Unable to fetch channels for guild {guild_id}, status code: {response.status_code}"}), response.status_code

# Route API pour récupérer toutes les tâches (lecture seule)
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks = load_tasks()  # Charger les tâches depuis le fichier JSON
    return jsonify(tasks), 200  # Retourner les tâches en réponse

# Fonction pour exécuter Flask avec asyncio
async def run_flask():
    loop = asyncio.get_event_loop()
    server = await loop.run_in_executor(None, app.run, '0.0.0.0', 5000)
    return server

# Lancer le bot et Flask simultanément avec asyncio
async def main():
    # Exécuter Discord et Flask simultanément
    await asyncio.gather(bot.start(token), run_flask())

# Lorsque le bot est prêt, on recharge les tâches depuis le fichier JSON
@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    logger.info('------')
    # Recharger les tâches depuis le fichier JSON
    reload_tasks_from_file()

if __name__ == "__main__":
    asyncio.run(main())
