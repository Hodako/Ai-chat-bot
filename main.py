import requests
import telebot
from telebot import types
import json
import time
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
        "show_thinking": False
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

@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle the /start command"""
    user_id = message.from_user.id
    initialize_user(user_id)
    
    welcome_text = (
        "<b>👋 Welcome to AI Assistant!</b>\n\n"
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

@bot.message_handler(commands=['help'])
def help_command(message):
    """Handle the /help command"""
    help_text = (
        "<b>📚 Help & Commands</b>\n\n"
        "<b>Available Commands:</b>\n"
        "• /start - Initialize or restart the bot\n"
        "• /help - Show this help message\n"
        "• /menu - Show the main menu\n"
        "• /provider - Change AI provider\n"
        "• /persona - Change AI persona\n\n"
        "<b>How to Use:</b>\n"
        "Simply type a message to chat with the AI assistant."
    )
    bot.send_message(message.chat.id, help_text, reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Handle all text messages"""
    user_id = message.from_user.id
    user_message = message.text
    
    # Initialize user data if not exists
    if user_id not in user_data:
        initialize_user(user_id)
    
    try:
        # Get current user settings
        settings = user_data[user_id]
        current_provider = settings.get("current_provider", "llama")
        provider_settings = AI_PROVIDERS.get(current_provider, AI_PROVIDERS["llama"])
        
        # Prepare base URL for Gemini
        api_url = provider_settings["api_url"]
        if current_provider == "gemini":
            api_url = f"{api_url}?key={provider_settings['api_key']}"
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json"
        }
        if current_provider != "gemini":
            headers["Authorization"] = f"Bearer {provider_settings['api_key']}"
        
        # Prepare payload based on provider
        if current_provider == "gemini":
            payload = {
                "contents": [{
                    "parts": [{
                        "text": user_message
                    }]
                }],
                "generationConfig": {
                    "temperature": settings.get("temperature", 0.7),
                    "maxOutputTokens": settings.get("max_tokens", 256)
                }
            }
        else:
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
        
        # Extract response based on provider
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
        
        # Send response
        bot.reply_to(
            message,
            f"<i>{settings['current_persona'].capitalize()} AI - Powered by {provider_settings['name']}</i>\n\n{ai_message}"
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        bot.reply_to(message, f"<b>❌ Error</b>\n\n{str(e)[:200]}")

# Custom request handler for the HTTP server
class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"AI Bot is running")

def run_http_server():
    """Run HTTP server on port 8765"""
    with socketserver.TCPServer(("", 8765), RequestHandler) as httpd:
        logger.info("Server running on port 8765")
        httpd.serve_forever()

def main():
    """Main function to run the bot"""
    # Start HTTP server in a separate thread
    server_thread = threading.Thread(target=run_http_server)
    server_thread.daemon = True
    server_thread.start()
    
    logger.info("Enhanced AI Bot with GPT, Llama, and Gemini support is running...")
    
    # Start bot polling in infinite loop
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logger.error(f"Bot polling error: {str(e)}")
            time.sleep(15)

if __name__ == "__main__":
    main()
