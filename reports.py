import io
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any
from openpyxl.styles import Font, PatternFill

def format_number(number: int) -> str:
    """Format number with thousand separators"""
    return f"{number:,}".replace(",", " ")

def add_total_row(sheet, row_num: int, col_letter: str, total_amount: int):
    """Add total row with formatting"""
    cell = sheet[f"{col_letter}{row_num}"]
    cell.value = f"Jami: {format_number(total_amount)} so'm"
    cell.font = Font(bold=True)
    cell.fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

def generate_excel_report(
    expenses: List[Dict[str, Any]],
    category_summary: List[Dict[str, Any]],
    daily_summary: List[Dict[str, Any]],
    start_date: str,
    end_date: str
) -> tuple[bytes, str]:
    """Generate Excel report for the given date range and return bytes"""
    # Create buffer to store Excel file in memory
    output = io.BytesIO()
    filename = f"expenses_{start_date}_to_{end_date}.xlsx"
    
    # Create Excel writer with buffer
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Expenses sheet
        expenses_df = pd.DataFrame(expenses)
        if not expenses_df.empty:
            expenses_df['date'] = pd.to_datetime(expenses_df['date']).dt.strftime('%d.%m.%Y %H:%M')
            raw_amounts = expenses_df['amount'].copy()  # Keep original amounts for sum
            expenses_df['amount'] = expenses_df['amount'].apply(format_number)
            expenses_df = expenses_df[['date', 'amount', 'category_name', 'description']]
            expenses_df.columns = ['Sana', 'Miqdor (so\'m)', 'Kategoriya', 'Izoh']
            expenses_df.to_excel(writer, sheet_name='Xarajatlar', index=False)
            
            # Add total to expenses sheet
            total_amount = raw_amounts.sum()
            sheet = writer.sheets['Xarajatlar']
            add_total_row(sheet, len(expenses_df) + 2, 'B', total_amount)

        # Category summary sheet
        category_df = pd.DataFrame(category_summary)
        if not category_df.empty:
            raw_amounts = category_df['total_amount'].copy()  # Keep original amounts for sum
            category_df['total_amount'] = category_df['total_amount'].apply(format_number)
            category_df.columns = ['Kategoriya', 'Xarajatlar soni', 'Umumiy miqdor (so\'m)']
            category_df.to_excel(writer, sheet_name='Kategoriyalar', index=False)
            
            # Add total to category sheet
            total_amount = raw_amounts.sum()
            sheet = writer.sheets['Kategoriyalar']
            add_total_row(sheet, len(category_df) + 2, 'C', total_amount)

        # Daily summary sheet
        daily_df = pd.DataFrame(daily_summary)
        if not daily_df.empty:
            daily_df['expense_date'] = pd.to_datetime(daily_df['expense_date']).dt.strftime('%d.%m.%Y')
            raw_amounts = daily_df['total_amount'].copy()  # Keep original amounts for sum
            daily_df['total_amount'] = daily_df['total_amount'].apply(format_number)
            daily_df.columns = ['Sana', 'Umumiy miqdor (so\'m)', 'Xarajatlar soni']
            daily_df.to_excel(writer, sheet_name='Kunlik', index=False)
            
            # Add total to daily sheet
            total_amount = raw_amounts.sum()
            sheet = writer.sheets['Kunlik']
            add_total_row(sheet, len(daily_df) + 2, 'B', total_amount)

        # Auto-adjust columns width
        for sheet in writer.sheets.values():
            for column in sheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                sheet.column_dimensions[column[0].column_letter].width = adjusted_width

    # Get the bytes from the buffer
    output.seek(0)
    return output.getvalue(), filename
