import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
)
from datetime import datetime
import json
import os

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot states
SELECT_LANG, MAIN_MENU, CATEGORIES, PRODUCTS, CART, ABOUT = range(6)
ADMIN, ADD_CATEGORY, ADD_PRODUCT = range(3, 6)

# Admin ID - o'zingizning Telegram IDingizni qo'ying
ADMIN_ID =  7877153414 # Bu yerga o'zingizning IDingizni yozing

# Data files
USERS_FILE = 'users.json'
PRODUCTS_FILE = 'products.json'
CARTS_FILE = 'carts.json'

# Initialize data files if they don't exist
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({}, f)

if not os.path.exists(PRODUCTS_FILE):
    with open(PRODUCTS_FILE, 'w') as f:
        json.dump({"categories": {}, "products": {}}, f)

if not os.path.exists(CARTS_FILE):
    with open(CARTS_FILE, 'w') as f:
        json.dump({}, f)

def load_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def save_data(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# Start command
def start(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)
    users = load_data(USERS_FILE)
    
    # Check if user exists
    if user_id not in users:
        users[user_id] = {
            "lang": None,
            "cart": []
        }
        save_data(users, USERS_FILE)
    
    # Check if admin
    if update.effective_user.id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data='lang_uz')],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')],
            [InlineKeyboardButton("👑 Admin", callback_data='admin')]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data='lang_uz')],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "Tilni tanlang / Выберите язык:",
        reply_markup=reply_markup
    )
    
    return SELECT_LANG

# Language selection
def select_lang(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    users = load_data(USERS_FILE)
    
    if query.data == 'lang_uz':
        users[user_id]['lang'] = 'uz'
        text = "O'zbek tili tanlandi."
    elif query.data == 'lang_ru':
        users[user_id]['lang'] = 'ru'
        text = "Выбран русский язык."
    elif query.data == 'admin':
        if query.from_user.id == ADMIN_ID:
            return admin_panel(update, context)
        else:
            query.edit_message_text(text="Siz admin emassiz!")
            return ConversationHandler.END
    
    save_data(users, USERS_FILE)
    
    # Show main menu
    return main_menu(update, context)

def main_menu(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    user_id = str(query.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    
    if lang == 'uz':
        text = "Asosiy menyu:"
        buttons = [
            ["🛒 Savat", "catalog"],
            ["📦 Mahsulotlar", "products"],
            ["🏪 Do'kon haqida", "about"],
        ]
    else:
        text = "Главное меню:"
        buttons = [
            ["🛒 Корзина", "catalog"],
            ["📦 Товары", "products"],
            ["🏪 О магазине", "about"],
        ]
    
    keyboard = [[InlineKeyboardButton(btn[0], callback_data=btn[1])] for btn in buttons]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        update.message.reply_text(text=text, reply_markup=reply_markup)
    
    return MAIN_MENU

def show_categories(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    products_data = load_data(PRODUCTS_FILE)
    categories = products_data['categories']
    
    if lang == 'uz':
        text = "Kategoriyalar:"
        back_text = "🔙 Orqaga"
    else:
        text = "Категории:"
        back_text = "🔙 Назад"
    
    if not categories:
        text = "Hozircha kategoriyalar mavjud emas." if lang == 'uz' else "Категории пока отсутствуют."
        keyboard = [[InlineKeyboardButton(back_text, callback_data='main_menu')]]
    else:
        keyboard = []
        for cat_id, cat_name in categories.items():
            keyboard.append([InlineKeyboardButton(cat_name, callback_data=f'cat_{cat_id}')])
        keyboard.append([InlineKeyboardButton(back_text, callback_data='main_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    
    return CATEGORIES

def show_products(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    products_data = load_data(PRODUCTS_FILE)
    category_id = query.data.split('_')[1]
    products = products_data['products'].get(category_id, {})
    
    if lang == 'uz':
        text = f"{products_data['categories'][category_id]} kategoriyasidagi mahsulotlar:"
        back_text = "🔙 Orqaga"
        add_to_cart = "🛒 Savatga qo'shish"
    else:
        text = f"Товары категории {products_data['categories'][category_id]}:"
        back_text = "🔙 Назад"
        add_to_cart = "🛒 В корзину"
    
    if not products:
        text = "Hozircha mahsulotlar mavjud emas." if lang == 'uz' else "Товары пока отсутствуют."
        keyboard = [[InlineKeyboardButton(back_text, callback_data='products')]]
    else:
        keyboard = []
        for prod_id, prod_info in products.items():
            product_text = f"{prod_info['name']} - {prod_info['price']} so'm"
            keyboard.append([
                InlineKeyboardButton(product_text, callback_data=f'prod_{category_id}_{prod_id}')
            ])
        keyboard.append([InlineKeyboardButton(back_text, callback_data='products')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    
    return PRODUCTS

def product_detail(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    products_data = load_data(PRODUCTS_FILE)
    
    _, category_id, product_id = query.data.split('_')
    product = products_data['products'][category_id][product_id]
    
    if lang == 'uz':
        text = (f"🛍 Mahsulot: {product['name']}\n"
                f"💵 Narxi: {product['price']} so'm\n"
                f"📝 Tavsif: {product.get('description', 'Mavjud emas')}")
        add_to_cart = "🛒 Savatga qo'shish"
        back_text = "🔙 Orqaga"
    else:
        text = (f"🛍 Товар: {product['name']}\n"
                f"💵 Цена: {product['price']} сум\n"
                f"📝 Описание: {product.get('description', 'Нет описания')}")
        add_to_cart = "🛒 В корзину"
        back_text = "🔙 Назад"
    
    keyboard = [
        [InlineKeyboardButton(add_to_cart, callback_data=f'add_{category_id}_{product_id}')],
        [InlineKeyboardButton(back_text, callback_data=f'cat_{category_id}')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    
    return PRODUCTS

def add_to_cart(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    products_data = load_data(PRODUCTS_FILE)
    carts = load_data(CARTS_FILE)
    
    if user_id not in carts:
        carts[user_id] = []
    
    _, category_id, product_id = query.data.split('_')
    product = products_data['products'][category_id][product_id]
    
    # Add product to cart
    carts[user_id].append({
        "category_id": category_id,
        "product_id": product_id,
        "name": product['name'],
        "price": product['price'],
        "quantity": 1
    })
    
    save_data(carts, CARTS_FILE)
    
    if lang == 'uz':
        text = "Mahsulot savatga qo'shildi!"
    else:
        text = "Товар добавлен в корзину!"
    
    query.edit_message_text(text=text)
    return show_cart(update, context)

def show_cart(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    user_id = str(query.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    carts = load_data(CARTS_FILE)
    user_cart = carts.get(user_id, [])
    
    if lang == 'uz':
        text = "🛒 Savat:\n\n"
        total_text = "Jami:"
        empty_text = "Savat bo'sh"
        back_text = "🔙 Orqaga"
        clear_text = "🧹 Savatni tozalash"
        order_text = "🚖 Buyurtma berish"
    else:
        text = "🛒 Корзина:\n\n"
        total_text = "Итого:"
        empty_text = "Корзина пуста"
        back_text = "🔙 Назад"
        clear_text = "🧹 Очистить корзину"
        order_text = "🚖 Оформить заказ"
    
    if not user_cart:
        text = empty_text
        keyboard = [[InlineKeyboardButton(back_text, callback_data='main_menu')]]
    else:
        total = 0
        for item in user_cart:
            text += f"📦 {item['name']} - {item['price']} so'm x {item['quantity']}\n"
            total += int(item['price']) * item['quantity']
        
        text += f"\n{total_text} {total} so'm"
        
        keyboard = [
            [InlineKeyboardButton(order_text, callback_data='order')],
            [InlineKeyboardButton(clear_text, callback_data='clear_cart')],
            [InlineKeyboardButton(back_text, callback_data='main_menu')]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    
    return CART

def clear_cart(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    carts = load_data(CARTS_FILE)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    
    carts[user_id] = []
    save_data(carts, CARTS_FILE)
    
    if lang == 'uz':
        text = "Savat tozalandi!"
    else:
        text = "Корзина очищена!"
    
    query.edit_message_text(text=text)
    return show_cart(update, context)

def about_shop(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    
    if lang == 'uz':
        text = ("🏪 Bizning do'kon haqida:\n\n"
                "Biz eng yaxshi mahsulotlarni eng arzon narxlarda taklif qilamiz!\n"
                "Ish vaqti: 09:00 - 21:00\n"
                "Telefon: +998906037222")
        back_text = "🔙 Orqaga"
    else:
        text = ("🏪 О нашем магазине:\n\n"
                "Мы предлагаем лучшие товары по самым низким ценам!\n"
                "Время работы: 09:00 - 21:00\n"
                "Телефон: +998906067222")
        back_text = "🔙 Назад"
    
    keyboard = [[InlineKeyboardButton(back_text, callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    
    return ABOUT

def admin_panel(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    
    if lang == 'uz':
        text = "👑 Admin paneli:"
        buttons = [
            ["📦 Kategoriya qo'shish", "add_category"],
            ["🛍 Mahsulot qo'shish", "add_product"],
            ["🔙 Asosiy menyu", "main_menu"]
        ]
    else:
        text = "👑 Админ панель:"
        buttons = [
            ["📦 Добавить категорию", "add_category"],
            ["🛍 Добавить товар", "add_product"],
            ["🔙 Главное меню", "main_menu"]
        ]
    
    keyboard = [[InlineKeyboardButton(btn[0], callback_data=btn[1])] for btn in buttons]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(text=text, reply_markup=reply_markup)
    
    return ADMIN

def add_category(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    
    if lang == 'uz':
        text = "Yangi kategoriya nomini yuboring:"
        back_text = "🔙 Orqaga"
    else:
        text = "Отправьте название новой категории:"
        back_text = "🔙 Назад"
    
    keyboard = [[InlineKeyboardButton(back_text, callback_data='admin')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    
    return ADD_CATEGORY

def save_category(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    products_data = load_data(PRODUCTS_FILE)
    
    category_name = update.message.text
    category_id = str(len(products_data['categories']) + 1)
    
    products_data['categories'][category_id] = category_name
    save_data(products_data, PRODUCTS_FILE)
    
    if lang == 'uz':
        text = f"Yangi kategoriya '{category_name}' qo'shildi!"
    else:
        text = f"Новая категория '{category_name}' добавлена!"
    
    update.message.reply_text(text)
    return admin_panel_from_message(update, context)

def add_product(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    products_data = load_data(PRODUCTS_FILE)
    
    if not products_data['categories']:
        if lang == 'uz':
            text = "Avval kategoriya qo'shishingiz kerak!"
        else:
            text = "Сначала нужно добавить категорию!"
        
        query.edit_message_text(text=text)
        return admin_panel(update, context)
    
    if lang == 'uz':
        text = "Mahsulot qo'shish uchun kategoriyani tanlang:"
        back_text = "🔙 Orqaga"
    else:
        text = "Выберите категорию для добавления товара:"
        back_text = "🔙 Назад"
    
    keyboard = []
    for cat_id, cat_name in products_data['categories'].items():
        keyboard.append([InlineKeyboardButton(cat_name, callback_data=f'add_prod_{cat_id}')])
    keyboard.append([InlineKeyboardButton(back_text, callback_data='admin')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    
    return ADD_PRODUCT

def get_product_info(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    
    context.user_data['add_product_category'] = query.data.split('_')[2]
    
    if lang == 'uz':
        text = ("Yangi mahsulot haqida ma'lumot yuboring quyidagi formatda:\n\n"
                "Nomi\nNarxi\nTavsif (ixtiyoriy)\n\n"
                "Misol: \n"
                "iPhone 13\n12000000\nEng yangi iPhone modeli")
        back_text = "🔙 Orqaga"
    else:
        text = ("Отправьте информацию о новом товаре в следующем формате:\n\n"
                "Название\nЦена\nОписание (необязательно)\n\n"
                "Пример: \n"
                "iPhone 13\n12000000\nНовейшая модель iPhone")
        back_text = "🔙 Назад"
    
    keyboard = [[InlineKeyboardButton(back_text, callback_data='add_product')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    
    return ADD_PRODUCT

def save_product(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    products_data = load_data(PRODUCTS_FILE)
    
    category_id = context.user_data['add_product_category']
    product_info = update.message.text.split('\n')
    
    if len(product_info) < 2:
        if lang == 'uz':
            text = "Noto'g'ri format! Iltimos, qayta urinib ko'ring."
        else:
            text = "Неверный формат! Пожалуйста, попробуйте еще раз."
        
        update.message.reply_text(text)
        return ADD_PRODUCT
    
    product_name = product_info[0].strip()
    product_price = product_info[1].strip()
    product_desc = product_info[2].strip() if len(product_info) > 2 else ""
    
    if category_id not in products_data['products']:
        products_data['products'][category_id] = {}
    
    product_id = str(len(products_data['products'][category_id]) + 1)
    products_data['products'][category_id][product_id] = {
        "name": product_name,
        "price": product_price,
        "description": product_desc
    }
    
    save_data(products_data, PRODUCTS_FILE)
    
    if lang == 'uz':
        text = f"Yangi mahsulot '{product_name}' qo'shildi!"
    else:
        text = f"Новый товар '{product_name}' добавлен!"
    
    update.message.reply_text(text)
    return admin_panel_from_message(update, context)

def admin_panel_from_message(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    users = load_data(USERS_FILE)
    lang = users[user_id]['lang']
    
    if lang == 'uz':
        text = "👑 Admin paneli:"
        buttons = [
            ["📦 Kategoriya qo'shish", "add_category"],
            ["🛍 Mahsulot qo'shish", "add_product"],
            ["🔙 Asosiy menyu", "main_menu"]
        ]
    else:
        text = "👑 Админ панель:"
        buttons = [
            ["📦 Добавить категорию", "add_category"],
            ["🛍 Добавить товар", "add_product"],
            ["🔙 Главное меню", "main_menu"]
        ]
    
    keyboard = [[InlineKeyboardButton(btn[0], callback_data=btn[1])] for btn in buttons]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(text=text, reply_markup=reply_markup)
    
    return ADMIN

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Amal bekor qilindi.')
    return ConversationHandler.END

def error(update: Update, context: CallbackContext):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main() -> None:
    # Bot tokenini o'rnating
    updater = Updater("8076561745:AAFHdCGcqBQXiST-EXfcWK9uiHUufYm0rA0", use_context=True)
    
    dp = updater.dispatcher
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_LANG: [
                CallbackQueryHandler(select_lang, pattern='^lang_'),
                CallbackQueryHandler(admin_panel, pattern='^admin$')
            ],
            MAIN_MENU: [
                CallbackQueryHandler(show_categories, pattern='^products$'),
                CallbackQueryHandler(show_cart, pattern='^catalog$'),
                CallbackQueryHandler(about_shop, pattern='^about$'),
                CallbackQueryHandler(admin_panel, pattern='^admin$')
            ],
            CATEGORIES: [
                CallbackQueryHandler(show_products, pattern='^cat_'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$')
            ],
            PRODUCTS: [
                CallbackQueryHandler(product_detail, pattern='^prod_'),
                CallbackQueryHandler(show_categories, pattern='^products$'),
                CallbackQueryHandler(add_to_cart, pattern='^add_')
            ],
            CART: [
                CallbackQueryHandler(clear_cart, pattern='^clear_cart$'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$'),
                CallbackQueryHandler(show_cart, pattern='^order$')
            ],
            ABOUT: [
                CallbackQueryHandler(main_menu, pattern='^main_menu$')
            ],
            ADMIN: [
                CallbackQueryHandler(add_category, pattern='^add_category$'),
                CallbackQueryHandler(add_product, pattern='^add_product$'),
                CallbackQueryHandler(main_menu, pattern='^main_menu$')
            ],
            ADD_CATEGORY: [
                MessageHandler(Filters.text & ~Filters.command, save_category),
                CallbackQueryHandler(admin_panel, pattern='^admin$')
            ],
            ADD_PRODUCT: [
                CallbackQueryHandler(get_product_info, pattern='^add_prod_'),
                MessageHandler(Filters.text & ~Filters.command, save_product),
                CallbackQueryHandler(admin_panel, pattern='^admin$')
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    dp.add_handler(conv_handler)
    dp.add_error_handler(error)
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()