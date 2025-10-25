import tkinter as tk
from tkinter import filedialog, messagebox
import json
from datetime import datetime, timedelta

def parse_wpt_file(wpt_path):
    descriptions = {}
    try:
        with open(wpt_path, 'r', encoding='utf-8') as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) >= 6 and not parts[0].startswith('$'):
                    name = parts[0]
                    desc = parts[-1]  # 最後の項目のみをdescriptionとして抽出
                    descriptions[name] = desc
    except Exception as e:
        messagebox.showerror("エラー", f"WPTファイルの読み込みに失敗しました: {e}")
    return descriptions

def parse_task_text(task_text, utc_offset, wpt_descriptions):
    lines = task_text.strip().split('\n')
    turnpoints = []
    sss_times = []
    
    # 最終行にStart gatesがある
    for line in lines:
        if line.startswith('Start gates:'):
            if ':' in line:
                parts = line.split(':', 1)
                times_str = parts[1].strip()
                if times_str:
                    times = times_str.split(',')
                    for t in times:
                        local_time = datetime.strptime(t.strip(), '%H:%M')
                        utc_time = (local_time - timedelta(hours=utc_offset)).strftime('%H:%M:%S') + 'Z'
                        sss_times.append(utc_time)

    for line in lines:
        if line.startswith('No') or line.startswith('Start gates:') or not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 8:
            continue

        no = parts[0].strip()
        tp_id = parts[2].strip()
        radius = float(parts[3].replace('m', '').strip())
        lat = float(parts[6].split()[1].replace('Lat:', '').strip())
        lon = float(parts[6].split()[3].replace('Lon:', '').strip())
        alt = float(parts[7].replace('m', '').strip())
        desc = wpt_descriptions.get(tp_id, '***')

        tp_type = None
        if 'TO' in tp_id:
            tp_type = 'TAKEOFF'
        elif 'SS' in no:
            tp_type = 'SSS'
        elif 'ES' in no:
            tp_type = 'ESS'

        turnpoint = {
            'radius': radius,
            'waypoint': {
                'lon': lon,
                'lat': lat,
                'altSmoothed': alt,
                'name': tp_id,
                'description': desc
            }
        }
        if tp_type:
            turnpoint['type'] = tp_type
        turnpoints.append(turnpoint)

    goal_deadline_local = lines[-2].split('\t')[5].strip() if len(lines) > 2 else '16:50'
    goal_deadline_local = goal_deadline_local.split()[0]
    goal_deadline_utc = (datetime.strptime(goal_deadline_local, '%H:%M') - timedelta(hours=utc_offset)).strftime('%H:%M:%S') + 'Z'

    sss_type = 'RACE' if sss_times else 'ELAPSED-TIME'

    task_data = {
        'version': 1,
        'taskType': 'CLASSIC',
        'turnpoints': turnpoints,
        'sss': {
            'type': sss_type,
            'direction': 'EXIT'
        },
        'goal': {
            'type': 'CYLINDER',
            'deadline': goal_deadline_utc
        },
        'earthModel': 'WGS84'
    }

    if sss_times:
        task_data['sss']['timeGates'] = sss_times

    return task_data

def save_task_file(task_data, filename):
    if not filename.endswith('.xctsk'):
        filename += '.xctsk'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(task_data, f, ensure_ascii=False, indent=2)

def generate_file():
    task_text = task_text_box.get('1.0', tk.END).strip()
    filename = filename_entry.get().strip()
    utc_offset = float(utc_offset_entry.get().strip())
    wpt_path = wpt_file_path.get().strip()

    if not task_text or not filename:
        messagebox.showerror('エラー', 'タスク情報とファイル名を入力してください。')
        return

    wpt_descriptions = parse_wpt_file(wpt_path) if wpt_path else {}
    task_data = parse_task_text(task_text, utc_offset, wpt_descriptions)
    save_task_file(task_data, filename)
    messagebox.showinfo('完了', f'{filename}.xctsk を作成しました。')

def browse_wpt_file():
    file_path = filedialog.askopenfilename(filetypes=[('WPT files', '*.wpt'), ('All files', '*.*')])
    if file_path:
        wpt_file_path.set(file_path)

root = tk.Tk()
root.title('report2xctsk')

frame = tk.Frame(root, padx=10, pady=10)
frame.pack(fill='both', expand=True)

info_frame = tk.Frame(frame)
info_frame.pack(fill='x', pady=5)

tk.Label(info_frame, text='出力ファイル名:').grid(row=0, column=0, sticky='e')
filename_entry = tk.Entry(info_frame, width=20)
filename_entry.grid(row=0, column=1, padx=5)

tk.Label(info_frame, text='UTC_offset').grid(row=0, column=2, sticky='e')
utc_offset_entry = tk.Entry(info_frame, width=5)
utc_offset_entry.grid(row=0, column=3, padx=5)
utc_offset_entry.insert(0, '9')

tk.Label(info_frame, text='WPTファイル(opt):').grid(row=1, column=0, sticky='e')
wpt_file_path = tk.StringVar()
wpt_entry = tk.Entry(info_frame, textvariable=wpt_file_path, width=40)
wpt_entry.grid(row=1, column=1, columnspan=2, padx=5)
tk.Button(info_frame, text='参照', command=browse_wpt_file).grid(row=1, column=3, padx=5)

tk.Label(frame, text='Task definition:').pack(anchor='w')
task_text_box = tk.Text(frame, height=15, width=80)
task_text_box.pack(pady=5)

tk.Button(frame, text='   生成！   ', command=generate_file).pack(pady=10)

root.mainloop()
