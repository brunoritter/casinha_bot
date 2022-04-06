from concurrent.futures import process
import logging
from datetime import date
from typing import Dict

import pandas as pd
import requests
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater,
)

import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

(
    WAIT_EXPENSE_TYPE,
    WAIT_EXPENSE_VALUE,
    WAIT_FOR_USER_NAME,
    CONFIRM_INPUT,
    SEND_DATA,
) = range(5)


def facts_to_str(user_data: Dict[str, str]) -> str:
    """Helper function for formatting the gathered user info."""
    facts = [f"{key}: {value}" for key, value in user_data.items()]
    return "\n".join(facts).join(["\n", "\n"])


def gastei_command(update: Update, context: CallbackContext):

    logging.info(f"User '{update.message.chat['first_name']}' sent a '/gastei' command")

    keyboard = [
        ["despesa"],
        ["consumo"],
        ["investimento"],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text(
        "De que tipo foi seu gasto, zé ruela?", reply_markup=reply_markup
    )

    return WAIT_EXPENSE_TYPE


def expense_value(update: Update, context: CallbackContext):
    user_input = update.message.text
    logging.info(f"User '{update.message.chat['first_name']}' has chosen {user_input}")
    context.user_data["tipo"] = user_input
    update.message.reply_text(f"E quanto custou essa brincadeira?")

    return WAIT_EXPENSE_VALUE


def expense_description(update: Update, context: CallbackContext):
    user_input = update.message.text
    context.user_data["valor"] = user_input
    logging.info(
        f"User '{update.message.chat['first_name']}' reported the expense value was: {user_input}"
    )
    # keyboard = [["mercado"], ["aluguel"], ["água"], ["outra coisa"]]
    # reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text(
        "AAHHH TÁ! Gastou isso com quê?!",
        # reply_markup=reply_markup
    )

    return WAIT_FOR_USER_NAME


def buyer_name(update: Updater, context: CallbackContext):
    user_input = update.message.text
    context.user_data["descrição"] = user_input
    logging.info(
        f"User '{update.message.chat['first_name']}' reported the expense description was: {user_input}"
    )

    keyboard = [
        ["Bruno"],
        ["Raissa"],
        ["João"],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text("Quem fez essa compra?", reply_markup=reply_markup)

    return CONFIRM_INPUT


def confirm(update: Updater, context: CallbackContext):
    user_input = update.message.text
    context.user_data["comprador"] = user_input
    logging.info(
        f"User '{update.message.chat['first_name']}' reported the expense buyer was: {user_input}"
    )

    keyboard = [["Sim", "Não"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text(
        f"Confere se as infos estão corretas: \n {facts_to_str(context.user_data)}",
        reply_markup=reply_markup,
    )

    return SEND_DATA


def done(update: Updater, context: CallbackContext):
    update.message.reply_text("Encerrando a conversa. Qqer coisa chama")
    return ConversationHandler.END


def upload_data(update: Updater, context: CallbackContext):
    logging.info(f"User '{update.message.chat['first_name']}' confirmed input data")

    data_dict = {key: value.lower() for key, value in context.user_data.items()}
    form_data = {
        "entry.1798295971": data_dict["tipo"],
        "entry.2027852565": data_dict["valor"],
        "entry.1107780057": data_dict["descrição"],
        "entry.2110430875": data_dict["comprador"],
    }

    response = requests.post(config.forms_url, data=form_data)
    if response.ok:
        logging.info("Data successfully uploaded")
        update.message.reply_text("Registrei a compra. Bjs até a próxima")
    else:
        logging.info("Something went wrong while uploading the data")
        update.message.reply_text(
            "Tive algum problema ao enviar as infos. Pede pra Raissa resolver"
        )
    return ConversationHandler.END


def get_manual_data():
    url_manual_data = f"{config.data_sheet_url}{config.sheet_name_manual}"
    manual_data = pd.read_csv(url_manual_data)
    return manual_data


def get_bot_data():
    url_bot_data = f"{config.data_sheet_url}{config.sheet_name_bot}"
    bot_data = pd.read_csv(url_bot_data)
    return bot_data


def process_manual_data(manual_data):
    manual_data = manual_data[["data", "valor", "pagador"]]
    manual_data["valor"].replace("R\$ ", "", regex=True, inplace=True)
    manual_data["valor"].replace("\.", "", regex=True, inplace=True)
    manual_data["valor"].replace("\,", ".", regex=True, inplace=True)
    manual_data["valor"] = manual_data["valor"].astype(float)
    manual_data["data"] = pd.to_datetime(manual_data["data"], format="%d/%m/%Y")
    manual_data["pagador"].replace("joao", "joão", regex=True, inplace=True)
    return manual_data


def process_bot_data(bot_data):
    bot_data.drop(["Tipo", "Descrição"], axis=1, inplace=True)
    bot_data.rename(
        {"Carimbo de data/hora": "data", "Valor": "valor", "Responsável": "pagador"},
        axis=1,
        inplace=True,
    )
    bot_data["data"].replace(" \d{2}\:\d{2}\:\d{2}", "", regex=True, inplace=True)
    bot_data["data"] = pd.to_datetime(bot_data["data"], format="%d/%m/%Y")
    bot_data["valor"].replace("\,", ".", regex=True, inplace=True)
    bot_data["valor"] = bot_data["valor"].astype(float)
    return bot_data


def get_data():
    manual_data = get_manual_data()
    manual_data = process_manual_data(manual_data)

    bot_data = get_bot_data()
    bot_data = process_bot_data(bot_data)

    all_data = pd.concat([manual_data, bot_data])
    return all_data


def process_args(args):
    month = int(args[0])
    try:
        year = int(args[1])
    except IndexError:
        year = date.today().year
    return month, year


def filter_target_month(data, month, year):
    target_month_data = data[data["data"].dt.month == month]
    target_month_data = target_month_data[target_month_data["data"].dt.year == year]
    return target_month_data


def calculate_total_expenses(target_df):
    total_month = round(target_df["valor"].sum(), 2)
    return total_month


def calculate_payments_breakdown(target_df):
    payments_breakdown = target_df.groupby("pagador").sum("valor")

    payments_done = {}
    for person in ["bruno", "joão", "raissa"]:
        try:
            payments_done[person] = payments_breakdown.loc[person, "valor"]
        except KeyError:
            payments_done[person] = 0

    return payments_done


def calculate_cost_division(total_month):
    cost_division = {}
    cost_division["bruno"] = round(total_month * 0.3642, 2)
    cost_division["joão"] = round(total_month * 0.3642, 2)
    cost_division["raissa"] = round(total_month * 0.2716, 2)

    return cost_division


def calculate_final_balance(cost_division, payments_done):
    final_balance = {
        key: round(cost_division[key] - payments_done[key], 2)
        for key in cost_division.keys()
    }
    return final_balance


def create_fechamento_message(
    month, year, total_month, cost_division, payments_done, final_balance
):
    fechamento_string = f"Gastos totais do mês {month}/{year}: {total_month} \n\nDivisão de gastos:{facts_to_str(cost_division)} \nPagamentos realizados: {facts_to_str(payments_done)} \nSaldo final: {facts_to_str(final_balance)}"
    return fechamento_string


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


def main():
    updater = Updater(token=config.token, use_context=True)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gastei", gastei_command)],
        states={
            WAIT_EXPENSE_TYPE: [
                # MessageHandler(Filters.regex("[\d]+,?\d+"), expense_value)
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex("^(r|R)eset$")),
                    expense_value,
                )
            ],
            WAIT_EXPENSE_VALUE: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex("^(r|R)eset$")),
                    expense_description,
                )
            ],
            WAIT_FOR_USER_NAME: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex("^(r|R)eset$")),
                    buyer_name,
                )
            ],
            CONFIRM_INPUT: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex("^(r|R)eset$")),
                    confirm,
                )
            ],
            SEND_DATA: [
                MessageHandler(
                    Filters.regex("^Sim$")
                    & ~(Filters.command | Filters.regex("^(r|R)eset$")),
                    upload_data,
                )
            ],
        },
        fallbacks=[MessageHandler(Filters.regex("^(r|R)eset$|^Não$"), done)],
    )

    fechamento_handler = CommandHandler("fechamento", fechamento_command)

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(fechamento_handler)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
