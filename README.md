# ifunny.chat-bot-wrapper
Python implementation of the ifunny.chat website for bots

## Usage:
1. clone the repository to your disk
2. pip install -r requirements.txt
3. put your data into bot.py
4. python3 bot.py

### You will need an api key to run this
- Get one from egg#3897 on Discord

---

You will need to put your account email and password, as well as region which can be either `United States` or `Brazil`, and pick a prefix that others don't use, into the `bot.py` file.

Use the latest version of python (specifically >= 3.8)

---

## bot.command() decorator usage

The command decorator is used to tell the bot what functions are commands. It takes several optional kwargs. 

- By default, the name of the function acts as the name of the command. This can be overridden with the kwarg: `name = "..."` where the string will replace the function name as the invocable command. It may include numbers or special characters that may not be permitted in a function name for example.
- The *aliases* kwarg takes a list of strings which can be used as additional command names. This means the same command may be called by multiple other names. `aliases = ["...", "...."]`.
- The bot comes with a built-in `{prefix}help` command. The following points discuss this. If you include a docstring in the command function, it will be used by the bot as the command's help message string when you call `{prefix}help {command name}`. The docstring help message may be replaced by the kwarg: `help_message = "..."`.
- You can specify the command category within the help message with the kwarg: `help_category = "..."`. The category can be anything. Multiple commands with the same category will be grouped.
- If you wish to exclude a command from the help message, use `hide_help = True`.
- Finally, if the `bot.developer` variable has been set, the user with the matching id will be able to execute commands that have the kwarg `developer = True` and nobody else will.

## bot.event() decorator usage

The event decorator is optional and it takes no args or kwargs. Functions with this decorator will be invoked when the respective "event" occurs within a chat. The functions with these decorators can only have the following names: `user_join, user_leave, user_kick, channel_change, on_join, on_message, on_file`. As you can tell by the names, when the bot detects such an event, those functions will be executed. If you have no need for the bot to do something on a certain event, there is no need to have the function. Again, these callbacks are optional.

## ctx object

The ctx object passed in to the commands and events is similar to the discord.py ctx. Its attributes include `bot, chat, message, author, user, inviter` bot is the instance of the bot, chat is the chat object which contains several functions and attributes, message is a message object which contains message related attributes. Author, user, and inviter are all user objects and they are used in commands, chat events, and invitations respectively. Invitations are handled internally so the inviter attribute will probably not be used.

The chat, user, and message objects each contain an equality operator `==`. Additionally, the chat object contains the following async functions: `send, upload, members, has_member, invite`, and the user object has `send, upload`. If you want to see what other attributes each object has, just `print(dir({the_object}))` on it; they are too numerous to describe.

## async ctx.chat.input() function

Use this to grab non-command messages (or files or both) within an active command. There is an example of this function in bot.py. You can use this as a one-liner to grab the next immediate message someone sends in the chat or use it in a loop to accept many responses (you are responsible for breaking the loop). Additionally, input() takes two optional arguments: `type` and `timeout`. If left blank, `type` defaults to `Message` and `timeout` defaults to `None`. For `type` you can specify `iFunny.Message`, `iFunny.File`, or, `any` for either.

### TODO

Need to add blacklisting functionality. Might consider adding built-in user data file support
