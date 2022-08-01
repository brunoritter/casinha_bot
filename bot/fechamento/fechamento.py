import logging

from telegram.ext import CallbackContext, Updater

from utils import *


def fechamento_command(update: Updater, context: CallbackContext):
    logging.info(
        f"User '{update.message.chat['first_name']}' sent a '/fechamento' command"
    )

    df = get_data()
    month, year = process_args(context.args)
    target_df = filter_target_month(df, month, year)
    total_month = calculate_total_expenses(target_df)
    payments_breakdown = calculate_payments_breakdown(target_df)
    cost_division = calculate_cost_division(total_month)
    final_balance = calculate_final_balance(cost_division, payments_breakdown)
    message_text = create_fechamento_message(
        month, year, total_month, cost_division, payments_breakdown, final_balance
    )

    context.bot.send_message(chat_id=update.effective_chat.id, text=message_text)
