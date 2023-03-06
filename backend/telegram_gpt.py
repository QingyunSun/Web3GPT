import openai
import pymongo 
openai.api_key = ''
import logging
import time
from telegram import __version__ as TG_VER
import pandas as pd
try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ForceReply, Update,InlineKeyboardButton, InlineKeyboardMarkup,ReplyKeyboardRemove, Update,constants, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters,CallbackQueryHandler,ConversationHandler
from telegram.ext.filters import BaseFilter
from telegram import Bot


import json 
import requests
from pybit import HTTP

bot = Bot()
# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

##you need this in a ipython notebook 
# import nest_asyncio
# nest_asyncio.apply()

from functools import wraps
def correct_encoding(dictionary):
    """Correct the encoding of python dictionaries so they can be encoded to mongodb
    inputs
    -------
    dictionary : dictionary instance to add as document
    output
    -------
    new : new dictionary with (hopefully) corrected encodings"""

    new = {}
    for key1, val1 in dictionary.items():
        # Nested dictionaries
        if isinstance(val1, dict):
            val1 = correct_encoding(val1)

        if isinstance(val1, np.bool_):
            val1 = bool(val1)

        if isinstance(val1, np.int64):
            val1 = int(val1)
            
        if isinstance(val1, np.int32):
            val1 = int(val1)

        if isinstance(val1, np.float64):
            val1 = float(val1)
        
        if isinstance(val1, np.float32):
            val1 = float(val1)

        new[key1] = val1

    return new

def gpt_reply(prompt:str,model_engine="text-davinci-003",**kwargs) -> None: 
# Set up the model and prompt
    # Generate a response
    completion = openai.Completion.create(
        engine=model_engine,
        prompt=prompt,
        max_tokens=2048,
        n=1,
        stop=None,
        temperature=0.5,
    )

    response = completion.choices[0].text
    # print(response)
    return response


def reply_gpt_turbo(messages):
    completion = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    stop=None,
    temperature=0.5,
    messages=messages
    )
    return completion["choices"][0]["message"]["content"]

import pymongo

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = myclient["web3gpt"]

def get_chats_in_db():
    mongo_db_chats = list(mongo_db.list_collection_names())
    return mongo_db_chats
get_chats_in_db()

def delete_chat(acct_name):
    mongo_db[acct_name].delete_many({})
    print('deleted chat history',acct_name)
# delete_chat(acct_name='bj')


def pull_chat_hist(acct_name):
    #pulls from the top most recent entrys..drop the id
    data = list(mongo_db[acct_name].find({},{'role':1,'content':1,'_id':0}).limit(15))
    return data

# chat_hist = pull_chat_hist('bjaggars')
# [{"role": "system", "content": "You are a helpful assistant."}] + chat_hist


def get_prices(symbol):
    session = HTTP('https://api.bybit.com')
    return (session.latest_information_for_symbol(symbol=symbol))['result'][0]
def send_order(symbol,tgt_exposure,acct_name='BILL_TRADER'):
    data={
    "message":"telegram_gpt_chat",# database recording.
    "algo_name":"BILL_TRADER_"+symbol,# needed to spesify what algo
    "symbol":symbol,# NO SLASHES ! use bybit symbol list only eg,BTCUSD,BTCUSDT,ETHUSD,XRPUSD,EOSUSD
    "tgt_exposure":round(float(tgt_exposure),4), # 1 = 100% so make sure u scale correctly. 1=nat long , 0 = cash , -1 = 1x short
    "expo_type":"SET_TO",# only SET_TO is allowed
    "max_expo":2.1,# the limit that will safe gard you if tgt expo is too high
    "tgt_price":float(get_prices(symbol=symbol)['last_price']),#MKT to use the current mkt price or type price manualy 
    "order_side":"buy",# this dose not matter... 
    "order_type":"LIMIT",# by default every trade is limit only for now
    "trade_auth":"True",# If false, it will submit order but will not trade, if true it will have the ability to trade your acct.
    "order_text":"telegram_gpt_chat!",# Used to store msg within the data base and to telegram. 
    "authToken":"43aa4e041d4acae895b44ddc0b74b816122b2e7b4908a6ad2876fd2ab6409202" # needed to auth order text to server.
    }

    headers = {'content-type': 'application/json'}
    json_data = json.dumps(data)
    res = requests.post('https://monkey-trader.com/devtest/ALGO_PORT_03',headers=headers, data=json_data,timeout=None)
    print(res)



####
#global keybords
# reply_markup_remove = ReplyKeyboardRemove()
keyboard = [
        [
            InlineKeyboardButton("START_GPT", callback_data="START_GPT"),
            InlineKeyboardButton("PLACE_TRADE", callback_data="1"),
            InlineKeyboardButton("EDIT/VIEW TRADES", callback_data="2"),
        ],
        [InlineKeyboardButton("GET NEWS", callback_data="NEWS_GPT")],
    ]

# menu_keyboard = [['PLACE_TRADE'],['GET_OPEN_TRADES','CANCEL_TRADES'],['BALLANCES']]
reply_menu_keyboard = InlineKeyboardMarkup(keyboard)
force_reply = ForceReply()

# Stages
START_ROUTES,GPT_CONVO,SYMBOL_CHOICE,PRE_TRADE_EXECUTION,TRADE_EXECUTION ,RETURN_NEWS,END_ROUTES = range(7)
# Callback data
ONE, TWO, THREE, FOUR = range(4)
START_GPT = 'START_GPT'
NEWS_GPT = 'NEWS_GPT'
# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    # Get user that sent /start and log his name
    user = update.effective_user
    await bot.send_photo(chat_id=update.message.chat.id, photo=open('web3gpt_1.jpg', 'rb'))
    msg = "HI "+str(user.first_name)+'\n'+'Main Menu. Press a button to continue.'+"\n"
    await update.message.reply_text(msg,reply_markup=reply_menu_keyboard)
    delete_chat(acct_name=user.username)
    
    return START_ROUTES


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("HERES A MENUE OF COMMANDS",reply_markup=reply_menu_keyboard)


async def start_over(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    """Prompt same text & keyboard as `start` does but not as new message"""
    # Get CallbackQuery from Update
    query = update.callback_query
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data=str(ONE)),
            InlineKeyboardButton("2", callback_data=str(TWO)),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Instad of sending a new message, edit the message that
    # originated the CallbackQuery. This gives the feeling of an
    # interactive menu.
    await query.edit_message_text(text="Start handler, Choose a route", reply_markup=reply_markup)
    return START_ROUTES

async def gpt_intro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # """Show new choice of buttons"""
    print('HERE1')
    query = update.callback_query
    print(update.message)
    await query.answer()
    print('HERE2')
    await bot.send_message(query.message.chat.id,text='Ok let me start the gpt bot for you.. the bot will intoduce itself when ready..')
    await bot.send_chat_action(query.message.chat.id,action=constants.ChatAction(value='typing'))
    # await query.message.reply_chat_action(constants.ChatAction(value='typing'),query.message.chat.id)
    # gpt_text = 'test'

    gpt_text = gpt_reply(prompt='First say Welcome to use Web3GPT.ai '+'In a line below make 2 sentences, introduce yourself as Web3GPT AI then say how knowledgeable you are in the cryptocurrency industry. After that ask what can I help you with')
    print('HERE3')
    print(query)
    # print(update)
    await bot.send_message(query.message.chat.id,text=gpt_text,reply_markup=ForceReply())
    # await query.message.reply_text(gpt_text)
    return GPT_CONVO


async def gpt_convo(update: Update, context: ContextTypes.DEFAULT_TYPE)->None:
    message = update.message
    
    # query = update.callback_query
    # await query.answer()
    
    print('parsing here below \n \n')
    
    print(message.to_dict())
    message_id = message.message_id
    # print('\n')
    # print(message.to_json())
    simple_msg = {
        'message_id':message_id,
        'username':message.from_user.username,
        'role':'user',
        'content':message.text,
    }

    if message.text and message.from_user.is_bot:
        # Handle the text reply from the bot here
        print(f"Received text reply from bot: {message.text}")
        q = {'message_id':message.message_id}
        data = {"$set":correct_encoding(message.to_dict())}
        
        mongo_db[user_name].update_one(q,data,upsert=True)
    else:
        user_name = message.from_user.username
        
        print(user_name,'\n')# if user_name in ['bjaggars','brendan']:
        print(f"Received reply from user: {message.text}")
        if (message.text.find('place trade'))>0:
            await set_symbol(update,context)
            pass
        #store the client message    
        # q = {'message_id':message.message_id,'username':user_name}
        # data = {"$set":simple_msg}
        mongo_db[user_name].insert_one(simple_msg)

        # await bot.send_message(message.chat.id,text='Ok '+user_name+' one sec')
        #respond to the client prompt using gpt
        
        # gpt_text = gpt_reply(prompt=str(message.text))
        chat_hist = pull_chat_hist(acct_name=user_name)#i ommit the '_id, message_id and the username. only role and content is reuturned
        await bot.send_chat_action(message.chat.id,action=constants.ChatAction(value='typing'))
        print(chat_hist)
        if len(chat_hist)==1:
            chat_hist = [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {'role':'user','content':message.text},
                ]

        gpt_text = reply_gpt_turbo(messages=chat_hist)
        #store the reply in the dict msg payload
        simple_msg_2 = {
        'message_id':message_id,
        'username':'web3gpt',
        'role':'assistant',
        'content':gpt_text,
        }
        
        #update the the siple meg obj with the bots reply it in the db under the same message id
        # q = {'message_id':message.message_id,'username':user_name}
        # data = {"$set":simple_msg}

        mongo_db[user_name].insert_one(simple_msg_2)
        #send the gpt reply to the client.
        await bot.send_message(message.chat.id,text=gpt_text,reply_markup=ForceReply())

    return GPT_CONVO

async def set_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sow new choice of buttons"""
    query = update.callback_query
    print(query)
    print('two \n', query.message.text)
    reply_keyboard = [
    ["BTCUSDT", "ETHUSDT"],
    ["LTCUSDT",'UNIUSDT'],
    ["BACK"],
    ]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    await bot.send_message(query.message.chat.id,text='SELECT A TRADING PAIR',reply_markup=reply_markup)
    return SYMBOL_CHOICE

async def set_tgt_exposure(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons. This is the end point of the conversation."""
    print('set_tgt_exposure \n', update)

    mongo_db[update.message.from_user.username]['trade'].drop({})
    data = {'tgt_exposure':'','symbol':update.message.text,'trade_auth':False}
    mongo_db[update.message.from_user.username]['trade'].insert_one(data)
    await bot.send_message(update.message.chat.id,text=f"Selected option: "+update.message.text)
    reply_keyboard = [
    ["1","0.5","0.25"],
    ["CLOSE"],
    ["-1","-0.5","-0.25"],
    ]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    await bot.send_message(update.message.chat.id,text='SELECT A TARGET EXPOSURE\nPOSIVE NUMBER MEANS LONG\nNEGITIVE MEANS SHORT\n AND 0 MEANS CLOSE THE POSISTION',reply_markup=reply_markup)
    return PRE_TRADE_EXECUTION


async def pre_trade_excecution(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons. This is the end point of the conversation."""
    print('pre_trade_excecution \n', update)
    trade = list(mongo_db[update.message.from_user.username]['trade'].find().limit(1))[0]
    working=True
    if update.message.text=='CLOSE':
        trade['tgt_exposure'] = 0
    elif isinstance(float(update.message.text),float):
        trade['tgt_exposure'] = update.message.text
    else:
        working = False
        await bot.send_message(update.message.chat.id,text=f"ERROR USER SENT IN SOMTHING NOT USABLE: "+update.message.text)
    assert working==True , 'user sent in somthing not usable for the tgt exposure'
    data = {"$set":{"tgt_exposure":update.message.text}}
    mongo_db[update.message.from_user.username]['trade'].update_one({'symbol':trade['symbol']},data)
    await bot.send_message(update.message.chat.id,text=f"Selected option: "+update.message.text)
    reply_keyboard = [
    ["CONFIRM_AND_SEND"],
    ["EXIT"],
    ]
    
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    await bot.send_message(update.message.chat.id,text='Confirm trade',reply_markup=reply_markup)
    return TRADE_EXECUTION


async def trade_excecution(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons. This is the end point of the conversation."""
    print('trade_excecution \n', update)
    trade = list(mongo_db[update.message.from_user.username]['trade'].find().limit(1))[0]
    if update.message.text == 'CONFIRM_AND_SEND':
        trade['trade_auth'] = True
        if trade['tgt_exposure']=='CLOSE':
            trade['tgt_exposure']=0
        await bot.send_message(update.message.chat.id,text=
                'SYMBOL: '+trade['symbol']+"\n"+
                'tgt exposure: '+str(trade['tgt_exposure'])+"\n"+
                'TRADE AUTH: '+str(trade['trade_auth'])+"\n"
            ,reply_markup=ReplyKeyboardRemove())
            #send a requrst to my monkey trader server
        send_order(symbol=trade['symbol'],tgt_exposure=trade['tgt_exposure'],acct_name='BILL_TRADER')
        await bot.send_animation(chat_id = update.message.chat.id, animation ='https://media.giphy.com/media/aNbGyHcDYphNbhe4EE/giphy.gif')
    else:
        await bot.send_message(update.message.chat.id,text='SYSTEM EXIT NO TRADE PLACED',reply_markup=ReplyKeyboardRemove())
    #update the payload in mongo db you should have symbol, tgt expo, and trade auth all filled out.
    data = {"$set":{"trade_auth":trade['trade_auth']}}
    mongo_db[update.message.from_user.username]['trade'].update_one({'symbol':trade['symbol']},data)

    return TRADE_EXECUTION


async def get_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons. This is the end point of the conversation."""
    print('get_news \n', update)
    query = update.callback_query
    await bot.send_message(query.message.chat.id,text='Hi im your News bot. Reply to me your query',reply_markup=ForceReply())
    # await bot.send_message(update.message.chat.id,text='',reply_markup=ReplyKeyboardRemove())
    return RETURN_NEWS

async def return_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons. This is the end point of the conversation."""
    print('RETURN news 2 \n', update)
    message = update.message

    headers = {
        'Content-Type': 'application/json'
        }

    query=message.text
    response = requests.get(url='https://web3gpt-3eil.onrender.com/query=' + query, headers=headers)
    print (response)
    dictio = json.loads(response.text)
    await bot.send_message(update.message.chat.id,text=dictio['response'],reply_markup=ForceReply())
    return RETURN_NEWS

class UsdtFilter(BaseFilter):
    def filter(self, message):
        matches = re.findall(r'\b\w*USDT\b', message.text)
        return bool(matches)


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token().build()
    # on different commands - answer in Telegram
    # application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    usdt_filter = UsdtFilter()
    # application.add_handler(CallbackQueryHandler(button))#keyboard reply 

    # Setup conversation handler with the states FIRST and SECOND
    # Use the pattern parameter to pass CallbackQueries with specific
    # data pattern to the corresponding handlers.
    # ^ means "start of line/string"
    # $ means "end of line/string"
    # So ^ABC$ will only allow 'ABC'
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START_ROUTES: [
                CallbackQueryHandler(gpt_intro, pattern="^" + str(START_GPT) + "$"),
                CallbackQueryHandler(set_symbol,pattern="^" + str(TWO) + "$"),
                CallbackQueryHandler(get_news,pattern="^" + str(NEWS_GPT) + "$"),
            ],
            GPT_CONVO:[MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_convo)],
            SYMBOL_CHOICE: [MessageHandler(usdt_filter,set_tgt_exposure)],
            PRE_TRADE_EXECUTION:[MessageHandler(filters.Regex("^(1|0.5|0.25|CLOSE|-0.25|-0.5|-1)$"), pre_trade_excecution)],
            TRADE_EXECUTION:[MessageHandler(filters.Regex("^(CONFIRM_AND_SEND|EXIT)$"), trade_excecution)],
            RETURN_NEWS:[MessageHandler(filters.TEXT & ~filters.COMMAND, return_news)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    # Add ConversationHandler to application that will be used for handling updates
    application.add_handler(conv_handler)
    # Create a MessageHandler object with the handle_message function and add it to the Updater
    # message_handler = MessageHandler(filters.TEXT, gpt_convo)
    # application.add_handler(message_handler)
    # # on non command i.e message - echo the message on Telegram
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()