# Trashcan-bot-discord
Trashcan bot discord V1  
Delete messages in channel  

# Build the image docker
docker build -t discord-bot .  

# Run the container
docker run --name auto-delete discord-bot  

# Commands
Must have admin privileges in the discord server  

!deleteall : delete all messages in the channel where this command is used.  

!automatedelete : set a hour and a day of the week. It will automatically delete all messages in the channel where the command was used. Ex : 11:00 AM, Wednesday. It will delete every wednesday at 11:00 AM  

!list_deletions : show a list of all automatic delete active.  

!dailydelete : schedule task to daily delete messages.  