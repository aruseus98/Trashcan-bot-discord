from flask import Flask, render_template, request, jsonify
import json
import os
import uuid
import requests

app = Flask(__name__)

# Chemin vers le fichier JSON partagé avec le bot
TASKS_FILE = os.path.join('conf', 'deletion_tasks.json')

def load_tasks():
    """Charger les tâches depuis le fichier JSON"""
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, 'r') as f:
        return json.load(f)

def save_tasks(tasks):
    """Sauvegarder les tâches dans le fichier JSON"""
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=4)

# Afficher le dashboard et charger les tâches
@app.route('/')
def index():
    tasks = load_tasks()  # Charger les tâches depuis le fichier JSON
    # Récupérer les informations du bot via l'API pour afficher les serveurs
    try:
        response = requests.get("http://bot:5000/guilds")  # Appel pour récupérer les serveurs où le bot est connecté
        servers = response.json()
    except requests.exceptions.RequestException:
        servers = []  # Si la requête échoue, on affiche une liste vide

    return render_template('index.html', tasks=tasks, servers=servers)

@app.route('/api/guilds/<guild_id>/channels', methods=['GET'])
def get_channels(guild_id):
    try:
        response = requests.get(f"http://bot:5000/guilds/{guild_id}/channels")
        if response.status_code == 200:
            return jsonify(response.json())  # Assurez-vous que vous retournez les données sous forme de JSON
        else:
            return jsonify({"error": f"Unable to fetch channels for guild {guild_id}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Retourner une erreur JSON en cas de problème

# Ajouter une nouvelle tâche (directement dans le fichier JSON)
@app.route('/api/task', methods=['POST'])
def add_task():
    # Récupérer les données du formulaire
    channel_id = request.form.get('channel_name')
    guild_id = request.form.get('discord_server')

    # Faire une requête pour obtenir le nom du canal à partir de l'ID du canal
    response = requests.get(f"http://bot:5000/guilds/{guild_id}/channels")
    
    if response.status_code == 200:
        channels = response.json()
        channel_name = None
        for channel in channels:
            if str(channel["id"]) == channel_id:
                channel_name = channel["name"]
                break
        
        if channel_name is None:
            return jsonify({"error": "Channel not found"}), 404
    else:
        return jsonify({"error": "Unable to fetch channels"}), 500

    # Créer la nouvelle tâche avec le nom du canal correct
    new_task = {
        "id": str(uuid.uuid4()),  # Générer un ID unique pour la tâche
        "channel_name": channel_name,  # Utiliser le nom du canal
        "channel_id": channel_id,
        "start_time": request.form.get('start_time'),
        "day_of_week": request.form.get('day_of_week'),
        "timezone": request.form.get('timezone'),
        "status": request.form.get('status', 'active')  # Par défaut, la tâche est active
    }

    # Charger les tâches existantes, ajouter la nouvelle, et sauvegarder
    tasks = load_tasks()
    tasks.append(new_task)
    save_tasks(tasks)

    return jsonify({"message": "Nouvelle tâche ajoutée", "task": new_task}), 201

# Route pour supprimer une tâche
@app.route('/api/task/<task_id>/delete', methods=['POST'])
def delete_task(task_id):
    tasks = load_tasks()
    tasks = [task for task in tasks if task['id'] != task_id]  # Supprimer la tâche par ID
    save_tasks(tasks)
    return jsonify({"message": f"Tâche {task_id} supprimée"})

# Route pour changer le statut d'une tâche
@app.route('/api/task/<task_id>/status', methods=['POST'])
def update_task_status(task_id):
    status = request.json.get('status')  # Récupérer le nouveau statut
    tasks = load_tasks()
    for task in tasks:
        if task['id'] == task_id:
            task['status'] = status
            break
    save_tasks(tasks)
    return jsonify({"message": f"Tâche {task_id} mise à jour avec succès"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
