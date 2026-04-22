@dp.message_created(Command('stats'))
async def cmd_stats(event: MessageCreated):
    chat_id = get_chat_id(event)
    if not chat_id:
        logger.warning("Не удалось получить chat_id в /stats")
        return
    
    try:
        # Используем асинхронные функции
        total = await get_messages_count()
        total_length = await get_messages_total_length()
        avg_len = total_length // total if total else 0
        keywords_count = await get_keywords_count()
        
        stats_text = (
            f"📊 **Статистика**\n\n"
            f"• Сообщений в базе: {total}\n"
            f"• Средняя длина: {avg_len} симв.\n"
            f"• Ключевых слов: {keywords_count}\n"
            f"• Время отправки: {SEND_HOUR:02d}:{SEND_MINUTE:02d}\n"
            f"• Чат: {'активирован' if state.chat_id else 'не активирован'}"
        )
        await bot.send_message(chat_id=chat_id, text=stats_text, parse_mode="markdown")
    except Exception as e:
        logger.error(f"Ошибка в /stats: {e}")
        await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {e}")
