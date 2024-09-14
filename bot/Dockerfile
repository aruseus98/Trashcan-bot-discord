# Utilisation de l'image Python
FROM python:3.9-slim

# Installe tzdata pour configurer le fuseau horaire
RUN apt-get update && apt-get install -y tzdata && apt-get clean && rm -rf /var/lib/apt/lists/*

# Configure le fuseau horaire à Europe/Paris
ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier les fichiers requirements et les installer
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code source du bot dans le conteneur
COPY . .

# Exposer le port (ceci est inutile pour le bot Discord, mais requis pour certaines configurations Docker)
EXPOSE 5000

# Démarrer le bot Discord
CMD ["python", "bot.py"]
