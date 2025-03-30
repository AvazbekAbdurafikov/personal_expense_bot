import asyncio
import logging
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from database import Database
from keyboards import get_main_keyboard, get_categories_keyboard, get_cancel_keyboard, get_report_period_keyboard
from reports import generate_excel_report

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())
db = Database()

# Get allowed users from env
ALLOWED_USER_IDS = {
    int(user_id.strip()) 
    for user_id in os.getenv("ALLOWED_USER_IDS", "").split(",") 
    if user_id.strip()
}

# Get admin users from env
ADMIN_USER_IDS = {
    int(user_id.strip()) 
    for user_id in os.getenv("ADMIN_USER_IDS", "").split(",") 
    if user_id.strip()
}

class ExpenseStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_description = State()
    waiting_for_custom_start_date = State()
    waiting_for_custom_end_date = State()
    waiting_for_month = State()

def format_number(number: int) -> str:
    """Format number with thousand separators"""
    return f"{number:,}".replace(",", " ")

async def check_user_access(message: types.Message) -> bool:
    """Check if user is allowed to use the bot"""
    if not message.from_user:
        await message.answer("❌ Kechirasiz, botdan foydalanish mumkin emas.")
        return False
    
    user_id = message.from_user.id
    if user_id not in ALLOWED_USER_IDS:
        await message.answer(
            "❌ Kechirasiz, bu bot faqat ruxsat berilgan foydalanuvchilar uchun.\n\n"
            "Bot egasi bilan bog'laning."
        )
        return False
    return True

async def check_callback_user_access(callback: types.CallbackQuery) -> bool:
    """Check if callback user is allowed to use the bot"""
    if not callback.from_user:
        await callback.answer("❌ Kechirasiz, botdan foydalanish mumkin emas.")
        return False
    
    user_id = callback.from_user.id
    if user_id not in ALLOWED_USER_IDS:
        await callback.answer("❌ Kechirasiz, bu bot faqat ruxsat berilgan foydalanuvchilar uchun.")
        return False
    return True

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Start command handler"""
    if not await check_user_access(message):
        return
    
    user_id = await db.get_or_create_user(message.from_user.id)
    
    await message.answer(
        f"👋 Assalomu alaykum, {message.from_user.full_name}!\n\n"
        "🤖 Men sizning shaxsiy xarajatlaringizni hisobga olishga yordam beraman.\n\n"
        "📝 Xarajat qo'shish uchun \"➕ Xarajat qo'shish\" tugmasini bosing.\n"
        "📊 Hisobotni ko'rish uchun \"📊 Oylik hisobot\" yoki \"📊 Excel hisobot\" tugmalaridan foydalaning.",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Help command handler"""
    if not await check_user_access(message):
        return
    
    await message.answer(
        "🔍 Botdan foydalanish bo'yicha qo'llanma:\n\n"
        "1️⃣ Xarajat qo'shish:\n"
        "   • \"➕ Xarajat qo'shish\" tugmasini bosing\n"
        "   • Summani kiriting\n"
        "   • Kategoriyani tanlang\n"
        "   • Izoh qoldiring (ixtiyoriy)\n\n"
        "2️⃣ Hisobotlar:\n"
        "   • \"📊 Oylik hisobot\" - oylik xarajatlar hisoboti\n"
        "   • \"📊 Excel hisobot\" - Excel formatdagi batafsil hisobot\n\n"
        "❓ Savollar bo'lsa, /help buyrug'idan foydalaning.",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "💰 Xarajat qo'shish")
async def add_expense(message: types.Message, state: FSMContext):
    """Handle expense addition"""
    if not await check_user_access(message):
        return

    # Get user categories
    user_id = await db.get_or_create_user(message.from_user.id)
    categories = await db.get_categories(user_id)
    
    if not categories:
        await message.answer("Xatolik: Kategoriyalar topilmadi. /start buyrug'ini qayta yuboring.")
        return

    await state.set_state(ExpenseStates.waiting_for_amount)
    await message.answer(
        "Xarajat miqdorini kiriting (faqat raqamlar):",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(Command("add_expense"))
async def cmd_add_expense(message: types.Message, state: FSMContext):
    """Add expense command handler"""
    if not message.from_user:
        return
    
    await state.set_state(ExpenseStates.waiting_for_amount)
    await message.answer(
        "💰 Xarajat miqdorini kiriting:",
        reply_markup=get_cancel_keyboard()
    )

@dp.message(StateFilter(ExpenseStates.waiting_for_amount))
async def process_amount(message: types.Message, state: FSMContext):
    """Process expense amount"""
    try:
        # Remove spaces and convert to integer
        amount = int(message.text.replace(" ", ""))
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Store amount in state
        await state.update_data(amount=amount)

        # Get categories for inline keyboard
        user_id = await db.get_or_create_user(message.from_user.id)
        categories = await db.get_categories(user_id)

        # Show category selection keyboard
        await state.set_state(ExpenseStates.waiting_for_category)
        await message.answer(
            f"Kategoriyani tanlang ({format_number(amount)} so'm):",
            reply_markup=get_categories_keyboard(categories)
        )

    except (ValueError, TypeError):
        await message.answer(
            "Noto'g'ri format. Iltimos, faqat raqamlardan foydalaning.\n"
            "Masalan: 50000"
        )

@dp.callback_query(lambda c: c.data.startswith("category_"))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    """Process category selection"""
    if not await check_callback_user_access(callback):
        return
    
    category_id = int(callback.data.split('_')[1])
    await state.update_data(category_id=category_id)
    await callback.message.answer(
        "Izoh kiriting (ixtiyoriy):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ExpenseStates.waiting_for_description)
    await callback.answer()

@dp.message(StateFilter(ExpenseStates.waiting_for_description))
async def process_description(message: types.Message, state: FSMContext):
    """Process expense description and save expense"""
    if not await check_user_access(message):
        return

    data = await state.get_data()
    amount = data["amount"]
    category_id = data["category_id"]
    user_id = await db.get_or_create_user(message.from_user.id)
    description = message.text

    await db.add_expense(user_id, amount, category_id, description)
    category = await db.get_category_by_id(category_id, user_id)
    
    await message.answer(
        f"✅ Xarajat qo'shildi:\n"
        f"💰 {format_number(amount)} so'm\n"
        f"📁 {category['name']}\n"
        f"📝 {description if description else 'Izohsiz'}",
        reply_markup=get_main_keyboard()
    )
    await state.clear()

@dp.message(F.text == "📊 Oylik hisobot")
async def monthly_report(message: types.Message):
    """Show monthly expenses report menu"""
    if not await check_user_access(message):
        return

    # Create keyboard with current and past 6 months
    buttons = []
    current_date = datetime.now()
    
    # Get last 7 months correctly
    for i in range(7):
        # Calculate date by subtracting months properly
        if i == 0:
            date = current_date.replace(day=1)
        else:
            # Handle year change correctly
            year = current_date.year
            month = current_date.month - i
            if month <= 0:
                year -= 1
                month += 12
            date = current_date.replace(year=year, month=month, day=1)
        
        # Format month name in Uzbek
        month_name = {
            1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
            5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
            9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr"
        }[date.month]
        
        button_text = f"{month_name} {date.year}"
        callback_data = f"month_{date.year}-{date.month}"
        buttons.append([types.InlineKeyboardButton(text=button_text, callback_data=callback_data)])

    await message.answer(
        "📅 Qaysi oy uchun hisobot kerak?",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@dp.callback_query(lambda c: c.data.startswith('month_'))
async def process_month_selection(callback: types.CallbackQuery):
    """Process month selection for report"""
    if not await check_callback_user_access(callback):
        return

    # Extract year and month from callback data
    _, year_month = callback.data.split('_')
    year, month = map(int, year_month.split('-'))
    
    # Calculate start and end dates for the selected month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

    user_id = await db.get_or_create_user(callback.from_user.id)
    
    # Get both summary and detailed expenses
    summary = await db.get_monthly_summary(user_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    expenses = await db.get_expenses_by_date_range(user_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    
    # Delete message with keyboard
    await callback.message.delete()
    
    if not summary and not expenses:
        await callback.message.answer(
            f"📅 {start_date.strftime('%B %Y')} oyida xarajatlar yo'q.",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return

    # First show the summary
    total = sum(item["total_amount"] for item in summary)
    report = f"📊 {start_date.strftime('%B %Y')} oyi uchun hisobot:\n\n"
    
    for item in summary:
        percentage = (item["total_amount"] / total) * 100
        report += (
            f"{item['category_name']}: {format_number(item['total_amount'])} so'm\n"
            f"({percentage:.1f}%)\n\n"
        )
    
    report += f"\n💰 Jami: {format_number(total)} so'm\n"
    report += "\n📝 Batafsil xarajatlar:\n"

    # Then show detailed expenses
    for expense in expenses:
        date = datetime.fromisoformat(expense['date'].replace('Z', '+00:00'))
        report += (
            f"\n📅 {date.strftime('%d.%m.%Y')}\n"
            f"💰 {format_number(expense['amount'])} so'm\n"
            f"📁 {expense['category_name']}\n"
            f"📝 {expense['description'] if expense['description'] else 'Izohsiz'}\n"
            f"{'─' * 20}\n"
        )
    
    # Send in chunks if too long
    if len(report) > 4000:
        chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
        for chunk in chunks:
            await callback.message.answer(chunk)
        await callback.message.answer(
            "✅ Hisobot tugadi.",
            reply_markup=get_main_keyboard()
        )
    else:
        await callback.message.answer(
            report,
            reply_markup=get_main_keyboard()
        )
    
    await callback.answer()

@dp.message(F.text == "📋 So'nggi xarajatlar")
async def recent_expenses(message: types.Message):
    """Show recent expenses"""
    if not await check_user_access(message):
        return

    user_id = await db.get_or_create_user(message.from_user.id)
    expenses = await db.get_expenses(user_id, 10)
    if not expenses:
        await message.answer("Hali xarajatlar yo'q.")
        return

    report = "📋 So'nggi xarajatlar:\n\n"
    for expense in expenses:
        date = datetime.fromisoformat(expense["date"]).strftime("%d.%m.%Y")
        report += (
            f"📅 {date}\n"
            f"💰 {format_number(expense['amount'])} so'm\n"
            f"📁 {expense['category_name']}\n"
            f"📝 {expense['description'] if expense['description'] else 'Izohsiz'}\n\n"
        )
    
    await message.answer(report)

@dp.message(F.text == "📈 Kunlik statistika")
async def daily_stats(message: types.Message):
    """Show daily statistics"""
    if not await check_user_access(message):
        return

    user_id = await db.get_or_create_user(message.from_user.id)
    stats = await db.get_daily_summary(user_id)
    if not stats:
        await message.answer("So'nggi 7 kun ichida xarajatlar yo'q.")
        return

    report = "📈 So'nggi 7 kunlik statistika:\n\n"
    for stat in stats:
        date = datetime.fromisoformat(stat["expense_date"]).strftime("%d.%m.%Y")
        report += f"📅 {date}: {format_number(stat['total_amount'])} so'm\n"
    
    await message.answer(report)

@dp.message(F.text == "📊 Excel hisobot")
async def excel_report_menu(message: types.Message):
    """Show Excel report menu"""
    if not await check_user_access(message):
        return
        
    await message.answer(
        "Qaysi davr uchun hisobot kerak?",
        reply_markup=get_report_period_keyboard()
    )

@dp.callback_query(lambda c: c.data.startswith('report_'))
async def process_report_period(callback: types.CallbackQuery, state: FSMContext):
    """Process report period selection"""
    if not await check_callback_user_access(callback):
        return
    
    period = callback.data.split('_')[1]
    user_id = await db.get_or_create_user(callback.from_user.id)
    
    # Calculate date range based on period
    end_date = datetime.now()
    
    if period == "custom":
        await state.update_data(user_id=user_id)  
        await state.set_state(ExpenseStates.waiting_for_custom_start_date)
        await callback.message.answer(
            "Boshlang'ich sanani kiriting (DD.MM.YYYY):",
            reply_markup=get_cancel_keyboard()
        )
        await callback.answer()
        return
    
    if period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    elif period == "year":
        start_date = end_date - timedelta(days=365)
    else:
        await callback.message.answer("Noto'g'ri davr tanlandi", reply_markup=get_main_keyboard())
        await callback.answer()
        return
    
    await generate_report(
        callback.message,
        user_id,
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    await callback.answer()

@dp.message(StateFilter(ExpenseStates.waiting_for_custom_start_date))
async def process_custom_start_date(message: types.Message, state: FSMContext):
    """Process custom start date"""
    try:
        start_date = datetime.strptime(message.text, "%d.%m.%Y")
        await state.update_data(start_date=start_date.strftime('%Y-%m-%d'))
        await state.set_state(ExpenseStates.waiting_for_custom_end_date)
        await message.answer(
            "Tugash sanasini kiriting (DD.MM.YYYY):",
            reply_markup=get_cancel_keyboard()
        )
    except ValueError:
        await message.answer(
            "Noto'g'ri sana formati. Iltimos DD.MM.YYYY formatida kiriting (masalan, 01.01.2024)",
            reply_markup=get_cancel_keyboard()
        )

@dp.message(StateFilter(ExpenseStates.waiting_for_custom_end_date))
async def process_custom_end_date(message: types.Message, state: FSMContext):
    """Process custom end date"""
    try:
        end_date = datetime.strptime(message.text, "%d.%m.%Y")
        data = await state.get_data()
        user_id = data["user_id"]
        start_date = data["start_date"]
        
        await generate_report(
            message,
            user_id,
            start_date,
            end_date.strftime('%Y-%m-%d')
        )
        await state.clear()
        
    except ValueError:
        await message.answer(
            "Noto'g'ri sana formati. Iltimos DD.MM.YYYY formatida kiriting (masalan, 01.01.2024)",
            reply_markup=get_cancel_keyboard()
        )
    except KeyError:
        await message.answer(
            "Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()

async def generate_report(message: types.Message, user_id: int, start_date: str, end_date: str):
    """Generate and send Excel report"""
    # Get data for report
    expenses = await db.get_expenses_by_date_range(user_id, start_date, end_date)
    if not expenses:
        await message.answer("Bu davr uchun xarajatlar topilmadi.", reply_markup=get_main_keyboard())
        return

    category_summary = await db.get_category_summary_by_date_range(user_id, start_date, end_date)
    daily_summary = await db.get_daily_summary_by_date_range(user_id, start_date, end_date)
    
    # Generate Excel file in memory
    excel_data, filename = generate_excel_report(
        expenses=expenses,
        category_summary=category_summary,
        daily_summary=daily_summary,
        start_date=start_date,
        end_date=end_date
    )
    
    # Format dates for message
    start = datetime.fromisoformat(start_date).strftime("%d.%m.%Y")
    end = datetime.fromisoformat(end_date).strftime("%d.%m.%Y")
    
    # Send file from memory
    await message.answer_document(
        types.BufferedInputFile(excel_data, filename=filename),
        caption=f"📊 Hisobot: {start} - {end}",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("reset_db"))
async def reset_database(message: types.Message):
    """Reset database tables - admin only command"""
    if not message.from_user or message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("Bu buyruq faqat administratorlar uchun.")
        return

    await db.reset_tables()
    await message.answer("Ma'lumotlar bazasi muvaffaqiyatli qayta tiklandi.")

@dp.callback_query(F.data == "cancel")
async def cancel_operation(callback: types.CallbackQuery, state: FSMContext):
    """Cancel current operation"""
    if not await check_callback_user_access(callback):
        return
    
    current_state = await state.get_state()
    await state.clear()
    
    # Delete the message with inline keyboard
    await callback.message.delete()
    
    # Send appropriate message based on the state
    if current_state in [ExpenseStates.waiting_for_amount, ExpenseStates.waiting_for_description]:
        await callback.message.answer(
            "✅ Xarajat kiritish bekor qilindi.",
            reply_markup=get_main_keyboard()
        )
    elif current_state in [ExpenseStates.waiting_for_custom_start_date, ExpenseStates.waiting_for_custom_end_date]:
        await callback.message.answer(
            "✅ Hisobot olish bekor qilindi.",
            reply_markup=get_main_keyboard()
        )
    else:
        await callback.message.answer(
            "✅ Amal bekor qilindi.",
            reply_markup=get_main_keyboard()
        )
    
    await callback.answer()

async def main():
    # Initialize database tables
    await db.create_tables()
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
