# Web3GPT

## Product Demo:


1) Web version (with Wallet Connect integration): 
https://web3gpt.ai/ 

2) Telegram chatbot version (connected with Bybit, can place order for my Bybit account with USDT perp futures): 
Chatbot name on Telegram:
@Web3GPTbot

To test in a official telegram group chat:
https://t.me/+EJyJ6BUjrrc1MDdl



## Development demo:
# Setup
Make sure you have your OpenAI API Key in the `.env` file.

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

# Run Locally (Backend API)
To run the backend locally, please do this in a terminal
```bash
cd backend
uvicorn api:app --host 0.0.0.0 --port 8080
```
The API can then be accessed at
```
http://0.0.0.0:8080
```
API docs is at
```
http://0.0.0.0:8080/docs
```

## Public URL Tunnel (ngrok)
To tunnel to a public URL, please first setup [ngrok](https://ngrok.com/), then run in another terminal:
```bash
ngrok http 8080
```

The terminal will then show something like:
```bash
ngrok                                                           (Ctrl+C to quit)
                                                                                
We added a plan for ngrok hobbyists @ https://ngrok.com/personal                
                                                                                
Session Status                online                                            
Account                       Hanchung Lee (Plan: Free)                         
Version                       3.1.1                                             
Region                        United States (us)                                
Latency                       74ms                                              
Web Interface                 http://127.0.0.1:4040                             
Forwarding                    https://03dd-99-44-171-191.ngrok.io -> http://locahost:8080
                                                                                
Connections                   ttl     opn     rt1     rt5     p50     p90       
                              0       0       0.00    0.00    0.00    0.00      
```
The API in this example will be at
```
https://03dd-99-44-171-191.ngrok.io
```
