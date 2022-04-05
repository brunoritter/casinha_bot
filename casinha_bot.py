import logging
from typing import Dict

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

from config import token, forms_url

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

    response = requests.post(forms_url, data=form_data)
    if response.ok:
        logging.info("Data successfully uploaded")
        update.message.reply_text("Registrei a compra. Bjs até a próxima")
    else:
        logging.info("Something went wrong while uploading the data")
        update.message.reply_text(
            "Tive algum problema ao enviar as infos. Pede pra Raissa resolver"
        )
    return ConversationHandler.END


def main():
    updater = Updater(token=token, use_context=True)
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

    dispatcher.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
