import discord
from discord.ui import Modal, TextInput, View
from datetime import datetime
from utils.delete_tasks import start_daily_deletion_task
from views.selects import DailyDeleteView 

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
            if isinstance(self.view, DailyDeleteView):
                start_daily_deletion_task(interaction.channel, self.view.start_time, self.view.timezone)
                await interaction.response.send_message(f"Daily deletion scheduled at {self.view.start_time}.", ephemeral=True)
            else:
                from views.selects import DayOfWeekSelect 
                day_of_week_select = DayOfWeekSelect(self.view)
                view = View()
                view.add_item(day_of_week_select)
                await interaction.response.send_message("Please choose a day of the week for the message deletion.", view=view, ephemeral=True)
        except ValueError:
            await interaction.followup.send("Please use the format HH:MM.", ephemeral=True)
