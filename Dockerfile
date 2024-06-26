FROM python:3.10-slim

WORKDIR /app

# Copier les fichiers du projet et les fichiers de dépendances dans le répertoire de travail
COPY . .

# Création dossier conf pour persistance données
RUN mkdir -p /app/conf

# Installer les dépendances à partir de requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Commande pour exécuter l'application
CMD ["python", "bot.py"]
