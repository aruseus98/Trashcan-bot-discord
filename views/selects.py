import discord
from discord.ui import Select, View
from utils.delete_tasks import start_deletion_task

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
        from views.start_time_modal import StartTimeModal  # Importer ici pour éviter l'importation circulaire
        modal = StartTimeModal(self.view)
        await interaction.response.send_modal(modal)

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
            await interaction.response.send_message(f"Erreur: {str(e)}", ephemeral=True)

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
        task_info = active_deletions.pop(self.index)
        task_info['task'].cancel()
        await interaction.response.send_message("Automatisation de suppression annulée.", ephemeral=True)
