import customtkinter as ctk
import yt_dlp, threading, re, os, json, sys, requests
from tkinter import filedialog

# --- 核心路径锁定 ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
FFMPEG_BIN = os.path.join(BASE_DIR, "bin") 

# 设置主题
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MyLogger:
    def __init__(self, textbox):
        self.textbox = textbox
    def write(self, msg):
        # 彻底过滤日志里的 ANSI 乱码
        clean_msg = re.sub(r'\x1b\[[0-9;]*m', '', msg)
        self.textbox.after(0, lambda: self.textbox.insert("end", clean_msg + "\n"))
        self.textbox.after(0, lambda: self.textbox.see("end"))
    def debug(self, msg): self.write(msg)
    def warning(self, msg): self.write(f"⚠️ {msg}")
    def error(self, msg): self.write(f"🚨 {msg}")

class YouTubeDownloaderPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YouTube 全能爬虫 Pro v4.4")
        self.geometry("750x920") 
        self.grid_columnconfigure(0, weight=1)
        
        self.conf = self.load_config()

        # 联网公告
        self.msg_label = ctk.CTkLabel(self, text="正在同步在线公告...", text_color="gray")
        self.msg_label.grid(row=0, column=0, pady=(10, 0))
        threading.Thread(target=self.check_online_info, daemon=True).start()

        self.label = ctk.CTkLabel(self, text="YouTube 全能爬虫系统", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.grid(row=1, column=0, padx=20, pady=(10, 10))

        # 批量输入
        self.url_text = ctk.CTkTextbox(self, width=680, height=100)
        self.url_text.grid(row=2, column=0, padx=20, pady=5)
        
        # 路径选择
        self.path_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.path_frame.grid(row=3, column=0, padx=20, pady=5)
        self.download_path_var = ctk.StringVar(value=self.conf['last_path']) 
        ctk.CTkEntry(self.path_frame, width=560, textvariable=self.download_path_var).pack(side="left", padx=(0, 10))
        ctk.CTkButton(self.path_frame, text="📁 选路径", width=80, command=self.select_path, fg_color="#34495e").pack(side="left")

        # 代理区
        self.proxy_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.proxy_frame.grid(row=4, column=0, padx=20, pady=5)
        self.proxy_enabled_var = ctk.BooleanVar(value=self.conf.get('proxy_enabled', False))
        ctk.CTkSwitch(self.proxy_frame, text="启用代理", variable=self.proxy_enabled_var, command=self.toggle_proxy).pack(side="left", padx=5)
        self.proxy_addr_var = ctk.StringVar(value=self.conf['last_proxy'])
        self.proxy_entry = ctk.CTkEntry(self.proxy_frame, width=450, textvariable=self.proxy_addr_var)
        self.proxy_entry.pack(side="left", padx=5)
        self.toggle_proxy()

        # 开关区
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.grid(row=5, column=0, padx=20, pady=10)
        self.sub_var = ctk.BooleanVar(value=self.conf.get('sub', False))
        self.audio_var = ctk.BooleanVar(value=self.conf.get('audio', False))
        self.thumb_var = ctk.BooleanVar(value=self.conf.get('thumb', False))
        self.shutdown_var = ctk.BooleanVar(value=self.conf.get('shutdown', False))

        ctk.CTkSwitch(self.ctrl_frame, text="内嵌字幕", variable=self.sub_var).pack(side="left", padx=5)
        ctk.CTkSwitch(self.ctrl_frame, text="仅音频", variable=self.audio_var).pack(side="left", padx=5)
        ctk.CTkSwitch(self.ctrl_frame, text="保存封面", variable=self.thumb_var).pack(side="left", padx=5)
        ctk.CTkSwitch(self.ctrl_frame, text="任务完关机", variable=self.shutdown_var).pack(side="left", padx=5)

        self.quality_var = ctk.StringVar(value=self.conf.get('quality', "最高画质"))
        ctk.CTkOptionMenu(self.ctrl_frame, values=["最高画质", "2160p (4K)", "1440p (2K)", "1080p", "720p"], variable=self.quality_var, width=120).pack(side="left", padx=5)

        # 下载按钮
        self.download_btn = ctk.CTkButton(self, text="🚀 开启全能爬取模式", height=50, command=self.start_batch_download, font=ctk.CTkFont(size=18, weight="bold"))
        self.download_btn.grid(row=6, column=0, padx=20, pady=20)

        # 进度显示（此处就是会出现乱码的地方，我们已修复）
        self.status_label = ctk.CTkLabel(self, text="准备就绪", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_label.grid(row=7, column=0)
        self.log_box = ctk.CTkTextbox(self, width=680, height=200, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_box.grid(row=8, column=0, padx=20, pady=10)

    def toggle_proxy(self):
        self.proxy_entry.configure(state="normal" if self.proxy_enabled_var.get() else "disabled")

    def check_online_info(self):
        try:
            url = "https://raw.githubusercontent.com/xiaofeitongxueaL/YoutubeDownload/refs/heads/main/info.json"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                self.after(0, lambda: self.msg_label.configure(text=data.get("notice", ""), text_color="cyan"))
        except: pass

    def load_config(self):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        default = {"last_path": desktop, "last_proxy": "http://127.0.0.1:7890", "proxy_enabled": False, "sub": False, "audio": False, "thumb": False, "shutdown": False, "quality": "最高画质"}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "VS Code" in data.get("last_path", ""): data["last_path"] = desktop
                    return {**default, **data}
            except: pass
        return default

    def save_config(self):
        data = {"last_path": self.download_path_var.get(), "last_proxy": self.proxy_addr_var.get(), "proxy_enabled": self.proxy_enabled_var.get(), "sub": self.sub_var.get(), "audio": self.audio_var.get(), "thumb": self.thumb_var.get(), "shutdown": self.shutdown_var.get(), "quality": self.quality_var.get()}
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except: pass

    def select_path(self):
        folder = filedialog.askdirectory()
        if folder: self.download_path_var.set(folder)

    def start_batch_download(self):
        self.save_config()
        urls = [u.strip() for u in self.url_text.get("0.0", "end").split("\n") if u.strip()]
        if not urls: return
        self.download_btn.configure(state="disabled")
        self.log_box.delete("0.0", "end")
        threading.Thread(target=self.batch_task, args=(urls,), daemon=True).start()

    # --- 核心修复：清洗进度字符串中的 ANSI 乱码 ---
    def update_ui_status(self, d):
        if d['status'] == 'downloading':
            # 1. 清洗百分比
            p = d.get('_percent_str', '0%')
            clean_p = re.sub(r'\x1b\[[0-9;]*m', '', p)

            # 2. 清洗速度 (修复你图片里的那个乱码)
            s = d.get('_speed_str', 'N/A')
            clean_s = re.sub(r'\x1b\[[0-9;]*m', '', s)

            # 3. 清洗剩余时间 (以防万一)
            eta = d.get('_eta_str', 'N/A')
            clean_eta = re.sub(r'\x1b\[[0-9;]*m', '', eta)

            # 更新到界面
            self.after(0, lambda: self.status_label.configure(
                text=f"进度: {clean_p} | 速度: {clean_s} | 剩余: {clean_eta}"
            ))
        elif d['status'] == 'finished':
            self.after(0, lambda: self.status_label.configure(text="下载完成，正在合并文件...", text_color="yellow"))

    def batch_task(self, urls):
        q_map = {"最高画质": "bestvideo+bestaudio/best", "2160p (4K)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]", "1440p (2K)": "bestvideo[height<=1440]+bestaudio/best[height<=1440]", "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]", "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]"}
        active_proxy = self.proxy_addr_var.get() if self.proxy_enabled_var.get() else None

        for i, url in enumerate(urls, 1):
            # 1. 确定后缀
            is_audio = self.audio_var.get()
            suffix = "_音频" if is_audio else ("_带字幕" if self.sub_var.get() else "_原版")
            
            # 2. 动态构造文件名模板
            # 如果是视频，文件名末尾加上 _分辨率p (例如: 视频标题_原版_1080p.mp4)
            if is_audio:
                name_tmpl = f'%(title)s{suffix}.%(ext)s'
            else:
                name_tmpl = f'%(title)s{suffix}_%(height)sp.%(ext)s'

            ydl_opts = {
                'proxy': active_proxy, 
                'ffmpeg_location': FFMPEG_BIN, 
                'outtmpl': os.path.join(self.download_path_var.get(), name_tmpl), # 使用新模板
                'noplaylist': True, 
                'quiet': True, 
                'no_warnings': True,
                'logger': MyLogger(self.log_box),
                'progress_hooks': [self.update_ui_status],
                
                # 确保合并和元数据开启
                'merge_output_format': 'mp4',
                'postprocessors': [
                    {'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'},
                    {'key': 'FFmpegMetadata'},
                ],
            }

            if self.thumb_var.get():
                ydl_opts.update({'writethumbnail': True})
                ydl_opts['postprocessors'].append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
            
            if self.audio_var.get():
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'].insert(0, {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'})
            else:
                ydl_opts['format'] = q_map.get(self.quality_var.get(), "bestvideo+bestaudio/best")
                ydl_opts['postprocessors'].append({'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'})
                if self.sub_var.get():
                    ydl_opts.update({'writesubtitles': True, 'writeautomaticsub': True, 'subtitleslangs': ['zh-Hans', 'en'], 'embedsubs': True})
                    ydl_opts['postprocessors'].extend([{'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'}, {'key': 'FFmpegEmbedSubtitle'}])

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
            except Exception as e:
                clean_err = re.sub(r'\x1b\[[0-9;]*m', '', str(e))
                self.after(0, lambda msg=clean_err[:50]: self.log_box.insert("end", f"🚨 失败: {msg}\n"))
        
        self.after(0, lambda: self.status_label.configure(text="✨ 任务全部完成！", text_color="#2ecc71"))
        self.after(0, lambda: self.download_btn.configure(state="normal"))
        if self.shutdown_var.get(): os.system("shutdown /s /t 60")

if __name__ == "__main__":
    YouTubeDownloaderPro().mainloop()