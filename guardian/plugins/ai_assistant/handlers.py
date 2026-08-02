"""Handlers untuk plugin ai_assistant."""

import structlog

from guardian.core.bot_gateway import CommandContext
from guardian.core.exceptions import AIProviderError, AIProviderNotConfiguredError
from guardian.plugins.ai_assistant.service import AIAssistantService
from guardian.utils.formatters import escape_html
from guardian.utils.keyboard_builder import nav_row
from telegram import InlineKeyboardMarkup

logger = structlog.get_logger(__name__)


class AIAssistantHandlers:
    """Handlers untuk plugin ai_assistant."""

    def __init__(self, service: AIAssistantService) -> None:
        self.service = service

    async def handle_ask(self, ctx: CommandContext) -> None:
        """Tanya AI Assistant (Gemini 2.5 Flash). Syntax: /ask [pertanyaan] atau /ai [pertanyaan]"""
        if not ctx.args:
            await ctx.bot_gateway.send_message(
                ctx.chat_id,
                "🤖 <b>Serverinka AI Assistant (Gemini 2.5 Flash)</b>\n\n"
                "<b>Penggunaan:</b> <code>/ask [pertanyaan_anda]</code> atau <code>/ai [pertanyaan_anda]</code>\n"
                "<b>Contoh:</b> <code>/ask Bagaimana kondisi RAM dan disk VPS saat ini?</code>",
            )
            return

        user_prompt = " ".join(ctx.args)
        loading_msg = await ctx.bot_gateway.send_message(
            ctx.chat_id, "🧠 <i>Gemini sedang menganalisis VPS & memproses jawaban...</i>"
        )

        try:
            response_text = await self.service.ask_ai(user_prompt)
            formatted_text = f"🤖 <b>Serverinka AI</b>\n\n{response_text}"
            kb = InlineKeyboardMarkup([nav_row(main_menu=True)])

            if loading_msg:
                await ctx.bot_gateway.edit_message(
                    ctx.chat_id, loading_msg.message_id, formatted_text, keyboard=kb
                )
            else:
                await ctx.bot_gateway.send_message(ctx.chat_id, formatted_text, keyboard=kb)

        except (AIProviderNotConfiguredError, AIProviderError) as e:
            error_text = f"❌ <b>AI Assistant Error:</b> {escape_html(e.message)}"
            if loading_msg:
                await ctx.bot_gateway.edit_message(ctx.chat_id, loading_msg.message_id, error_text)
            else:
                await ctx.bot_gateway.send_message(ctx.chat_id, error_text)
        except Exception as e:
            logger.exception("Gagal memproses AI chat.", error=str(e))
            if loading_msg:
                await ctx.bot_gateway.edit_message(
                    ctx.chat_id, loading_msg.message_id, "❌ Terjadi kesalahan pada AI Service."
                )
