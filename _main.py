import discord
from discord.ext import commands
import json
import re

CONFIG_PATH = "./config/bot_settings.json"

# 載入設定
with open(CONFIG_PATH) as json_file:
    config = json.load(json_file)

# 建立機器人實例
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# 初始化表符字典
emoji_dict = {}

@bot.event
async def on_ready():
    # 載入機器人擁有的表符列表
    print(bot)
    global emoji_dict
    emoji_dict = {emoji.name: str(emoji) for emoji in bot.emojis}
    print("Bot is ready and emojis loaded:", emoji_dict)
    # 在所有伺服器中同步命令
    await bot.tree.sync()

@bot.tree.command(name="list")
async def list_emojis(interaction: discord.Interaction):
    """顯示所有儲存的表符名稱和對應 emoji"""
    if not emoji_dict:
        await interaction.response.send_message("目前沒有儲存任何表符。", ephemeral=True)
    else:
        emoji_list = "\n".join([f"{name}: {emoji}" for name, emoji in emoji_dict.items()])
        await interaction.response.send_message(f"儲存的表符：\n{emoji_list}", ephemeral=True)

# 定義說明的命令
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
            new_content = new_content.replace(f"?!{match}!?", emoji_dict[match])
            # 刪除原訊息
            await message.delete()
            
            # 發送新的訊息，模仿原訊息的發送者
            emoji_replaced_message = emoji_dict[emoji_name]
            webhook = await message.channel.create_webhook(name=message.author.display_name)
            await webhook.send(
                content=emoji_replaced_message,
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

    await bot.process_commands(message)

# 啟動機器人
bot.run(config["BOT_TOKEN"])

