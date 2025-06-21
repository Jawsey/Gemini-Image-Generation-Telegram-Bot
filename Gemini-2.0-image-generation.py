import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
import requests
from typing import Optional
import tempfile

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class GeminiImageBot:
    def __init__(self, telegram_token: str, gemini_api_key: str):
        self.telegram_token = telegram_token
        self.gemini_api_key = gemini_api_key
        
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-preview-image-generation')
        
        self.application = Application.builder().token(self.telegram_token).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("generate", self.generate_image))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_message = """
🎨 Welcome to Gemini 2.0 Flash Preview Image Generator Bot!

I can generate high-quality images using Google's Gemini 2.0 Flash Preview Image Generation model.

Commands:
/start - Show this welcome message
/help - Show detailed help
/generate <prompt> - Generate an image

Or simply send me a text message with your image description!

Example: "A futuristic cityscape at sunset with flying cars"
        """
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_message = """
🔍 How to use this bot:

1. Send /generate followed by your image description
   Example: /generate A majestic dragon flying over mountains

2. Or simply send a message with your prompt
   Example: Beautiful sunset over ocean waves

🎯 Tips for better results:
• Be specific and descriptive
• Mention style (e.g., "photorealistic", "cartoon", "oil painting")
• Include details about lighting, colors, composition
• Specify image orientation if needed

⚡ Powered by Gemini 2.0 Flash Preview Image Generation - Google's specialized image generation model
        """
        await update.message.reply_text(help_message)
    
    async def generate_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Please provide a prompt for image generation.\nExample: /generate A beautiful landscape")
            return
        
        prompt = ' '.join(context.args)
        await self._generate_and_send_image(update, prompt)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        prompt = update.message.text
        await self._generate_and_send_image(update, prompt)
    
    async def _generate_and_send_image(self, update: Update, prompt: str):
        try:
            await update.message.reply_text("🎨 Generating your image... Please wait a moment.")
            
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_output_tokens": 8192,
            }
            
            full_prompt = f"Generate an image: {prompt}"
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                full_prompt,
                generation_config=generation_config
            )
            
            if hasattr(response, '_result') and hasattr(response._result, 'candidates'):
                for candidate in response._result.candidates:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data'):
                                image_data = part.inline_data.data
                                mime_type = part.inline_data.mime_type
                                
                                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                                    temp_file.write(image_data)
                                    temp_file_path = temp_file.name
                                
                                try:
                                    with open(temp_file_path, 'rb') as image_file:
                                        await update.message.reply_photo(
                                            photo=image_file,
                                            caption=f"🎨 Generated image for: {prompt}"
                                        )
                                    return
                                finally:
                                    os.unlink(temp_file_path)
            
            await update.message.reply_text(
                "❌ Sorry, I couldn't generate an image for that prompt. "
                "Please try with a different description."
            )
            
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            await update.message.reply_text(
                "❌ An error occurred while generating the image. "
                "Please try again later or with a different prompt."
            )
    
    def run(self):
        logger.info("Starting Gemini 2.0 Flash Preview Image Generation Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    
    if not telegram_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY environment variable not set")
        return
    
    bot = GeminiImageBot(telegram_token, gemini_api_key)
    bot.run()

if __name__ == '__main__':
    main()