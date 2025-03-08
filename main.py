import requests
import telebot
from telebot import types
import json
import time

# Configuration
TELEGRAM_BOT_TOKEN = "8146539981:AAFDbCokG_NcbXW0EPT31v8CVSJaBl-WWyw"   # Replace with your Telegram bot token
AI_API_KEY = "c149b1d61653460fbda905f47275a5a2"
AI_API_URL = "https://api.aimlapi.com/v1/chat/completions"
AI_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"

# Define available AI personas
AI_PERSONAS = {
    "travel": "You are a travel agent. Be descriptive and helpful with travel recommendations.",
    "chef": "You are a professional chef. Provide detailed cooking advice and recipe recommendations.",
    "tech": "You are a tech support specialist. Help users solve technology problems with clear explanations.",
    "finance": "You are a financial advisor. Provide cautious and educational financial guidance.",
    "writer": "You are a writing assistant. Help improve writing with thoughtful suggestions and edits."
}

# Initialize the bot with parse_mode set to HTML
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# Dictionary to store conversation history and settings for each user
user_data = {}

# Helper function to initialize user data
def initialize_user(user_id, persona="travel"):
    user_data[user_id] = {
        "conversation_history": [
            {
                "role": "system",
                "content": AI_PERSONAS[persona]
            }
        ],
        "current_persona": persona,
        "temperature": 0.7,
        "max_tokens": 256,
        "show_thinking": False
    }

# Helper function to create the main menu keyboard
def get_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💬 Change AI Persona", callback_data="change_persona"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        types.InlineKeyboardButton("📝 View History", callback_data="view_history"),
        types.InlineKeyboardButton("❓ Help", callback_data="help")
    )
    return markup

# Helper function to create the persona selection keyboard
def get_persona_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    for key, value in AI_PERSONAS.items():
        persona_name = key.capitalize()
        markup.add(types.InlineKeyboardButton(f"🤖 {persona_name}", callback_data=f"persona_{key}"))
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main"))
    return markup

# Helper function to create the settings keyboard
def get_settings_menu(user_id):
    user = user_data.get(user_id, {})
    temp = user.get("temperature", 0.7)
    max_tok = user.get("max_tokens", 256)
    show_thinking = "✅" if user.get("show_thinking", False) else "❌"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"🌡️ Temperature: {temp}", callback_data="temp_menu"),
        types.InlineKeyboardButton(f"📏 Max Tokens: {max_tok}", callback_data="tokens_menu"),
        types.InlineKeyboardButton(f"🧠 Show Thinking: {show_thinking}", callback_data="toggle_thinking"),
        types.InlineKeyboardButton("◀️ Back", callback_data="back_to_main")
    )
    return markup

# Helper function for temperature selection menu
def get_temperature_menu():
    markup = types.InlineKeyboardMarkup(row_width=3)
    options = [0.3, 0.5, 0.7, 0.9, 1.0]
    buttons = [types.InlineKeyboardButton(str(temp), callback_data=f"set_temp_{temp}") for temp in options]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_settings"))
    return markup

# Helper function for max tokens selection menu
def get_tokens_menu():
    markup = types.InlineKeyboardMarkup(row_width=3)
    options = [128, 256, 512, 1024]
    buttons = [types.InlineKeyboardButton(str(tokens), callback_data=f"set_tokens_{tokens}") for tokens in options]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="back_to_settings"))
    return markup

@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle the /start command"""
    user_id = message.from_user.id
    
    # Initialize user data
    initialize_user(user_id)
    
    # Welcome message with HTML formatting
    welcome_text = (
        "<b>👋 Welcome to AI Assistant!</b>\n\n"
        "I'm your personal AI assistant powered by advanced language models. "
        "I can help you with various tasks based on my current persona.\n\n"
        "<i>Currently set as: Travel Agent</i>\n\n"
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
        "• /reset - Clear your conversation history\n"
        "• /menu - Show the main menu\n\n"
        "<b>How to Use:</b>\n"
        "Simply type a message to chat with the AI assistant. Your conversation "
        "history is maintained to provide contextual responses.\n\n"
        "<b>Change Settings:</b>\n"
        "Use the menu buttons to change the AI persona, adjust response settings, "
        "or view your conversation history."
    )
    bot.send_message(message.chat.id, help_text, reply_markup=get_main_menu())

@bot.message_handler(commands=['reset'])
def reset_command(message):
    """Handle the /reset command"""
    user_id = message.from_user.id
    
    # Get current persona before reset
    current_persona = "travel"
    if user_id in user_data:
        current_persona = user_data[user_id].get("current_persona", "travel")
    
    # Reinitialize user data
    initialize_user(user_id, current_persona)
    
    bot.send_message(
        message.chat.id,
        "<b>💫 Conversation history has been reset.</b>\n\nWhat would you like to talk about?",
        reply_markup=get_main_menu()
    )

@bot.message_handler(commands=['menu'])
def menu_command(message):
    """Handle the /menu command"""
    bot.send_message(
        message.chat.id,
        "<b>📋 Main Menu</b>\n\nSelect an option:",
        reply_markup=get_main_menu()
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_queries(call):
    """Handle all callback queries from inline keyboards"""
    user_id = call.from_user.id
    
    # Initialize user data if not exists
    if user_id not in user_data:
        initialize_user(user_id)
    
    # Main menu options
    if call.data == "change_persona":
        bot.edit_message_text(
            "<b>🤖 Select AI Persona</b>\n\nChoose the role you want the AI to assume:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_persona_menu()
        )
    
    elif call.data == "settings":
        bot.edit_message_text(
            "<b>⚙️ Settings</b>\n\nAdjust how the AI responds to your messages:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_settings_menu(user_id)
        )
    
    elif call.data == "help":
        help_text = (
            "<b>📚 Help & Commands</b>\n\n"
            "<b>Available Commands:</b>\n"
            "• /start - Initialize or restart the bot\n"
            "• /help - Show this help message\n"
            "• /reset - Clear your conversation history\n"
            "• /menu - Show the main menu\n\n"
            "<b>How to Use:</b>\n"
            "Simply type a message to chat with the AI assistant. Your conversation "
            "history is maintained to provide contextual responses."
        )
        bot.edit_message_text(
            help_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_main_menu()
        )
    
    elif call.data == "view_history":
        # Show a summary of the conversation history
        history = user_data[user_id]["conversation_history"]
        if len(history) <= 1:  # Only system message
            history_text = "<b>📝 Conversation History</b>\n\nNo messages yet."
        else:
            # Format the last 5 exchanges
            history_text = "<b>📝 Recent Conversation</b>\n\n"
            for i, msg in enumerate(history[1:min(11, len(history))]):
                role = "👤 You" if msg["role"] == "user" else "🤖 AI"
                content = msg["content"]
                if len(content) > 50:
                    content = content[:47] + "..."
                history_text += f"{role}: {content}\n\n"
        
        bot.edit_message_text(
            history_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_main_menu()
        )
    
    # Persona selection handling
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
            f"<b>✅ Persona Updated</b>\n\nNow chatting with <b>{persona.capitalize()} AI</b>. Your conversation history has been reset with this new persona.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_main_menu()
        )
    
    # Settings menu handling
    elif call.data == "temp_menu":
        bot.edit_message_text(
            "<b>🌡️ Temperature Setting</b>\n\nLower values make responses more focused and deterministic. Higher values make responses more creative and varied.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_temperature_menu()
        )
    
    elif call.data == "tokens_menu":
        bot.edit_message_text(
            "<b>📏 Max Tokens Setting</b>\n\nThis controls the maximum length of the AI's response. Higher values allow for longer responses.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_tokens_menu()
        )
    
    elif call.data == "toggle_thinking":
        user_data[user_id]["show_thinking"] = not user_data[user_id].get("show_thinking", False)
        bot.edit_message_text(
            "<b>⚙️ Settings</b>\n\nAdjust how the AI responds to your messages:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_settings_menu(user_id)
        )
    
    # Temperature setting handling
    elif call.data.startswith("set_temp_"):
        temp = float(call.data.split("_")[2])
        user_data[user_id]["temperature"] = temp
        bot.edit_message_text(
            f"<b>✅ Temperature Updated</b>\n\nTemperature set to {temp}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_settings_menu(user_id)
        )
    
    # Max tokens setting handling
    elif call.data.startswith("set_tokens_"):
        tokens = int(call.data.split("_")[2])
        user_data[user_id]["max_tokens"] = tokens
        bot.edit_message_text(
            f"<b>✅ Max Tokens Updated</b>\n\nMax tokens set to {tokens}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_settings_menu(user_id)
        )
    
    # Navigation handling
    elif call.data == "back_to_main":
        bot.edit_message_text(
            "<b>📋 Main Menu</b>\n\nSelect an option:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_main_menu()
        )
    
    elif call.data == "back_to_settings":
        bot.edit_message_text(
            "<b>⚙️ Settings</b>\n\nAdjust how the AI responds to your messages:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_settings_menu(user_id)
        )
    
    # Acknowledge the callback query to stop the loading animation
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Handle all text messages"""
    user_id = message.from_user.id
    user_message = message.text
    
    # Initialize user data if not exists
    if user_id not in user_data:
        initialize_user(user_id)
    
    # Add user message to conversation history
    user_data[user_id]["conversation_history"].append({
        "role": "user",
        "content": user_message
    })
    
    # Get current user settings
    temperature = user_data[user_id].get("temperature", 0.7)
    max_tokens = user_data[user_id].get("max_tokens", 256)
    show_thinking = user_data[user_id].get("show_thinking", False)
    current_persona = user_data[user_id].get("current_persona", "travel")
    
    # Show typing indicator
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Show "thinking" message if enabled
    thinking_msg = None
    if show_thinking:
        thinking_msg = bot.send_message(
            message.chat.id,
            "<i>🧠 Thinking...</i>"
        )
    
    try:
        # Prepare API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AI_API_KEY}"
        }
        
        payload = {
            "model": AI_MODEL,
            "messages": user_data[user_id]["conversation_history"],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Show request details if thinking is enabled
        if show_thinking and thinking_msg:
            # Format the API request to show to the user (exclude auth token)
            safe_payload = payload.copy()
            # Truncate message content for display
            safe_payload["messages"] = [
                {
                    "role": msg["role"],
                    "content": msg["content"][:50] + ("..." if len(msg["content"]) > 50 else "")
                }
                for msg in safe_payload["messages"]
            ]
            request_info = f"<b>🔄 API Request:</b>\n<pre>{json.dumps(safe_payload, indent=2)}</pre>"
            bot.edit_message_text(
                request_info,
                message.chat.id,
                thinking_msg.message_id
            )
            time.sleep(1)  # Pause briefly to show the request
        
        # Make API request
        start_time = time.time()
        response = requests.post(AI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        response_time = time.time() - start_time
        
        # Extract AI response
        response_data = response.json()
        ai_message = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        if not ai_message:
            ai_message = "I apologize, but I couldn't generate a response. Please try again."
        
        # Add AI response to conversation history
        user_data[user_id]["conversation_history"].append({
            "role": "assistant",
            "content": ai_message
        })
        
        # Manage conversation history length to avoid token limits
        if len(user_data[user_id]["conversation_history"]) > 10:
            # Keep system message and last 9 messages
            user_data[user_id]["conversation_history"] = [
                user_data[user_id]["conversation_history"][0]
            ] + user_data[user_id]["conversation_history"][-9:]
        
        # Show response metadata if thinking is enabled
        if show_thinking and thinking_msg:
            metadata = (
                f"<b>✅ Response received in {response_time:.2f}s</b>\n\n"
                f"<b>Model:</b> {AI_MODEL}\n"
                f"<b>Persona:</b> {current_persona.capitalize()}\n"
                f"<b>Temperature:</b> {temperature}\n"
                f"<b>Max Tokens:</b> {max_tokens}\n\n"
                f"<i>Generating response...</i>"
            )
            bot.edit_message_text(
                metadata,
                message.chat.id,
                thinking_msg.message_id
            )
            time.sleep(1)  # Brief pause for UI feedback
        
        # Create inline keyboard for quick actions
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate"),
            types.InlineKeyboardButton("📋 Menu", callback_data="show_menu")
        )
        
        # Send the AI response with the quick action buttons
        # Delete thinking message if it exists
        if thinking_msg:
            bot.delete_message(message.chat.id, thinking_msg.message_id)
        
        # Add persona indicator to response
        persona_indicator = f"<i>{current_persona.capitalize()} AI</i>\n\n"
        formatted_response = persona_indicator + ai_message
        
        bot.send_message(
            message.chat.id,
            formatted_response,
            reply_markup=markup
        )
        
    except requests.exceptions.RequestException as e:
        error_message = f"<b>❌ API Request Error</b>\n\n{str(e)[:200]}"
        if thinking_msg:
            bot.edit_message_text(
                error_message,
                message.chat.id,
                thinking_msg.message_id
            )
        else:
            bot.send_message(message.chat.id, error_message)
        print(f"API request error: {e}")
        
    except Exception as e:
        error_message = f"<b>❌ Unexpected Error</b>\n\n{str(e)[:200]}"
        if thinking_msg:
            bot.edit_message_text(
                error_message,
                message.chat.id,
                thinking_msg.message_id
            )
        else:
            bot.send_message(message.chat.id, error_message)
        print(f"Unexpected error: {e}")

# Handle the 'regenerate' callback - regenerate the last AI response
@bot.callback_query_handler(func=lambda call: call.data == "regenerate")
def handle_regenerate(call):
    user_id = call.from_user.id
    
    # Check if user has conversation history
    if user_id not in user_data or len(user_data[user_id]["conversation_history"]) < 2:
        bot.answer_callback_query(call.id, "No previous message to regenerate.")
        return
    
    # Remove the last AI response
    if user_data[user_id]["conversation_history"][-1]["role"] == "assistant":
        user_data[user_id]["conversation_history"].pop()
    
    # If the last message isn't a user message, don't proceed
    if user_data[user_id]["conversation_history"][-1]["role"] != "user":
        bot.answer_callback_query(call.id, "Cannot regenerate at this point.")
        return
    
    # Show regenerating message
    bot.edit_message_text(
        "<i>🔄 Regenerating response...</i>",
        call.message.chat.id,
        call.message.message_id
    )
    
    # Process the last user message again
    try:
        # Get user settings
        temperature = user_data[user_id].get("temperature", 0.7)
        max_tokens = user_data[user_id].get("max_tokens", 256)
        current_persona = user_data[user_id].get("current_persona", "travel")
        
        # Prepare API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AI_API_KEY}"
        }
        
        payload = {
            "model": AI_MODEL,
            "messages": user_data[user_id]["conversation_history"],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Make API request
        response = requests.post(AI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        # Extract AI response
        response_data = response.json()
        ai_message = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        if not ai_message:
            ai_message = "I apologize, but I couldn't generate a response. Please try again."
        
        # Add AI response to conversation history
        user_data[user_id]["conversation_history"].append({
            "role": "assistant",
            "content": ai_message
        })
        
        # Create inline keyboard for quick actions
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate"),
            types.InlineKeyboardButton("📋 Menu", callback_data="show_menu")
        )
        
        # Add persona indicator to response
        persona_indicator = f"<i>{current_persona.capitalize()} AI</i>\n\n"
        formatted_response = persona_indicator + ai_message
        
        # Send the regenerated response
        bot.edit_message_text(
            formatted_response,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
        
    except Exception as e:
        bot.edit_message_text(
            f"<b>❌ Error regenerating response</b>\n\n{str(e)[:200]}",
            call.message.chat.id,
            call.message.message_id
        )
        print(f"Error regenerating: {e}")
    
    bot.answer_callback_query(call.id)

# Handle the 'show_menu' callback
@bot.callback_query_handler(func=lambda call: call.data == "show_menu")
def handle_show_menu(call):
    bot.send_message(
        call.message.chat.id,
        "<b>📋 Main Menu</b>\n\nSelect an option:",
        reply_markup=get_main_menu()
    )
    bot.answer_callback_query(call.id)

# Start the bot
if __name__ == "__main__":
    print("Enhanced AI Bot is running...")
    bot.polling(none_stop=True)
