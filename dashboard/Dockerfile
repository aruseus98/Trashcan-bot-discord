# Utilisation de l'image Python 3.9
FROM python:3.9-slim

# Installe tzdata pour configurer le fuseau horaire
RUN apt-get update && apt-get install -y tzdata && apt-get clean && rm -rf /var/lib/apt/lists/*

# Configure le fuseau horaire à Europe/Paris
ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier le fichier requirements.txt et installer les dépendances
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code source dans le répertoire de travail du conteneur
COPY . .

# Exposer le port 5000 pour Flask
EXPOSE 5000

# Lancer le serveur Flask
CMD ["python", "dashboard.py"]
