import requests
import websockets
import simplejson
import json
import asyncio
import aiohttp
import traceback
from termcolor import colored
from datetime import datetime
import time
import textwrap
import sys
import sqlite3
import os

host = "https://api.ifunny.chat"


def cprint(*args, end_each=" ", end_all=""):
	dt = str(datetime.fromtimestamp(int(time.time())))
	print(colored(dt, "white"), end=end_each)
	for i in args:
		print(colored(str(i[0]), i[1].lower()), end=end_each)
	print(end_all)
	
	
async def get_request(url):
	async with aiohttp.ClientSession() as session:
		async with session.get(url) as r: 
			return await r.json()
			
			
async def post_request(url, data=None):
	async with aiohttp.ClientSession() as session:
		async with session.post(url, data=data) as r: 
			return await r.json()
			
			
class LoginError(Exception): pass
			
class Parser:

	version = "7b2274797065223a2022626f74227d"

	@staticmethod
	async def chat_list(bot, ctx, frame):
		
		bot.chats = [Chat(i, bot) for i in frame["chat_list"]]


	@staticmethod
	async def invitations(bot, ctx, frame):
		
		for i in frame["invitations"]:
			ctx.chat = Chat(i["chat"], bot)
			ctx.chat.inviter = User(i["inviter"], bot)
			await bot.accept_invite(ctx)
			cprint(("Joined chat", "magenta"), (i["chat"]["id"], "yellow"))
				
				
	@staticmethod
	async def error(bot, ctx, frame):
		
		if frame["error"] == "message_rate_limit":
			bot.ratelimit()
			if package := bot.unconfirmed_queue.get(frame["response_to"]):
				await asyncio.sleep(0.5)
				await bot.message_queue.put(package)
			
			
	@staticmethod
	async def affirmation(bot, ctx, frame):
		
		if bot.unconfirmed_queue.get(frame["response_to"]):
			del bot.unconfirmed_queue[frame["response_to"]]
				
				
	@staticmethod
	async def chat_event(bot, ctx, frame):
		
		if function := bot.events.get(frame["chat_event"]):
			ctx.chat = Chat(frame["chat"], bot)
			
			if frame["user"]:
				if frame["user"]["id"] == bot.user_id: return
				ctx.user = User(frame["user"], bot)
			
			ctx.chat.yield_ratelimit = True
			bot.run_callback(function, ctx)
				
				
	@staticmethod
	async def member_list(bot, ctx, frame):
		
		if chat_id := bot.member_request_ids.get(frame["response_to"]):
			if q := bot.member_list_queues.get(chat_id):
				await q.put(frame["member_list"])
		
		
	@staticmethod
	async def message(bot, ctx, frame):
		
		user_id = frame["user"]["id"]
		
		if user_id == bot.user_id: return
		if frame["user"].get("is_bot"): return
		if user_id in bot.blacklist() and user_id != bot.developer: return
		
		ctx.chat = Chat(frame["chat"], bot)
		ctx.message = Message(frame["message"], bot)
		ctx.author = User(frame["user"], bot)
		ctx.message.author = ctx.author
		ctx.chat.message = ctx.message
		ctx.message.chat = ctx.chat
		ctx.chat.author = ctx.author
		ctx.author.is_developer = ctx.author.id == bot.developer
				
		if frame["message"]["text"].startswith(bot.prefix):

			if command_items := frame["message"]["text"].strip(bot.prefix).split():
				base_name = command_items[0]
				
				if function := bot.commands.get(base_name):
					await bot.run_command(function, ctx)
				
		else:
			await bot.siphon_input(bot.on_message, ctx)
				
				
	@staticmethod
	async def file(bot, ctx, frame):
		
		user_id = frame["user"]["id"]
		
		#if user_id == bot.user_id: return
		#if frame["user"].get("is_bot"): return
		if user_id in bot.blacklist() and user_id != bot.developer: return

		if bot.on_file:
			
			ctx.chat = Chat(frame["chat"], bot)
			ctx.message = File(frame["file"], bot)
			ctx.author = User(frame["user"], bot)
			ctx.message.author = ctx.author
			ctx.chat.message = ctx.message
			ctx.message.chat = ctx.chat
			ctx.author.is_developer = ctx.author.id == bot.developer
			await bot.siphon_input(bot.on_file, ctx)
	
	

async def user_by_nick(nick: str, bot=None):
	data = await get_request(host+"/user_by_nick/"+nick)
	if data["status"] == 200:
		return User(data["data"], bot)
		
		
async def user_by_id(user_id: str, bot=None):
	data = await get_request(host+"/user/"+user_id)
	if data["status"] == 200:
	
		return User(data["data"], bot)


class CTX:
	
	chat = None
	message = None
	author = None
	user = None
	inviter = None
	
	def __init__(self, bot=None):
		self.bot = bot
		
	async def user(self, nick_or_id):
		return await(user(nick_or_id, self.bot))
		
	async def user_by_nick(self, nick: str):
		return user_by_nick(nick, self.bot)
		
	async def user_by_id(self, user_id: str):
		return user_by_id(nick, self.bot)
		
		
class CTXtype:
	
	def __init__(self, data, bot):
		self.bot = bot
		for k, v in data.items():
		  setattr(self, k, v)
		
			
class User(CTXtype):
	
	def __init__(self, data, bot):
		super().__init__(data, bot)
		self.chat_id = bot.user_id+"_"+self.id
		self.name = self.nick
		self.blacklisted = self.id in bot.blacklist()
		self.developer = self.id == bot.developer
		
	def __eq__(self, other):
		return self.id == other.id
		
	def __ne__(self, other):
		return self.id != other.id
		
	async def send(self, message):
		await self.bot.send_message(self.chat_id, message)
		
	async def upload(self, data):
		await self.bot.upload(self.chat_id, data)
		
		
async def user(nick_or_id: str, bot=None):
	
	nick_or_id = nick_or_id.lower()
	
	if len(nick_or_id) == 24 and nick_or_id[0].isdigit() and sum([1 for i in nick_or_id if ord(i) >= 103]): #most likely to be an id
		if test_user := await user_by_id(nick_or_id, bot):
			return test_user
	
	return await user_by_nick(nick_or_id, bot)
	

class Message(CTXtype):
	
	def __init__(self, data, bot):
		super().__init__(data, bot)
		self.author = None
		self.chat = None
		self.text = self.text.strip()
		self.args_list = self.text.split(" ")[int(bool(self.text.startswith(bot.prefix))):]
		self.args = " ".join(self.args_list)
		self.ts = self.pub_at
		self.ping = int(time.time()*1000)-self.ts
		
	def __eq__(self, other):
		return self.text == other.text
		
	def __ne__(self, other):
		return self.text != other.text
		
		
class File(CTXtype):
	
	def __init__(self, data, bot):
		super().__init__(data, bot)
		for k, v in data["file"].items():
		  setattr(self, k, v)
		self.author = None
		self.chat = None
		self.ts = self.pub_at
		self.ping = int(time.time()*1000)-self.ts
		
	def __eq__(self, other):
		return self.hash == other.hash
		
	def __ne__(self, other):
		return self.hash != other.hash
		
		
class Chat(CTXtype):
	
	def __init__(self, data, bot):
		super().__init__(data, bot)
		self.author = None
		self.message = None
		self.inviter = None
		self.yield_ratelimit = False
		
	def __eq__(self, other):
		return self.id == other.id
		
	def __ne__(self, other):
		return self.id != other.id
		
	async def send(self, message):
		if self.yield_ratelimit and self.bot.ratelimited: return
		author_name = None
		if self.author and self.type != 1: author_name = self.author.nick
		await self.bot.send_message(self.id, message, author_name)
		
	async def upload(self, data):
		await self.bot.upload(self.id, data)
		
	async def members(self):
		return await self.bot.get_members(self.id)
		
	async def has_member(self, user):
		for i in await self.members():
			if user == i: return True
		return False
		
	async def invite(self, user):
		await self.bot.invite(self.id, user.id)
		
	async def input(self, type=Message, timeout=None):
		return await self.bot.input(self.id, type, timeout)


class Bot:
	
	def __init__(self, email: str, password: str, region: str, api_key: str, prefix: str):
	
		assert(prefix), "Prefix string cannot be empty"
	
		self.email = email
		self.password = password
		self.region = region
		self.api_key = api_key
		self.prefix = prefix
		self.user_id = ""
		self.nick = ""
		self.commands = {}
		self.events = {}
		self.cooldowns = {}
		self.timekeeping = {}
		self.developer_commands = []
		self.developer = None
		self.help_categories = {}
		self.command_help_messages = {}
		self.member_list_queues = {}
		self.member_request_ids = {}
		self.chats = []
		self.ratelimited = False
		self.open = True
		self.on_join = self.on_message = self.on_file = None
		self.prev_chat_id = self.prev_message = self.prev_nick = None
		self.unconfirmed_queue = {}
		self.siphons = {}
		self.generate_help_command()
		self._blacklist = set()
		self.load_blacklist()
		self.login()
		

	def login(self):
	
		url = host+"/login"
		payload = json.dumps({"email": self.email,
			"password": self.password, "region": self.region,
			"apikey": self.api_key})
			
		try:
			login = requests.post(url, data=payload)
			login = login.json()
			
		except (json.decoder.JSONDecodeError, simplejson.errors.JSONDecodeError):
			raise LoginError("The server accepted the login request but did not reply. Try again later.")
		
		except:
			raise LoginError("A complete failure occurred while contacting the server to login.")
		
		if login["error"]:
			raise LoginError("An error occurred while attempting to login: "+login["error_description"])
		
		self.bearer = login["bearer"]
		self.user_id = login["user_id"]
		
		cprint(("Bot is authenticated", "magenta"))
		
		
	def command(self, *args, **kwargs):
		def container(function):
		
			name = kwargs.get("name")
			if not name: name  = function.__name__
			name = name.lower()
			self.commands[name] = function
			
			if not kwargs.get("hide_help"):
				help_category = kwargs.get("help_category")
				if help_category: help_category = str(help_category).lower()
				
				if not self.help_categories.get(help_category):
					self.help_categories[help_category] = []
				
				self.help_categories[help_category].append(name)
				help_message = function.__doc__
				if kwargs.get("help_message"): help_message = kwargs.get("help_message")
				self.command_help_messages[function] = help_message
				
			if aliases := kwargs.get("aliases"):
				for alias in aliases:
					self.commands[alias] = function
					
			if cooldown := kwargs.get("cooldown"):
				self.cooldowns[function] = cooldown
				
			if kwargs.get("developer"):
				self.developer_commands.append(function)
			
			def decorator(*dargs, **dkwargs):
				return function(*dargs, **dkwargs)
			
			return decorator
		return container
		
		
	def event(self, *args, **kwargs):
		def container(function):
		
			name = function.__name__
			valid_types = ("user_join", "user_leave", "user_kick", "channel_change", "on_join", "on_message", "on_file")
			assert (name in valid_types), "Function name for an event must be in "+", ".join(valid_types)
			
			if name in valid_types[4:]: setattr(self, name, function)
			else: self.events[name] = function

			def decorator(*dargs, **dkwargs):
				function(*dargs, **dkwargs)

			return decorator
		return container
		

	def run(self):
		
		try:
			asyncio.run(self.run_tasks())
		
		except KeyboardInterrupt:
			print()
			cprint(("Bot has shut down", "red"))
		
		except:
			cprint(("Bot has shut down due to error", "red"))
			traceback.print_exc()
		
		finally:
			self.blacklist_db_con.commit()
			self.blacklist_db_con.close()
			sys.exit(0)
			
		
	def disconnect(self):
		cprint(("Shutting down bot...", "red"))
		self.open = False
		
		
	async def connect_ws(self):
	
		connected = False
		
		while not connected:
		
			try:
				self.ws = await websockets.connect("wss://api.ifunny.chat/ws/"+self.bearer)
				
				ws_status = json.loads(await self.ws.recv())

				if ws_status["type"] == "connection_error":
					cprint(("Websocket connected but received error: "+ws_status["error"], "red"))
					cprint(("Attempting new login", "magenta"))
					
					try:
						self.login()
						continue
						
					except LoginError as ex:
						cprint((str(ex), "red"))
					
				elif ws_status["type"] == "connection_success":
					self.nick = ws_status["user_info"]["nick"]
					self.user_id = ws_status["user_info"]["user_id"]
					connected = True
					break
					
			except KeyboardInterrupt:
				return self.disconnect()

			except:
				cprint(("Error connecting to websocket", "red"))

			cprint(("Attempting new connection in 5 seconds...", "red"))
			await asyncio.sleep(5)
			
			continue

		await asyncio.sleep(1)
		cprint(("Bot is online", "magenta"))
		cprint(("User id", "magenta"), (self.user_id, "yellow"), ("Username", "magenta"), (self.nick, "green"))
		

	async def run_tasks(self):
	
		self.message_queue = asyncio.Queue()
		await self.connect_ws()
		await asyncio.gather(
			asyncio.create_task(self.listen()),
			asyncio.create_task(self.message_queuer()))


	async def listen(self):

		while self.open:

			try:
				if frame := await self.ws.recv():
					await self.parse(json.loads(frame))
					
			except websockets.exceptions.ConnectionClosedOK:
				cprint(("Server has closed the connection", "red"))
				await self.connect_ws()
				
			except websockets.exceptions.ConnectionClosedError:
				cprint(("Disconnected from server due to error", "red"))
				await self.connect_ws()
				
			except KeyboardInterrupt:
				return self.disconnect()
				
				
	async def siphon_input(self, callback, ctx):
		
		if ctx.chat.id in self.siphons:
			for t, q in self.siphons[ctx.chat.id].items():
				if t == any or type(ctx.message) == t:
					await q.put(ctx.message)
		
		if callback:
			self.run_callback(callback, ctx)
			
			
	async def input(self, chat_id, type=Message, timeout=None):
		
		if not self.siphons.get(chat_id):
			self.siphons[chat_id] = {}
			
		if not self.siphons[chat_id].get(type):
			self.siphons[chat_id].update({type: asyncio.Queue()})
		
		try:
			message = await asyncio.wait_for(self.siphons[chat_id][type].get(), timeout)
		
		except:
			message = None
			
		del self.siphons[chat_id][type]
		if not self.siphons[chat_id]:
			del self.siphons[chat_id]
			
		return message
		
		
	def blacklist(self, user=None):
		
		if not user:
			return list(self._blacklist)
		
		if isinstance(user, User):
			user = user.id
		
		if user == self.developer:
			return False
			
		self._blacklist.add(user)
		self.blacklist_db_con.execute("INSERT INTO users VALUES (?)", (user,))
		self.blacklist_db_con.commit()
		return True
		
		
	def whitelist(self, user):
		
		if isinstance(user, User):
			user = user.id
			
		if user not in self._blacklist:
			return False
			
		self._blacklist.remove(user)
		self.blacklist_db_con.execute("DELETE FROM users WHERE id = ?", (user,))
		self.blacklist_db_con.commit()
		return True
		
		
	def load_blacklist(self):
		
		self.blacklist_db_con = sqlite3.connect("libs/data/blacklist.db")
		self.blacklist_db_cur = self.blacklist_db_con.cursor()
		self.blacklist_db_cur.execute("CREATE TABLE IF NOT EXISTS users (id TEXT, unique(id))")
		self.blacklist_db_con.commit()
		self._blacklist = set([i[0] for i in self.blacklist_db_cur.execute("SELECT * FROM users")])
			

	async def message_queuer(self):
	
		while self.open:
		
			if self.ratelimited:
				await asyncio.sleep(60)
				self.unratelimit()
				self.unconfirmed_queue = {}
				
				queue_dict = {}
				
				while not self.message_queue.empty():
					chat_id, message, nick = await self.message_queue.get()
					message = str(message)
					if not queue_dict.get(chat_id): queue_dict[chat_id] = []
					if nick: message = nick+": "+message
					queue_dict[chat_id].append(message)
					
				for k, v in queue_dict.items():
					message = "\n\n".join(v)
					await self.message_queue.put((k, message, None))
					
				continue
					
			chat_id, message, nick = await self.message_queue.get()
			
			if self.ratelimited:
				await self.message_queue.put((chat_id, message, nick))
				continue
			
			try:
				payload = json.loads(bytes.fromhex(Parser.version).decode("utf-8"))
			
			except:
				return self.disconnect()
				
			request_id = int(time.time()*1000000)
			package = (chat_id, message, nick)
			self.unconfirmed_queue[request_id] = package
			
			await self.ws.send(
				json.dumps({"type": "message", "message": message,
				"chat_id": chat_id,
				"request_id": request_id,
				"payload": payload}))
				
			
			
	async def send_message(self, chat_id, message, nick=None):
	
		chunks = textwrap.wrap(str(message), 500, break_long_words=True, replace_whitespace=False)
		
		for message in chunks:
			await self.message_queue.put((chat_id, message, nick))
			

	async def accept_invite(self, ctx):
		await self.ws.send(json.dumps({"type": "accept_invitation", "chat_id": ctx.chat.id}))
		if self.on_join:
			await asyncio.sleep(0.1)
			self.run_callback(self.on_join, ctx)
			
			
	async def get_members(self, chat_id):
		request_id = int(time.time()*1000)
		self.member_request_ids[request_id] = chat_id
		self.member_list_queues[chat_id] = asyncio.Queue()
		await self.ws.send(json.dumps({"type": "list_members", "chat_id": chat_id, "request_id": request_id}))
		
		try:
			member_list = await asyncio.wait_for(self.member_list_queues[chat_id].get(), 3)
		except asyncio.TimeoutError:
			member_list = []
			
		del self.member_list_queues[chat_id]
		member_list = [User(i, self) for i in member_list]
		return member_list
		
		
	async def invite(self, chat_id, user_id):
		await self.ws.send(json.dumps({"type": "send_invitation", "user_id": user_id, "chat_id": chat_id}))
		
		
	async def upload(self, chat_id, data):
	
		form = aiohttp.FormData()
		form.add_field("bearer", self.bearer)
		form.add_field("chat_id", chat_id)
		form.add_field("file", data, filename=f"{int(time.time()*1000)}.img", content_type="multipart/form-data")
		response = await post_request(host+"/upload", form)
		
		if response["error"]:
			raise Exception(response)
			
		
	async def parse(self, frame):
	
		ctx = CTX(self)
	
		if hasattr(Parser, frame["type"]):
			await getattr(Parser, frame["type"])(self, ctx, frame)
						
						
	def ratelimit(self):
		if not self.ratelimited:
			self.ratelimited = True
			cprint(("Ratelimited", "red"))
		
		
	def unratelimit(self):
		if self.ratelimited:
			self.ratelimited = False
			cprint(("Ratelimit unlocked", "magenta"))
		
		
	async def run_command(self, function, ctx):
	
		if function in self.developer_commands and not ctx.author.is_developer:
			return
	
		ratelimit = self.cooldowns.get(function)
		now = time.time()
		
		if not ctx.author.is_developer:
			if ratelimit:
				user_timekeeping = self.timekeeping.get(ctx.author.id)
				if user_timekeeping:
					ratelimit_expires_at = user_timekeeping.get(function)
					if ratelimit_expires_at:
						if now < ratelimit_expires_at:
							remaining_time = int(ratelimit_expires_at-now)
							remaining_time_str = seconds_to_str(remaining_time)
							return await ctx.chat.send(f"You must wait {remaining_time_str} before you can use this command again")
						else:
							del self.timekeeping[ctx.message.author.id][function]
		
		if not self.timekeeping.get(ctx.author.id):
			self.timekeeping[ctx.author.id] = {}
			
		if self.cooldowns.get(function):
			self.timekeeping[ctx.author.id][function] = now+self.cooldowns[function]
		
		cprint((ctx.author.id, "yellow"), (ctx.author.nick, "green"), (ctx.message.text.strip(self.prefix), "cyan"))
		self.run_callback(function, ctx, *ctx.message.args_list)
		
		
	def run_callback(self, function, *args):
		asyncio.get_event_loop().create_task(function(*args))


	def generate_help_command(self):
	
		@self.command(hide_help=True)
		async def help(ctx, *args):
			
			self = ctx.bot
		
			if args:
				
				if command_list := self.help_categories.get(args[0].lower()):
					response = "List of commands"
					response += f"\n▼{args[0].title()}\n\n"
					response += "\n".join([self.prefix+i for i in command_list
						if (not self.commands[i] in self.developer_commands or
						(ctx.author.is_developer and self.commands[i] in self.developer_commands))])
					response += f"\n\nUse \"{self.prefix}help (command name)\" for detailed usage help."
			
				elif function := self.commands.get(args[0]):
					function_help = self.command_help_messages[function]
					if not function_help: function_help = "No help message for this command has been written"
					response = f"{self.prefix}{function.__name__}\n\n{function_help}"
					
				else:
					response = "A category or command with that name does not exist. Check \"{self.prefix}help\" for the full list of commands."
				
			else:
				response = "List of command categories:\n\n"
				response += "\n".join(["‣"+i for i in self.help_categories.keys() if i])
				
				if None in self.help_categories:
					response += "\n\nUncategorized commands:\n\n"
					response += "\n".join([self.prefix+i for i in self.help_categories[None]
						if (not self.commands[i] in self.developer_commands or
						(ctx.author.is_developer and self.commands[i] in self.developer_commands))])
					
				response += f"\n\nUse \"{self.prefix}help (category)\" for detailed usage help."
				
			await ctx.chat.send(response)
		
		
def seconds_to_str(t):
	
	y, r = divmod(t, 31557600)
	month, r = divmod(r, 2629800)
	d, r = divmod(r, 86400)
	h, r = divmod(r, 3600)
	m, s = divmod(r, 60)
	durations = [[int(y),"year"],[int(month),"month"],[int(d),"day"],[int(h),"hour"],[int(m),"minute"],[int(s),"second"]]
	durations = [i for i in durations if i[0]]
	s_durations = []

	for count, i in enumerate(durations):
		if i[0] > 1:
			durations[count][1] += "s"
			
	durations = [str(i[0])+" "+i[1] for i in durations]
	total = ", ".join(durations)

	if t > 0:
		return total
	
	return "1 second"
		
