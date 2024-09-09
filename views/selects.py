import discord
from discord.ui import Select, View
from utils.delete_tasks import start_deletion_task, start_daily_deletion_task, active_deletions
from utils.file_storage import save_tasks

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
        self.view.timezone = self.values[0]
        from views.start_time_modal import StartTimeModal
        modal = StartTimeModal(self.view)
        await interaction.response.send_modal(modal)
        await interaction.followup.send("Sélectionnez une heure pour la suppression.", ephemeral=True)

class DayOfWeekSelect(Select):
    def __init__(self, custom_view):
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        options = [
            discord.SelectOption(label=day, description=f"Every {day}") for day in days_of_week
        ]
        super().__init__(placeholder="Choose a day of the week", min_values=1, max_values=1, options=options)
        self.custom_view = custom_view

    async def callback(self, interaction: discord.Interaction):
        self.custom_view.day_of_week = self.values[0]
        await interaction.response.send_message(f"Day of week set to {self.values[0]}.", ephemeral=True)
        start_deletion_task(
            interaction.channel,
            self.custom_view.start_time,
            self.custom_view.day_of_week,
            self.custom_view.timezone
        )
        await interaction.followup.send(f"Automated deletion scheduled every {self.values[0]} at {self.custom_view.start_time}.", ephemeral=True)

class AutomatedeleteView(View):
    def __init__(self):
        super().__init__()
        self.timezone = None
        self.start_time = None
        self.frequency = None
        self.add_item(TimezoneSelect())

class DeleteButton(discord.ui.Button):
    def __init__(self, task_id):
        super().__init__(label="Annuler", style=discord.ButtonStyle.red)
        self.task_id = task_id

    async def callback(self, interaction: discord.Interaction):
        # Vérification des permissions d'administrateur
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Vous devez être administrateur pour effectuer cette action.", ephemeral=True)
            return
        
        # Chercher la tâche correspondant à l'ID
        task_info = next((t for t in active_deletions if t['id'] == self.task_id), None)
        if task_info:
            active_deletions.remove(task_info)
            task_info['task'].cancel()  # Annuler la tâche asyncio
            save_tasks(active_deletions)  # Sauvegarder après modification
            await interaction.response.send_message("Automatisation de suppression annulée.", ephemeral=True)
        else:
            await interaction.response.send_message("Tâche introuvable ou déjà supprimée.", ephemeral=True)

class StopButton(discord.ui.Button):
    def __init__(self, task_id):
        super().__init__(label="Stopper", style=discord.ButtonStyle.gray)
        self.task_id = task_id

    async def callback(self, interaction: discord.Interaction):
        # Chercher la tâche correspondant à l'ID
        task_info = next((t for t in active_deletions if t['id'] == self.task_id), None)
        if task_info:
            if task_info['status'] == 'inactive':
                await interaction.response.send_message("Cette tâche est déjà inactive.", ephemeral=True)
            else:
                task_info['status'] = 'inactive'
                save_tasks(active_deletions) 
                await interaction.response.send_message(f"Tâche stoppée avec succès.", ephemeral=True)
        else:
            await interaction.response.send_message("Tâche introuvable.", ephemeral=True)

class ActivateButton(discord.ui.Button):
    def __init__(self, task_id):
        super().__init__(label="Activer", style=discord.ButtonStyle.green)
        self.task_id = task_id

    async def callback(self, interaction: discord.Interaction):
        # Chercher la tâche correspondant à l'ID
        task_info = next((t for t in active_deletions if t['id'] == self.task_id), None)
        if task_info:
            if task_info['status'] == 'active':
                await interaction.response.send_message("Cette tâche est déjà active.", ephemeral=True)
            else:
                task_info['status'] = 'active' 
                save_tasks(active_deletions) 
                await interaction.response.send_message("Tâche réactivée avec succès.", ephemeral=True)
        else:
            await interaction.response.send_message("Tâche introuvable.", ephemeral=True)

class DailyDeleteView(View):
    def __init__(self):
        super().__init__()
        self.timezone = None
        self.start_time = None
        self.add_item(TimezoneSelect())
