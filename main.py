import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
import re
import asyncio

CONFIG_PATH = "./config/bot_settings.json"

# 載入設定
with open(CONFIG_PATH) as json_file:
    config = json.load(json_file)

# 建立機器人實例
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# 初始化表符字典
emoji_dict = {}

async def fetch_application_emojis(app_id, bot_token):
    """獲取應用程式擁有的表符"""
    url = f"https://discord.com/api/v10/applications/{app_id}/emojis"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Error fetching emojis: {response.status} {await response.text()}")
                return None

async def list_application_emojis():
    """列出應用程式擁有的表符"""
    app_id = config["APP_ID"]  # 您的應用程式 ID
    bot_token = config["BOT_TOKEN"]     # 機器人的 Token

    emojis = await fetch_application_emojis(app_id, bot_token)
    if emojis:
        emoji_dict.update({emoji['name']: emoji['id'] for emoji in emojis.get("items",[])})
        # emoji_list = "\n".join([f"{emoji['name']}: {emoji['id']}" for emoji in emojis.get("items", [])])
        # await ctx.send(f"應用程式擁有的表符：\n{emoji_list or '沒有可用的表符。'}")
    else:
        # await ctx.send("無法獲取應用程式的表符。")
        print("無法獲取應用程式的表符。")

@bot.event
async def on_ready():
    global emoji_dict
    await list_application_emojis()
    print(emoji_dict)
    # emoji_dict = {emoji.name: str(emoji) for emoji in bot.emojis}
    # print("Bot is ready and emojis loaded:", emoji_dict)
    # 獲取所有伺服器的自訂表符
    # for guild in bot.guilds:
    #     emoji_dict.update({emoji.name: str(emoji) for emoji in guild.emojis})
    #     print("Emojis_owned:",emoji_dict)
    # 在所有伺服器中同步命令
    await bot.tree.sync()

# 定義上傳 emoji 的指令 還不能用 打指令沒辦法上傳圖片
@bot.tree.command(name="add_emoji")
async def add_emoji(interaction: discord.Interaction, name: str):
    """新增一個表符和其對應名稱 (需附上圖片附件)"""
    if not interaction.message.attachments:
        await interaction.response.send_message("請附加一張圖片來作為表符。", ephemeral=True)
        return

    # 取得圖片 URL
    image_url = interaction.message.attachments[0].url
    
    # 檢查是否有權限上傳表符
    if not interaction.guild.me.guild_permissions.manage_emojis:
        await interaction.response.send_message("我沒有權限上傳表符。", ephemeral=True)
        return

    # 上傳表符
    try:
        emoji = await interaction.guild.create_custom_emoji(name=name, image=await fetch_image(image_url))
        emoji_dict[name] = str(emoji)
        await interaction.response.send_message(f"表符 '{name}' 已儲存成功！", ephemeral=True)
    except discord.HTTPException:
        await interaction.response.send_message("無法上傳表符，請檢查圖片格式或大小。", ephemeral=True)

# 錯誤處理 - 捕捉缺少參數的錯誤
@add_emoji.error
async def add_emoji_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("指令格式錯誤！請使用 `/add_emoji <名稱>`，並附加圖片。")

async def fetch_image(url): # 應該還不能用
    """從 URL 下載圖片並返回二進制數據"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.read()

# 定義列出 emoji 的指令
@bot.tree.command(name="list")
async def list_emojis(interaction: discord.Interaction):
    """顯示所有儲存的表符名稱和對應 emoji"""
    if not emoji_dict:
        await interaction.response.send_message("目前沒有儲存任何表符。", ephemeral=True)
    else:
        emoji_list = "\n".join([f"{name}: <:{name}:{emoji}>" for name, emoji in emoji_dict.items()])
        await interaction.response.send_message(f"儲存的表符：\n{emoji_list}", ephemeral=True)

# 定義說明的指令
@bot.tree.command(name="help")
async def help_command(interaction: discord.Interaction):
    """顯示機器人的使用說明"""
    help_message = (
        "以下是可用的指令：\n"
        "/add_emoji <名稱> - 新增表符，並附上圖片\n"
        "/list - 列出所有儲存的表符\n"
        "/help - 顯示此說明"
    )
    await interaction.response.send_message(help_message, ephemeral=True)

# 偵測訊息事件
@bot.event
async def on_message(message):
    # 機器人不回應自己
    if message.author == bot.user:
        return

    # 使用正則表達式查找所有符合 ?!xxx!? 的表符名稱
    matches = re.findall(r"\?!([a-zA-Z0-9_]+)!?", message.content)
    new_content = message.content

    # 替換找到的表符名稱
    for match in matches:
        if match in emoji_dict:
            new_content = new_content.replace(f"?!{match}!?", f"<:{match}:{emoji_dict[match]}>")
            # 刪除原訊息
            await message.delete()
            
            # 發送新的訊息，模仿原訊息的發送者
            # emoji_replaced_message = emoji_dict[emoji_name]
            webhook = await message.channel.create_webhook(name=message.author.display_name)
            await webhook.send(
                content=new_content,
                username=message.author.display_name,
                avatar_url=message.author.avatar.url,
            )
            await webhook.delete()
    # 如果有替換，刪除原訊息並用替換後的訊息重新發送
    # if new_content != message.content:
    #     await message.delete()
    #     await message.channel.send(
    #         f"{message.author.display_name} 發送了: {new_content}"
    #     )

    # await bot.process_commands(message)

# 啟動機器人
bot.run(config["BOT_TOKEN"])
# async def main():
#     output = await (fetch_application_emojis(app_id=config["APP_ID"],bot_token=config["BOT_TOKEN"]))
#     print(output)
# asyncio.run(main())