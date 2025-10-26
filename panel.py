from ctypes import windll
from tkinter import Tk, Canvas
from variable import *
from update_status import update_status
from update_icons import update_icons
from update_grap import update_grap
from shortcut_panel import create_shortcut_icons

# Создаем главное окно
root = Tk()
root.title("pop")
root.attributes('-fullscreen', True)  # Полноэкранный режим
root.resizable(False, False)  # Отключаем изменение размера окна
root.overrideredirect(True)
root.wm_attributes('-topmost', True)  # Сделать окно поверх других
root.wm_attributes("-transparentcolor", "#45765a")  # Прозрачный цвет
root.wm_overrideredirect(True)  # Скрыть заголовок окна

# Получение разрешения экрана
w = root.winfo_screenwidth()
h = root.winfo_screenheight()

# Создание канваса
canvas = Canvas(root, width=w, height=h, bg='#45765a', highlightthickness=0)
canvas.pack()

# Скрываем панель задач
h_tray = windll.user32.FindWindowA(b'Shell_TrayWnd', None)
windll.user32.ShowWindow(h_tray, 0)

color="#220294" 
bar=canvas.create_rectangle(0, 0, 400, RECT_HEIGHT, fill=color, outline='')
canvas.addtag_withtag("icon", bar)

# Функция для рисования закругленного прямоугольника

def draw_rounded_rectangle(canvas, x1, y1, x2, y2, radius, **kwargs):
    if radius > (x2 - x1) / 2:
        radius = (x2 - x1) / 2
    if radius > (y2 - y1) / 2:
        radius = (y2 - y1) / 2

    arc = radius * 2
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2 - radius,
        x1, y1 + radius,
    ]
    polygon_id = canvas.create_polygon(points, **kwargs, smooth=True)
    # Добавляем тег для полигона
    canvas.addtag_withtag("icon", polygon_id)

    # Создание арки в четырех разных местах на canvas и добавление тегов
    arc1_id = canvas.create_arc(x1, y1, x1 + arc, y1 + arc, start=90, extent=90, style='pieslice', **kwargs)
    canvas.addtag_withtag("icon", arc1_id)

    arc2_id = canvas.create_arc(x2 - arc, y1, x2, y1 + arc, start=0, extent=90, style='pieslice', **kwargs)
    canvas.addtag_withtag("icon", arc2_id)

    arc3_id = canvas.create_arc(x2 - arc, y2 - arc, x2, y2, start=270, extent=90, style='pieslice', **kwargs)
    canvas.addtag_withtag("icon", arc3_id)

    arc4_id = canvas.create_arc(x1, y2 - arc, x1 + arc, y2, start=180, extent=90, style='pieslice', **kwargs)
    canvas.addtag_withtag("icon", arc4_id)

draw_rounded_rectangle(canvas, 1192,0,1243,RECT_HEIGHT,5,fill=color)
draw_rounded_rectangle(canvas, 1250,0,1315,RECT_HEIGHT,5,fill=color)
draw_rounded_rectangle(canvas, 1320,0,1405,RECT_HEIGHT,5,fill=color)
draw_rounded_rectangle(canvas, 1412,0,1490,RECT_HEIGHT,5,fill=color)
draw_rounded_rectangle(canvas, 1503,0,1652,RECT_HEIGHT,5,fill=color)
draw_rounded_rectangle(canvas, 1658,0,1725,RECT_HEIGHT,5,fill=color)
draw_rounded_rectangle(canvas, 1735,0,1770,RECT_HEIGHT,5,fill=color)
draw_rounded_rectangle(canvas, 1780,0,1915,RECT_HEIGHT,5,fill=color)
root.after(100, lambda: update_status(canvas, root, w))

draw_rounded_rectangle(canvas, 990,0,1050,RECT_HEIGHT,5,fill=color)
draw_rounded_rectangle(canvas, 1115,0,1160,RECT_HEIGHT,5,fill=color)
draw_rounded_rectangle(canvas, 610,0,860,RECT_HEIGHT,5,fill=color)
draw_rounded_rectangle(canvas, 490,0,550,RECT_HEIGHT,5,fill=color)
root.after(100, lambda: create_shortcut_icons(canvas, root, SHORTCUTS_DIR))

root.after(100, lambda: update_icons(canvas, root, w))
root.after(100, lambda: update_grap(canvas, root))

# Запуск основного цикла
root.mainloop()
