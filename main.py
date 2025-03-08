import requests
import telebot
from telebot import types
import json
import time
import datetime
import pytz
from tenacity import retry, stop_after_attempt, wait_exponential
from ratelimit import limits, sleep_and_retry
import logging
import http.server
import socketserver
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = "8146539981:AAFDbCokG_NcbXW0EPT31v8CVSJaBl-WWyw"
AI_API_KEY = "c149b1d61653460fbda905f47275a5a2"
AI_API_URL = "https://api.aimlapi.com/v1/chat/completions"
AI_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"

# Llama API configuration
LLAMA_API_KEY = "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"
LLAMA_API_URL = "https://api.groq.com/openai/v1/chat/completions"
LLAMA_MODEL = "llama-3.3-70b-versatile"

# Gemini 2.0 Flash API configuration
GEMINI_API_KEY = "AIzaSyDmx3XqFrM4lDNxMM0Zj9GINDU-RHMvPEM"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# User configuration
CURRENT_USER = "Hodako"
UTC_NOW = datetime.datetime.strptime("2025-03-08 08:49:23", "%Y-%m-%d %H:%M:%S")

# Define available AI personas
AI_PERSONAS = {
    "travel": "You are a travel agent. Be descriptive and helpful with travel recommendations.",
    "chef": "You are a professional chef. Provide detailed cooking advice and recipe recommendations.",
    "tech": "You are a tech support specialist. Help users solve technology problems with clear explanations.",
    "finance": "You are a financial advisor. Provide cautious and educational financial guidance.",
    "writer": "You are a writing assistant. Help improve writing with thoughtful suggestions and edits."
}

# Define available AI providers
AI_PROVIDERS = {
    "gpt": {
        "name": "GPT",
        "api_url": AI_API_URL,
        "api_key": AI_API_KEY,
        "model": AI_MODEL
    },
    "llama": {
        "name": "Llama",
        "api_url": LLAMA_API_URL,
        "api_key": LLAMA_API_KEY,
        "model": LLAMA_MODEL
    },
    "gemini": {
        "name": "Gemini",
        "api_url": GEMINI_API_URL,
        "api_key": GEMINI_API_KEY,
        "model": "gemini-2.0-flash"
    }
}

# Initialize the bot with parse_mode set to HTML
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# Dictionary to store conversation history and settings for each user
user_data = {}

def get_current_time():
    """Get current UTC time in formatted string"""
    return UTC_NOW.strftime("%Y-%m-%d %H:%M:%S")

def initialize_user(user_id, persona="travel", provider="llama"):
    """Initialize user data with default settings"""
    logger.info(f"Initializing user data for user_id: {user_id}")
    user_data[user_id] = {
        "conversation_history": [
            {
                "role": "system",
                "content": AI_PERSONAS[persona]
            }
        ],
        "current_persona": persona,
        "current_provider": provider,
        "temperature": 0.7,
        "max_tokens": 256,
        "show_thinking": False,
        "last_activity": get_current_time(),
        "username": CURRENT_USER
    }
    return user_data[user_id]

def get_main_menu():
    """Create the main menu keyboard"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💬 Change AI Persona", callback_data="change_persona"),
        types.InlineKeyboardButton("🔄 Change AI Provider", callback_data="change_provider"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        types.InlineKeyboardButton("📜 View History", callback_data="view_history"),
        types.InlineKeyboardButton("❓ Help", callback_data="help")
    )
    return markup

def get_persona_menu():
    """Create the persona selection keyboard"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    for key in AI_PERSONAS:
        persona_name = key.capitalize()
        markup.add(types.InlineKeyboardButton(f"🤖 {persona_name}", callback_data=f"persona_{key}"))
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main"))
    return markup

def get_provider_menu(user_id):
    """Create the AI provider selection keyboard"""
    user = user_data.get(user_id, {})
    current_provider = user.get("current_provider", "llama")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for key, value in AI_PROVIDERS.items():
        provider_name = value["name"]
        selected = "✅ " if key == current_provider else ""
        markup.add(types.InlineKeyboardButton(f"{selected}{provider_name}", callback_data=f"provider_{key}"))
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main"))
    return markup

def get_settings_menu(user_id):
    """Create the settings keyboard"""
    user = user_data.get(user_id, {})
    temp = user.get("temperature", 0.7)
    max_tok = user.get("max_tokens", 256)
    show_thinking = "✅" if user.get("show_thinking", False) else "❌"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"🌡️ Temperature: {temp}", callback_data="temp_menu"),
        types.InlineKeyboardButton(f"📝 Max Tokens: {max_tok}", callback_data="tokens_menu"),
        types.InlineKeyboardButton(f"🧠 Show Thinking: {show_thinking}", callback_data="toggle_thinking"),
        types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main")
    )
    return markup

@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle the /start command"""
    user_id = message.from_user.id
    initialize_user(user_id)
    
    welcome_text = (
        f"<b>👋 Welcome to AI Assistant!</b>\n\n"
        f"Current User: {CURRENT_USER}\n"
        f"Current Time (UTC): {get_current_time()}\n\n"
        "I'm your personal AI assistant powered by advanced language models. "
        "I can help you with various tasks based on my current persona.\n\n"
        "<i>Currently set as: Travel Agent with Llama AI</i>\n\n"
        "Use the menu below to change settings or get help:"
    )
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=get_main_menu()
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_queries(call):
    """Handle all callback queries from inline keyboards"""
    try:
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        message_id = call.message.message_id

        # Initialize user data if not exists
        if user_id not in user_data:
            initialize_user(user_id)
        
        # Update last activity
        user_data[user_id]["last_activity"] = get_current_time()

        if call.data == "change_persona":
            bot.edit_message_text(
                "<b>🤖 Select AI Persona</b>\n\nChoose the role you want the AI to assume:",
                chat_id, message_id,
                reply_markup=get_persona_menu(),
                parse_mode="HTML"
            )

        elif call.data == "change_provider":
            bot.edit_message_text(
                "<b>🔄 Select AI Provider</b>\n\nChoose the AI provider you want to use:",
                chat_id, message_id,
                reply_markup=get_provider_menu(user_id),
                parse_mode="HTML"
            )

        elif call.data == "settings":
            bot.edit_message_text(
                "<b>⚙️ Settings</b>\n\nAdjust how the AI responds to your messages:",
                chat_id, message_id,
                reply_markup=get_settings_menu(user_id),
                parse_mode="HTML"
            )

        elif call.data == "view_history":
            history = user_data[user_id]["conversation_history"]
            if len(history) <= 1:
                history_text = "<b>📜 Conversation History</b>\n\nNo messages yet."
            else:
                history_text = f"<b>📜 Conversation History</b>\n\nUser: {CURRENT_USER}\nLast Activity: {user_data[user_id]['last_activity']}\n\n"
                for msg in history[-5:]:
                    role = "👤 You" if msg["role"] == "user" else "🤖 AI"
                    content = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
                    history_text += f"{role}: {content}\n\n"
            
            bot.edit_message_text(
                history_text,
                chat_id, message_id,
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )

        elif call.data.startswith("persona_"):
            persona = call.data.split("_")[1]
            user_data[user_id]["current_persona"] = persona
            user_data[user_id]["conversation_history"] = [
                {
                    "role": "system",
                    "content": AI_PERSONAS[persona]
                }
            ]
            
            bot.edit_message_text(
                f"<b>✅ Persona Updated</b>\n\nNow chatting with <b>{persona.capitalize()} AI</b>.\nTime: {get_current_time()}",
                chat_id, message_id,
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )

        elif call.data.startswith("provider_"):
            provider = call.data.split("_")[1]
            user_data[user_id]["current_provider"] = provider
            provider_name = AI_PROVIDERS[provider]["name"]
            
            bot.edit_message_text(
                f"<b>✅ Provider Updated</b>\n\nNow using <b>{provider_name}</b>.\nTime: {get_current_time()}",
                chat_id, message_id,
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )

        elif call.data == "back_to_main":
            bot.edit_message_text(
                "<b>📋 Main Menu</b>\n\nSelect an option:",
                chat_id, message_id,
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )

        # Acknowledge the callback
        bot.answer_callback_query(call.id)

    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        try:
            bot.answer_callback_query(call.id, text="An error occurred")
        except:
            pass

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Handle all text messages"""
    user_id = message.from_user.id
    user_message = message.text
    
    # Initialize user data if not exists
    if user_id not in user_data:
        initialize_user(user_id)
    
    # Update last activity
    user_data[user_id]["last_activity"] = get_current_time()
    
    try:
        # Get current user settings
        settings = user_data[user_id]
        current_provider = settings.get("current_provider", "llama")
        provider_settings = AI_PROVIDERS.get(current_provider, AI_PROVIDERS["llama"])
        
        # Prepare API request
        if current_provider == "gemini":
            api_url = f"{provider_settings['api_url']}?key={provider_settings['api_key']}"
            headers = {"Content-Type": "application/json"}
            
            # Prepare conversation context
            conversation_text = f"Current User: {CURRENT_USER}\nTime: {get_current_time()}\n\n"
            conversation_text += "\n".join([
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in settings["conversation_history"][-5:]
            ])
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"{conversation_text}\n\nUser: {user_message}"
                    }]
                }],
                "generationConfig": {
                    "temperature": settings.get("temperature", 0.7),
                    "maxOutputTokens": settings.get("max_tokens", 256)
                }
            }
        else:
            api_url = provider_settings["api_url"]
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {provider_settings['api_key']}"
            }
            payload = {
                "model": provider_settings["model"],
                "messages": settings["conversation_history"] + [{"role": "user", "content": user_message}],
                "temperature": settings.get("temperature", 0.7),
                "max_tokens": settings.get("max_tokens", 256)
            }
        
        # Make API request
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        
        # Extract response
        if current_provider == "gemini":
            candidates = response_data.get("candidates", [])
            if candidates and candidates[0].get("content", {}).get("parts"):
                ai_message = candidates[0]["content"]["parts"][0].get("text", "")
            else:
                raise Exception("No valid response from Gemini API")
        else:
            ai_message = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Update conversation history
        settings["conversation_history"].append({"role": "user", "content": user_message})
        settings["conversation_history"].append({"role": "assistant", "content": ai_message})
        
        # Format response
        response_text = (
            f"<i>{settings['current_persona'].capitalize()} AI - Powered by {provider_settings['name']}</i>\n"
            f"Time: {get_current_time()}\n\n"
            f"{ai_message}"
        )
        
        # Send response with inline keyboard
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate"),
            types.InlineKeyboardButton("📋 Menu", callback_data="back_to_main")
        )
        
        bot.reply_to(message, response_text, reply_markup=markup)
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        error_text = (
            "<b>❌ Error</b>\n\n"
            f"Time: {get_current_time()}\n"
            f"User: {CURRENT_USER}\n"
            f"Error: {str(e)[:200]}"
        )
        bot.reply_to(message, error_text)

@bot.callback_query_handler(func=lambda call: call.data == "regenerate")
def handle_regenerate(call):
    """Handle regenerate button clicks"""
    try:
        user_id = call.from_user.id
        
        # Check if user has conversation history
        if user_id not in user_data or len(user_data[user_id]["conversation_history"]) < 2:
            bot.answer_callback_query(call.id, "No previous message to regenerate.")
            return
        
        # Update last activity
        user_data[user_id]["last_activity"] = get_current_time()
        
        # Get the last user message
        last_user_message = None
        for msg in reversed(user_data[user_id]["conversation_history"]):
            if msg["role"] == "user":
                last_user_message = msg["content"]
                break
        
        if not last_user_message:
            bot.answer_callback_query(call.id, "No user message found to regenerate.")
            return
        
        # Remove the last AI response
        if user_data[user_id]["conversation_history"][-1]["role"] == "assistant":
            user_data[user_id]["conversation_history"].pop()
        
        # Get current settings
        settings = user_data[user_id]
        current_provider = settings.get("current_provider", "llama")
        provider_settings = AI_PROVIDERS.get(current_provider, AI_PROVIDERS["llama"])
        
        # Show regenerating message
        bot.edit_message_text(
            f"<i>🔄 Regenerating response...</i>\n"
            f"Time: {get_current_time()}\n"
            f"User: {CURRENT_USER}",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Make new API request
        try:
            if current_provider == "gemini":
                api_url = f"{provider_settings['api_url']}?key={provider_settings['api_key']}"
                headers = {"Content-Type": "application/json"}
                
                conversation_text = f"Current User: {CURRENT_USER}\nTime: {get_current_time()}\n\n"
                conversation_text += "\n".join([
                    f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                    for msg in settings["conversation_history"][-5:]
                ])
                
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": f"{conversation_text}\n\nUser: {last_user_message}"
                        }]
                    }],
                    "generationConfig": {
                        "temperature": settings.get("temperature", 0.7),
                        "maxOutputTokens": settings.get("max_tokens", 256)
                    }
                }
            else:
                api_url = provider_settings["api_url"]
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {provider_settings['api_key']}"
                }
                payload = {
                    "model": provider_settings["model"],
                    "messages": settings["conversation_history"] + [{"role": "user", "content": last_user_message}],
                    "temperature": settings.get("temperature", 0.7),
                    "max_tokens": settings.get("max_tokens", 256)
                }
            
            # Make API request
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
            
            # Extract response
            if current_provider == "gemini":
                candidates = response_data.get("candidates", [])
                if candidates and candidates[0].get("content", {}).get("parts"):
                    ai_message = candidates[0]["content"]["parts"][0].get("text", "")
                else:
                    raise Exception("No valid response from Gemini API")
            else:
                ai_message = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Update conversation history
            settings["conversation_history"].append({"role": "assistant", "content": ai_message})
            
            # Format response
            response_text = (
                f"<i>{settings['current_persona'].capitalize()} AI - Powered by {provider_settings['name']}</i>\n"
                f"Time: {get_current_time()}\n"
                f"User: {CURRENT_USER}\n\n"
                f"{ai_message}"
            )
            
            # Update message with new response
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate"),
                types.InlineKeyboardButton("📋 Menu", callback_data="back_to_main")
            )
            
            bot.edit_message_text(
                response_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="HTML"
            )
            
        except Exception as e:
            error_text = (
                "<b>❌ Error Regenerating Response</b>\n\n"
                f"Time: {get_current_time()}\n"
                f"User: {CURRENT_USER}\n"
                f"Error: {str(e)[:200]}"
            )
            bot.edit_message_text(
                error_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML"
            )
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Error in regenerate handler: {e}")
        bot.answer_callback_query(call.id, text="Error occurred while regenerating response")

# Custom request handler for the HTTP server
class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        response = (
            f"<h1>AI Bot Status</h1>"
            f"<p>Current Time (UTC): {get_current_time()}</p>"
            f"<p>Current User: {CURRENT_USER}</p>"
            f"<p>Active Users: {len(user_data)}</p>"
        )
        self.wfile.write(response.encode())

def run_http_server():
    """Run HTTP server on port 8765"""
    with socketserver.TCPServer(("", 8765), RequestHandler) as httpd:
        logger.info(f"Server running on port 8765 - Current Time (UTC): {get_current_time()}")
        httpd.serve_forever()

def cleanup_old_sessions():
    """Cleanup inactive user sessions older than 1 hour"""
    while True:
        try:
            current_time = datetime.datetime.strptime(get_current_time(), "%Y-%m-%d %H:%M:%S")
            for user_id in list(user_data.keys()):
                last_activity = datetime.datetime.strptime(
                    user_data[user_id]["last_activity"],
                    "%Y-%m-%d %H:%M:%S"
                )
                if (current_time - last_activity).total_seconds() > 3600:  # 1 hour
                    del user_data[user_id]
                    logger.info(f"Cleaned up inactive session for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")
        time.sleep(300)  # Run every 5 minutes

def main():
    """Main function to run the bot"""
    try:
        # Delete webhook before starting polling
        bot.delete_webhook()
        
        # Start HTTP server in a separate thread
        server_thread = threading.Thread(target=run_http_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=cleanup_old_sessions)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        logger.info(f"Enhanced AI Bot started - Current Time (UTC): {get_current_time()}")
        logger.info(f"Current User: {CURRENT_USER}")
        
        # Start bot polling in infinite loop
        while True:
            try:
                bot.infinity_polling(timeout=60, long_polling_timeout=60)
            except Exception as e:
                logger.error(f"Bot polling error: {str(e)}")
                time.sleep(15)
    except Exception as e:
        logger.error(f"Critical error in main: {str(e)}")

if __name__ == "__main__":
    main()
