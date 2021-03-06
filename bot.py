from libs import iFunny
import asyncio
import aiohttp

email = ""
password = ""
region = "United States" #or "Brazil"
api_key = ""
prefix = "-"

bot = iFunny.Bot(email, password, region, api_key, prefix)

bot.developer = None #(you can choose to insert the user id of a user who is in charge of the bot)


@bot.command(developer=True)
async def blacklist(ctx, *args):
	
	chat = ctx.chat
	
	if args:
		user = await ctx.user(args[0])
		ctx.bot.blacklist(user)
		return await chat.send(f"{user.nick} has been blacklisted")
		
	await chat.send(ctx.bot.blacklist())
	
	
@bot.command(developer=True)
async def whitelist(ctx, *args):
	
	chat = ctx.chat
	
	if args:
		user = await ctx.user(args[0])
		ctx.bot.whitelist(user)
		return await chat.send(f"{user.nick} has been whitelisted")


@bot.command(name="hi", aliases=["hey","heyy"], help_message="I will say hi to you")
async def hello(ctx, *args):
	"""docstring overridden by decorator kwargs help_message"""

	chat = ctx.chat
	message = ctx.message
	author = message.author

	await chat.send(f"Hi there {author.name} :)")
	

@bot.command(help_category="general")
async def say(ctx, *args):
	"""I will repeat you"""

	chat = ctx.chat
	message = ctx.message

	await chat.send(message.args)
	
	
@bot.command(help_category="general")
async def mimic(ctx, *args):
	"""A long-lived command example. I mimic what you say."""

	chat = ctx.chat
	
	await chat.send("I will now repeat you. Say stop to stop me.")
	
	while message := await chat.input(type=any): #iFunny.Message or iFunny.File or any
		
		if isinstance(message, iFunny.File):
			await chat.send({"img": "Image", "video": "Video"}[message.type])
		
		elif isinstance(message, iFunny.Message):
		
			if message.text.lower() == "stop":
				return await chat.send("ok lol")
			
			await chat.send(message.text)
			
	await chat.send("No longer mimicking")
		
		
@bot.command(hide_help=True)
async def ping(ctx, *args):
	"""See how fast the bot replies"""

	chat = ctx.chat
	message = ctx.message

	await chat.send("Pong "+str(message.ping)+" ms")
	
	
@bot.command(help_category="general")
async def members(ctx, *args):
	"""see the number of members in the chat"""
	
	import random
	chat = ctx.chat
	mems = await chat.members()

	await chat.send(f"There are {len(mems)} members in this chat")
	
	
@bot.command(help_category="general")
async def invite(ctx, *args):
	"""invite a user to the chat"""
	
	chat = ctx.chat
	
	if not args:
		return await chat.send("Specify a user to invite")
	
	user = await ctx.user(args[0])
	
	if not await chat.has_member(user):
		await chat.invite(user)
		await chat.send(f"{user.name} has been invited to the chat")
		
	else:
		await chat.send("That user is already in the chat")


@bot.command(help_category="general")
async def image(ctx, *args):
	"""I will repeat you"""

	chat = ctx.chat
	message = ctx.message
	
	url = "https://picsum.photos/200"
	
	async with aiohttp.ClientSession() as session:
		async with session.get(url) as r:
			
			try:
				await chat.upload(await r.read())
			except:
				await chat.send("There was an error sending the image")
				
				
@bot.command(developer=True, hide_help=True)
async def secret(ctx, *args):
	"""A developer only command"""
	
	chat = ctx.chat
	author = ctx.author
	
	await chat.send(f"This command can only be done by you, {author.name}")
	
	
"""
The following bot.event callbacks yield to the ratelimit.
If the bot is ratelimited, messages from the event callbacks
will not be sent.

This can be disabled by:
	ctx.chat.yield_ratelimit = False
	
Having these functions is not mandatory; they are just here
to demonstrate how they work.
"""
		
@bot.event()
async def user_join(ctx):
	await ctx.chat.send("Hello "+ctx.user.name)
	
@bot.event()
async def user_leave(ctx):
	await ctx.chat.send("Bye "+ctx.user.name)
	
@bot.event()
async def user_kick(ctx):
	await ctx.chat.send(ctx.user.name+" deserved it")
	
@bot.event()
async def channel_change(ctx):
	"""runs when the chat title, icon, or description is changed"""
	await ctx.chat.send("I have detected a channel change")

@bot.event()
async def on_join(ctx):
	"""runs when the bot joins a chat."""
	await ctx.chat.send(f"Thanks for adding me {ctx.chat.inviter.name}!")
	
@bot.event()
async def on_message(ctx):
	"""runs when someone sends a non-command message"""
	import random
	responses = ["gm", "good morning", "gn", "good night"]
	if ctx.message.text.lower() in responses:
		await ctx.chat.send(random.choice(responses))
		
@bot.event()
async def on_file(ctx):
	"""runs when someone sends an image in chat. neither self nor bots are ignored"""
	
	return

bot.run()


