import gspread

_gspread = gspread.service_account()

gs_sheet = _gspread.open("Музыкальная школа")

