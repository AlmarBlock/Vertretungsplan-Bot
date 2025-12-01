import os
import discord
import asyncio
import json
import ast
import re
import requests
import aiohttp
import time
from discord import Webhook
from discord.ui import Button, View
from get_content import _day

DATE_TIME_FORMAT = "%d.%m.%Y %H:%M:%S"

#SECTION  ---- Logging Function ---- #
def log(message):
    print(time.strftime(DATE_TIME_FORMAT), message)
async def _log(message):
    print(time.strftime(DATE_TIME_FORMAT), message)
#!SECTION  ---- Logging Function ---- #


#SECTION  ---- Configuration ---- #
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config/config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r', encoding='utf-8') as CONFIG:
        CONFIG_FILE = json.load(CONFIG)
    log("Configuration file loaded successfully.")
else:
    CONFIG_FILE = {}
    log("Configuration file not found. Using default configuration.")

COLOR_DICT = CONFIG_FILE.get("COLOR_DICT", {})
CLASSES = CONFIG_FILE.get("CLASSES", [])
BOT_TOKEN = CONFIG_FILE.get("BOT_TOKEN", os.getenv("BOT_TOKEN", ""))

LONG_DELETE_TIME = CONFIG_FILE.get("LONG_DELETE_TIME", 43200)
MEDIUM_DELETE_TIME = CONFIG_FILE.get("MEDIUM_DELETE_TIME", 60)
SHORT_DELETE_TIME = CONFIG_FILE.get("SHORT_DELETE_TIME", 20)
PURGE_LIMIT = CONFIG_FILE.get("PURGE_LIMIT", 10)

DEFULT_CLAS = CONFIG_FILE.get("DEFULT_CLAS", "11n")
DAY_NAMES = CONFIG_FILE.get("DAY_NAMES", ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"])
DATE_FORMAT = CONFIG_FILE.get("DATE_FORMAT", "%d.%m.%Y")
TIME_FORMAT = CONFIG_FILE.get("TIME_FORMAT", "%H:%M")
DATE_TIME_FORMAT = CONFIG_FILE.get("DATE_TIME_FORMAT", "%d.%m.%Y %H:%M:%S")

LOGO_URL = CONFIG_FILE.get("LOGO_URL", "")
COMMAND_OUTPUT_LOG_URL = CONFIG_FILE.get("COMMAND_OUTPUT_LOG_URL", "")
JOIN_WEBHOOK_URL = CONFIG_FILE.get("JOIN_WEBHOOK_URL", "")
COMMAND_USE_LOG_URL = CONFIG_FILE.get("COMMAND_USE_LOG_URL", "")

RESULT_FILE_PATH = CONFIG_FILE.get("RESULT_FILE_PATH", "./results.txt")

SETTINGS_CHANNEL_ID = CONFIG_FILE.get("SETTINGS_CHANNEL_ID")
START_MESSAGE_CHANNEL_ID = CONFIG_FILE.get("START_MESSAGE_CHANNEL_ID")
JOINS_CHANNEL_ID = CONFIG_FILE.get("JOINS_CHANNEL_ID")
VERTRETUNGS_CHANNEL_ID = CONFIG_FILE.get("VERTRETUNGS_CHANNEL_ID")

ROLE_ID_MORGENS = CONFIG_FILE.get("ROLE_ID_MORGENS")
ROLE_ID_ABENDS = CONFIG_FILE.get("ROLE_ID_ABENDS")
ROLE_ID_UPDATES = CONFIG_FILE.get("ROLE_ID_UPDATES")
ROLE_ID_STUDENT = CONFIG_FILE.get("ROLE_ID_STUDENT")

log("Configuration updated successfully.")
#!SECTION  ---- Configuration ---- #


#SECTION  ---- Variables ---- #
texts = {}
clas_texts = [""] * len(CLASSES)
#!SECTION  ---- Variables ---- #


#SECTION  ---- Gloabl Functions ---- #
async def _get_avatar_pic_url(message):
    try:
        source_url = 'https://discordlookup.mesalytic.moe/v1/user/'+str(message.author.id)
        response = requests.get(source_url)
        response_json = response.json()
        avatar_url = response_json['avatar']['link']
    except discord.NotFound:
        print(f"User with ID {message.author.id} not found.")
        avatar_url = LOGO_URL
    return avatar_url

async def _clear_class_channel():
    for clas in CLASSES:
        channel = client.get_channel(clas[1])
        await channel.purge(limit=PURGE_LIMIT)

async def _reload_texts():
    global texts
    TEXTS_PATH = os.path.join(os.path.dirname(__file__), "config/texte.json")
    with open(TEXTS_PATH, 'r', encoding='utf-8') as file:
        texts = json.load(file)

async def _get_class_id_by_name(clas_name):
    for clas in CLASSES:
        if clas[0][0].lower() + clas[0][1].lower() == clas_name.lower():
            return CLASSES.index(clas)
    return None

async def _log_commands(message, current_date_time, clas): # Logs all lookup responses to a webhook
    if clas == "header":
        clas = "Header"
        color = discord.Color.from_rgb(0, 0, 0)
    else:
        try:
            color = discord.Color.from_rgb(COLOR_DICT[clas][0], COLOR_DICT[clas][1], COLOR_DICT[clas][2])
        except KeyError:
            color = discord.Color.from_rgb(0, 0, 0)

    # Send each part of the message as a separate embed to get around Discord's embed character limit
    for i in range(len(message)):  
        title = f"{current_date_time} | {clas}"
        if i > 0:
            title = ""

        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(COMMAND_OUTPUT_LOG_URL, session=session)
            embed = discord.Embed(title=title, description=message[i], color=color)
            await webhook.send(embed=embed, username="Vertretungsplan", avatar_url=LOGO_URL)

async def _convert_to_2d_array(update_result):
    try:
        array_2d = ast.literal_eval(update_result)
        if isinstance(array_2d, list) and all(isinstance(row, list) for row in array_2d):
            return array_2d
        else:
            raise ValueError(texts.get("Error_No_2D_Array",""))
    except (ValueError, SyntaxError) as e:
        log(texts.get("Error_Converting_String","").format(error=e))
        return None

async def _check_for_valid_input(tokens):  
    if not tokens[1].lower() == "h":
        #Check if class exists if not header
        if await _get_class_id_by_name(tokens[1]) == None:
            return "CLASS"
        
    if not tokens[0].lower() == "all":
        # Check if day is valid integer if not all
        try:
            day_int = int(tokens[0])
        except (ValueError, IndexError):
            day_int = -1  # Fallback value for invalid input
        if day_int > 5 or day_int < 1:
                return "DAY"
    return True

async def _convert_short_to_long(tokens):
    for i in range(len(tokens)): #Converts shorthand to full words
        if tokens[i] == "h":
            tokens[i] = "header"
        if tokens[i] == "all":
            tokens[i] = 0
    return tokens
#!SECTION  ---- Gloabl Functions ---- #


#SECTION  ---- Functions ---- #

#SECTION ---- Send Schedule Changes ---- #
async def _send_respond_message(day = 1, clas = DEFULT_CLAS, original_message = None, delete_time = SHORT_DELETE_TIME):
    if original_message is None:
        await _log(texts.get("Error_No_Message_Provided",""))
        return
    

    #SECTION -- Local Variables -- #
    channel = client.get_channel(original_message.channel.id)
    current_date_time = time.strftime(DATE_TIME_FORMAT)
    split_message_content = []
    #!SECTION -- Local Variables -- #


    #Check if input is valid
    tokens = [day, clas]
    validity = await _check_for_valid_input(tokens) 
    if validity == "DAY":
        #Send message that day is invalid
        await channel.send(texts.get("Error_Entered_Day_Not_Found", "").format(tokens=tokens[0]), delete_after=SHORT_DELETE_TIME)
        return
    if validity == "CLASS":
        #Send message that class is invalid
        await channel.send(texts.get("Error_Entered_Class_Not_Found", "").format(tokens=tokens[1]), delete_after=SHORT_DELETE_TIME)
        return
    if validity == True:
        #Looks up the schedule for the given day and class
        tokens = await _convert_short_to_long(tokens)
        day = tokens[0]
        clas = tokens[1]
    await _log(texts.get("Change_Lookup_Log", "").format(clas=clas, day=day))

    if clas == "header":
        delete_time = MEDIUM_DELETE_TIME

    if day == 0:
        delete_time = MEDIUM_DELETE_TIME
        if clas == "header":
            message_content = _day(1, clas) + "\n" + _day(2, clas) + "\n" + _day(3, clas) + "\n" + _day(4, clas) + "\n" + _day(5, clas)
        else:
            message_content = _day(1, clas) + "\n" + _day(2, clas) + "\n" + _day(3, clas) + "\n" + _day(4, clas) + "\n" + _day(5, clas)
    else:
        message_content = _day(day, clas)

    for i in range(0, len(message_content), 2000):
        split_message_content.append(message_content[i:i+2000])
    for i in range(len(split_message_content)):  
        await channel.send(content=split_message_content[i], delete_after=delete_time)

    await _log_commands(split_message_content, current_date_time, clas)

#!SECTION ---- Send Schedule Changes ---- #


#SECTION ---- Daily Update Message ---- #
async def _send_daily_update_message(dry_run=False):
    global clas_texts
    with open(RESULT_FILE_PATH, 'r', encoding='utf-8') as file:
        update_result = file.read()
    update_result_array = await _convert_to_2d_array(update_result)

    for i in range(len(update_result_array)-1):  
        for k in range(len(update_result_array[i])):
            if update_result_array[i][k] == "":
                update_result_array[i][k] = "---"
    log(texts.get("Fixed_Empty_Fields", "").format(update_result_array=update_result_array))
    
    for i in range(len(update_result_array)-1): 
        for clas in CLASSES:
            class_name = clas[0][0] + clas[0][1]
            text_variable = ""
            if re.match(fr"{clas[0][0]}.*?{clas[0][1]}", update_result_array[i][0]):
                if text_variable == "":
                    text_variable = "Klasse | Std. | Lehrer | Fach | statt | Raum | Art | Bemerkung"
                text_variable += "\n" + update_result_array[i][0] + " | " + update_result_array[i][1] + " | " + update_result_array[i][2] + " | " + update_result_array[i][3] + " | " + update_result_array[i][4] + " | " + update_result_array[i][5] + " | " + update_result_array[i][6] + " | " + update_result_array[i][7]
                clas_texts[await _get_class_id_by_name(class_name)] = text_variable
    for clas in CLASSES:  
        class_name = clas[0][0] + clas[0][1]
        channel = client.get_channel(clas[1])
        text_variable = clas_texts[await _get_class_id_by_name(class_name)]
        if not text_variable == "":
            await _log(text_variable)
            if dry_run or update_result_array[len(update_result_array)-1][0] is None:
                ping_text = ""
            elif update_result_array[len(update_result_array)-1][0] == True:
                ping_text = "\n|| <@&1287841332857147428> ||"
            elif update_result_array[len(update_result_array)-1][0] == False:
                ping_text = "\n|| <@&1287841414268325988> ||"
            await channel.send(content=text_variable + ping_text, delete_after=LONG_DELETE_TIME)
    clas_texts = [""] * len(CLASSES)
#!SECTION ---- Daily Update Message ---- #

#!SECTION  ---- Functions ---- #


#SECTION ---- Discord Bot ---- #
class MyClient(discord.Client):

    #SECTION ---- On Ready ----- #
    async def on_ready(self):
        global texts
        text = str(discord.version_info)
        pattern = r"major=(\d+), minor=(\d+), micro=(\d+)"
        matches = re.search(pattern, text)  
        if matches:
            major = matches.group(1)
            minor = matches.group(2)
            micro = matches.group(3)    
            version_string = "{}.{}.{}".format(major, minor, micro)
            await _log(f"Version: {version_string}")

        await client.change_presence(status=discord.Status.idle, activity=discord.CustomActivity(name="Vertretungsplan anzeigen"))
        await _log("Activity! ✅")
        await self.send_button()
        await _log("Buttons reloaded ✅")
        try:
            await tree.sync()
            await _log("Slash commands synced ✅")
        except Exception as e:
            await _log(f"Failed to sync slash commands: {e}")
        await _clear_class_channel()
        await _log("Class Chats Cleared ✅")
        await client.change_presence(status=discord.Status.online, activity=discord.CustomActivity(name="Vertretungsplan anzeigen"))
        await _log("Done! ✅")
    #!SECTION ---- On Ready ----- #


    #SECTION ---- On Disconnect ----- #
    async def on_disconnect(self):
        await _log(texts.get('Bot_Disconnect',''))
    #!SECTION ---- On Disconnect ----- #


    #SECTION ---- Button - Settings ----- #
    async def send_button(self):        
        await _reload_texts()
        morgens_button = Button(label="Morgens", style=discord.ButtonStyle.success)
        abends_button = Button(label="Abends", style=discord.ButtonStyle.danger)
        updates_button = Button(label="Updates", style=discord.ButtonStyle.primary)
        

        #SECTION ---- Callbacks ----- #
        async def button_callback_morgens(interaction):
            role_id = ROLE_ID_MORGENS
            role = interaction.guild.get_role(role_id)
            member = interaction.user
        
            if role in member.roles:
                await member.remove_roles(role)
                await interaction.response.send_message(texts.get('Settings_Response_Morgen_Down',''), ephemeral=True)
            else:
                await member.add_roles(role)
                await interaction.response.send_message(texts.get('Settings_Response_Morgen_Up',''), ephemeral=True)
        
        async def button_callback_abends(interaction):
            role_id = ROLE_ID_ABENDS
            role = interaction.guild.get_role(role_id)
            member = interaction.user
        
            if role in member.roles:
                await member.remove_roles(role)
                await interaction.response.send_message(texts.get('Settings_Response_Abend_Down',''), ephemeral=True)
            else:
                await member.add_roles(role)
                await interaction.response.send_message(texts.get('Settings_Response_Abend_Up',''), ephemeral=True)
        
        async def button_callback_updates(interaction):
            role_id = ROLE_ID_UPDATES
            role = interaction.guild.get_role(role_id)
            member = interaction.user
        
            if role in member.roles:
                await member.remove_roles(role)
                await interaction.response.send_message(texts.get('Settings_Response_Updates_Down',''), ephemeral=True)
            else:
                await member.add_roles(role)
                await interaction.response.send_message(texts.get('Settings_Response_Updates_Up',''), ephemeral=True)

        morgens_button.callback = button_callback_morgens
        abends_button.callback = button_callback_abends
        updates_button.callback = button_callback_updates
        #!SECTION ---- Callbacks ----- #

        
        view = View(timeout=None)  # Set timeout to None to keep the view active indefinitely
        view.add_item(morgens_button)
        view.add_item(abends_button)
        view.add_item(updates_button)
        
        Setting_Info_Title = texts.get('Settings_Info_Title', '')
        Setting_Info_Text = texts.get('Settings_Info_Text', '')

        channel = client.get_channel(SETTINGS_CHANNEL_ID)
        color = discord.Color.from_rgb(0, 0, 0)
        embed = discord.Embed(title=Setting_Info_Title, description=Setting_Info_Text, color=color)
        
        await channel.purge(limit=2)
        await channel.send(embed=embed)
        await asyncio.sleep(5)
        await channel.send(view=view)
    #!SECTION ---- Button - Settings ----- #


    #SECTION ---- Message Handling ---- #
    async def on_message(self, message):
        tokens = message.content.lower().strip().split()
        if message.author == self.user:
            return
        elif message.channel.id == VERTRETUNGS_CHANNEL_ID:
            await message.channel.purge(limit=1, check=lambda m: m.id == message.id)
        if not tokens:
            await _log(f"Empty message received, ignoring: {message.content} -> message.author: {message.author}")
            return
        if tokens[0] == "ping":
            await message.channel.send("pong", delete_after=SHORT_DELETE_TIME)
            await _log("Responded to ping command.")
        elif tokens[0] == "vp" :
            if tokens.__len__() < 3:
                await _send_respond_message(original_message=message, day=tokens[1])  
            else:
                await _send_respond_message(original_message=message, day=tokens[1], clas=tokens[2])
            avatar_url = _get_avatar_pic_url(message)
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(COMMAND_USE_LOG_URL, session=session)
                await webhook.send(message.content.lower(), username=message.author.display_name, avatar_url=avatar_url)
        elif "update" in tokens and message.channel.id == START_MESSAGE_CHANNEL_ID:
            await _reload_texts()
            if tokens.__len__() > 1:
                if tokens[1] == "-dry":
                    await message.channel.send(texts.get("Update_Dailys_Beginn_Response","").format(dry_run=True), delete_after=SHORT_DELETE_TIME)
                await _send_daily_update_message(dry_run=True)
            await _send_daily_update_message()
    #!SECTION ---- Message Handling ---- #

    #SECTION ---- Member Join Handling ---- #
    async def on_member_join(self, member):
        await _log(texts.get('New_Join','').format(member=member.name))
        channel = client.get_channel(JOINS_CHANNEL_ID)
        embed = discord.Embed(title="Joined:", description="<@" + str(member.id) + "> - " + str(member.name), color=discord.Color.from_rgb(0, 0, 0))

        allow_button = Button(label="Morgens", style=discord.ButtonStyle.success)
        deny_button = Button(label="Abends", style=discord.ButtonStyle.danger)
    #SECTION ---- Callbacks ----- #
        async def button_callback_allow_button(interaction, member=member):
            role_id = ROLE_ID_STUDENT
            role = interaction.guild.get_role(role_id)
        
            await member.add_roles(role)
            await interaction.response.send_message("<@" + str(member.id) + "> - " + str(member.name) + texts.get('User_Allowed',''), ephemeral=True)
        
        async def button_callback_deny_button(interaction, member=member):
            member.kick(reason=texts.get('Kick_Reason',''))
            await interaction.response.send_message("<@" + str(member.id) + "> - " + str(member.name) + texts.get('User_Denied',''), ephemeral=True)

        allow_button.callback = button_callback_allow_button
        deny_button.callback = button_callback_deny_button
        #!SECTION ---- Callbacks ----- #

        view = View(timeout=None)  # Set timeout to None to keep the view active indefinitely
        view.add_item(allow_button)
        view.add_item(deny_button)
        await channel.send(embed=embed)
        await channel.send(texts.get('Join_New_Ping',''), delete_after=0)
    #!SECTION ---- Member Join Handling ---- #

intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
tree = discord.app_commands.CommandTree(client)


#SECTION ---- Slash Command Handling ---- #
@tree.command(name="update", description=texts.get("Update_Description",""))
@discord.app_commands.describe(dry=texts.get("Update_Dry_Description",""))
async def update(interaction: discord.Interaction, dry: bool = True):
    await interaction.response.send_message(texts.get("Update_Dailys_Beginn_Response","").format(dry_run=dry), delete_after=SHORT_DELETE_TIME, ephemeral=True)
    await _reload_texts()
    await _send_daily_update_message(dry_run=dry)

@tree.command(name="vp", description=texts.get("VP_Description",""))
@discord.app_commands.describe(tag=texts.get("VP_Tag_Description",""), klasse=texts.get("VP_Klasse_Description",""))
async def vp(interaction: discord.Interaction, tag: str, klasse: str):
    await interaction.response.send_message(texts.get("Loading_Message",""), delete_after=SHORT_DELETE_TIME, ephemeral=True)
    await _send_respond_message(day=tag, clas=klasse, original_message=interaction)
#!SECTION ---- Slash Command Handling ---- #


#!SECTION ---- Discord Bot ---- #
client.run(BOT_TOKEN)