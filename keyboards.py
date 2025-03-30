from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard"""
    keyboard = [
        [
            KeyboardButton(text="💰 Xarajat qo'shish"),
            KeyboardButton(text="📊 Oylik hisobot")
        ],
        [
            KeyboardButton(text="📋 So'nggi xarajatlar"),
            KeyboardButton(text="📈 Kunlik statistika")
        ],
        [
            KeyboardButton(text="📊 Excel hisobot")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_categories_keyboard(categories: List[Dict]) -> InlineKeyboardMarkup:
    """Categories selection keyboard"""
    keyboard = []
    row = []
    for i, cat in enumerate(categories):
        row.append(InlineKeyboardButton(
            text=cat["name"],
            callback_data=f"category_{cat['id']}"
        ))
        if len(row) == 2 or i == len(categories) - 1:
            keyboard.append(row)
            row = []
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_report_period_keyboard() -> InlineKeyboardMarkup:
    """Report period selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="📅 Hafta", callback_data="report_week"),
            InlineKeyboardButton(text="📅 Oy", callback_data="report_month")
        ],
        [
            InlineKeyboardButton(text="📅 Yil", callback_data="report_year"),
            InlineKeyboardButton(text="📅 Boshqa davr", callback_data="report_custom")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel operation keyboard"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
        ]]
    )
