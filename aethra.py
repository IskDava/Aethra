"""
It is Aethra - TTS and STT bot for telegram..

Classes:
- Markups: Contains all markups for buttons and languages.
- Backend: Contains all backend (TTS and STT) methods.
- Frontend: Contains all frontend (Telegram) methods and commands.
- Frontend.Commands: Contains all commands for the bot.
"""
import edge_tts # Text _> Speech (TTS)
from faster_whisper import WhisperModel # Speech -> Text (STT)
import asyncio # Asyncio for async functions
import telebot # Telegram bot library
from telebot import types # Types for inline keyboard buttons
import json # For reading json files
import os # For making directories and reading environment variables
import dotenv # For reading .env file

dotenv.load_dotenv()
TOKEN = os.getenv("TOKEN")

os.makedirs("temp", exist_ok=True) #* Making temp folder if it doesn't exist

with open("RPV.json", encoding="utf-8") as f:
    RPV = json.load(f) # Rates, pitches and volumes

with open("voices.json", encoding = "utf-8") as f:
    voices = json.load(f) # Voices names and codes

voices_names_male = voices["voices_names_male"]
voices_name_female = voices["voices_names_female"]
rates = RPV["rates"]
pitches = RPV["pitches"]
volumes = RPV["volumes"]

class Markups:
    '''
    All markups for buttons and languages
    '''
    voice_lang_markup = types.InlineKeyboardMarkup(row_width=4) # Language buttons markup

    langs = [ # Valid languages
        ('English (US)', 'en-US'),
        ('Russian', 'ru-RU'),
        ('German', 'de-DE'),
        ('French', 'fr-FR'),
        ('Spanish', 'es-ES'),
        ('Italian', 'it-IT'),
        ('Chinese', 'zh-CN'),
        ('Japanese', 'ja-JP')
    ]

    buttons = [types.InlineKeyboardButton(name, callback_data=code) for name, code in langs] 
    voice_lang_markup.add(*buttons)

    voice_type_markup = types.InlineKeyboardMarkup(row_width=2) # Male/Female buttons

    row = [
        types.InlineKeyboardButton('Male', callback_data='M'),
        types.InlineKeyboardButton('Female', callback_data='F')
        ]

    voice_type_markup.add(*row)
    
    voice_names_male = voices["voices_names_male"]
    voice_names_female = voices["voices_names_female"]

    rate_markup = types.InlineKeyboardMarkup(row_width=2)
    rate_buttons = [types.InlineKeyboardButton(name, callback_data=name) for name in rates]
    rate_markup.add(*rate_buttons)

    pitch_markup = types.InlineKeyboardMarkup(row_width=2)
    pitch_buttons = [types.InlineKeyboardButton(name, callback_data=name) for name in pitches]
    pitch_markup.add(*pitch_buttons)

    volume_markup = types.InlineKeyboardMarkup(row_width=2)
    volume_buttons = [types.InlineKeyboardButton(name, callback_data=name) for name in volumes]
    volume_markup.add(*volume_buttons)

users = {}

class Backend:
    '''
    All backend (TTS and STT itself)
    '''
    async def say(text: str, chat_id) -> str:
        '''
        TTS
        '''
        print("Starting saying...")
        print(f"Lang: {users[chat_id]['language']}\nVoice: {users[chat_id]['voice_type']}") #? Logs
        communicate = edge_tts.Communicate(text=text, voice=users[chat_id]['voice_type'],
                                        rate=users[chat_id]["rate"], pitch=users[chat_id]["pitch"],
                                        volume=users[chat_id]["volume"])
        await communicate.save(users[chat_id]['output_file'])
        print("Ended saying")
        return users[chat_id]['output_file'] # File with speech

    def write(file: str, chat_id) -> str:
        '''
        STT
        '''
        print("Starting writing...") #? Logs
        model = WhisperModel("small", device="cuda", compute_type="float16")
        segments, info = model.transcribe(file, language=users[chat_id]['language'][:2])
        print("Ended writing")
        return ' '.join([segment.text for segment in segments]) #* Output text 

bot = telebot.TeleBot(TOKEN) #! Token

class Frontend:
    '''
    All Frontend (Telegram) happening
    '''
    class Commands:
        '''
        All commands
        '''
        @bot.message_handler(commands=['rate'])
        def set_rate(message):
            '''
            /rate
            '''
            bot.send_message(message.chat.id, "Please send me the rate level:", reply_markup=Markups.rate_markup)

        @bot.message_handler(commands=['pitch'])
        def set_pitch(message):
            '''
            /pitch
            '''
            bot.send_message(message.chat.id, "Please send me the pitch level:", reply_markup=Markups.pitch_markup)

        @bot.message_handler(commands=['volume'])
        def set_volume(message):
            '''
            /volume
            '''
            bot.send_message(message.chat.id, "Please send me the volume level:", reply_markup=Markups.volume_markup)

        @bot.message_handler(commands=['language'])
        def set_language(message):
            '''
            /language
            '''
            bot.send_message(message.chat.id, "Please send me the language code:", reply_markup=Markups.voice_lang_markup)

        @bot.message_handler(commands=['start'])
        def start(message):
            '''
            /start
            '''
            users[message.chat.id] = {'language': 'en-US', 'voice_type': 'en-US-JennyNeural',
                                    'output_file': None, 'rate': rates["default"],
                                    'pitch': pitches["default"], "volume": volumes["default"]} # Default properties
            bot.send_message(message.chat.id, "I'm Aethra, bot for speech recognition and voice-over!"
                            "Send me a voice message and I will transcribe it for you or send me text and I will voice it!")

    @bot.message_handler(content_types=['text', 'audio', 'voice'])
    def handle_message(message):
        '''
        Messages like text, audio and voice sorting to their funcs
        '''
        try:
            if message.content_type == 'text':
                users[message.chat.id]['output_file'] = f"temp\\{message.chat.id}.wav" # Making output path

                file = asyncio.run(Backend.say(message.text, message.chat.id)) 
                bot.send_audio(message.chat.id, open(file, 'rb'), caption="Here is your audio!") # Sending audio

                os.remove(users[message.chat.id]['output_file']) #* Deleting temporary files
            elif message.content_type in ('audio', 'voice'):
                bot.send_message(message.chat.id, "Please, wait. It might take a while...") 

                file_id = (message.voice or message.audio).file_id
                file_info = bot.get_file(file_id)
                downloaded = bot.download_file(file_info.file_path) # Downloading file from telegram servers

                input_path= f'temp\\{message.chat.id}.ogg' # Input path
                with open(input_path, 'wb') as f:
                    f.write(downloaded)

                text = Backend.write(input_path, message.chat.id)
                bot.send_message(message.chat.id, text) # Sending text

                os.remove(input_path) #* Deleting temporary files
        except edge_tts.exceptions.NoAudioReceived:
            bot.send_message(message.chat.id, "Something's wrong with your text. Check your language!") # In case NoAudioReceived Error
        except KeyError:
            bot.send_message(message.chat.id, "Hey! You didn't send /start! I can't work without it!") # In case of no /start command

    @bot.callback_query_handler(func=lambda call: True)
    def button_handler(call):
        '''
        Buttons
        '''
        if call.data in Markups.voice_names_male: # If it is lang
            users[call.message.chat.id]['language'] = call.data
            bot.send_message(call.message.chat.id, "Please choose a voice gender:", reply_markup=Markups.voice_type_markup) # Sending gender properties
        elif call.data in ['M', 'F']: # if it is Male/Female
            if call.data == 'M':
                users[call.message.chat.id]['voice_type'] = \
                    Markups.voice_names_male[users[call.message.chat.id]['language']] # Changing voice type
            elif call.data == 'F':
                users[call.message.chat.id]['voice_type'] = \
                    Markups.voice_names_female[users[call.message.chat.id]['language']]
            bot.send_message(call.message.chat.id, f"Current language is {users[call.message.chat.id]['language']}")
        elif call.data in rates.keys():
            print('Rate changed!')
            users[call.message.chat.id]['rate'] = rates[call.data]
            bot.send_message(call.message.chat.id, f"Current rate is {users[call.message.chat.id]['rate']}")
        elif call.data in pitches.keys():
            users[call.message.chat.id]['pitch'] = pitches[call.data]
            bot.send_message(call.message.chat.id, f"Current pitch is {users[call.message.chat.id]['pitch']}")
        elif call.data in volumes.keys():
            users[call.message.chat.id]['volume'] = volumes[call.data]
            bot.send_message(call.message.chat.id, f"Current volume is {users[call.message.chat.id]['volume']}")

print("Bot started!") #? Logs
bot.polling() #* Main func