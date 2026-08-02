"""Integration tests untuk alur perintah Telegram Bot."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Message, Update, User

from guardian.core.bot_gateway import BotGateway


@pytest.mark.asyncio
async def test_bot_start_command_flow(app_ctx):
    """Test alur perintah /start dari Telegram update."""
    mock_tg_bot = MagicMock()
    mock_tg_bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))

    bot_gateway = BotGateway(bot=mock_tg_bot, ctx=app_ctx)

    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.text = "/start"
    update.message.chat_id = 1001
    update.message.message_id = 50
    update.message.from_user = User(
        id=123456789, is_bot=False, first_name="Super", last_name="Admin", username="superadmin"
    )
    update.callback_query = None

    await bot_gateway.handle_update(update)

    assert mock_tg_bot.send_message.called
    call_args = mock_tg_bot.send_message.call_args
    assert call_args.kwargs.get("chat_id") == 1001 or call_args[0][0] == 1001


@pytest.mark.asyncio
async def test_unauthorized_user_blocked(app_ctx):
    """Test user tidak terdaftar tidak diberi akses."""
    mock_tg_bot = MagicMock()
    mock_tg_bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))

    bot_gateway = BotGateway(bot=mock_tg_bot, ctx=app_ctx)

    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.text = "/status"
    update.message.chat_id = 2002
    update.message.message_id = 51
    update.message.from_user = User(
        id=99999999, is_bot=False, first_name="Intruder", username="intruder"
    )
    update.callback_query = None

    await bot_gateway.handle_update(update)

    assert mock_tg_bot.send_message.called
    call_args = mock_tg_bot.send_message.call_args
    sent_text = call_args.kwargs.get("text", "")
    assert "Akses Ditolak" in sent_text or "User tidak terdaftar" in sent_text
