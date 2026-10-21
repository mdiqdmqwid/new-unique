import webview, win32gui, win32con, ctypes, time, platform, json, os, colorama, subprocess, shutil, threading, requests, configs, asyncio, uuid, logging, uvicorn, webbrowser, hashlib, random, string, binascii, base64, datetime, curl_cffi, mimetypes, pyperclip, unique, functools, traceback
from pathlib import Path
from Crypto import Random
from Crypto.Cipher import AES
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware


if __name__ == "__main__":

    app = FastAPI()
    unique_previews = {}

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex="https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/get_unique_preview/{imageUuid}")
    async def get_unique_preview(imageUuid: str):
        data = unique_previews[imageUuid]
        del unique_previews[imageUuid]

        return Response(content=data, media_type="image/jpeg")




    base_loop = asyncio.new_event_loop()


    def start_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()


    class WebViewAPI:

        def __init__(self):
            self.presets_config = configs.presets_config.data
            self._unique_jobs: dict[str, unique.UniqueJob] = {}
            self._command_thread_started = False

        def close_app(self):
            webview.active_window().destroy()

        def minimize_app(self):
            webview.active_window().minimize()

        def maximize_app(self):
            webview.active_window().maximize()

        def restore_app(self):
            webview.active_window().restore()

        def get_session(self):
            return configs.USER_INFORMATION

        def new_session(self):
            return configs.USER_INFORMATION

        def check_session(self, is_first: bool = False):
            return [True, configs.USER_INFORMATION]

        def open_main_page(self):
            self.load_presets_config()

            webview.windows[0].set_title("Belfort Unique")
            webview.windows[0].resize(1203, 717)
            webview.windows[0].resize(1203, 717)
            webview.windows[0].run_js("window.location.hash = '#/unique_page'")

        def load_presets_config(self):
            self.presets_config = configs.presets_config.data

        def get_presets_list(self):
            return self.presets_config

        def delete_preset(self, name: str):
            if name in self.presets_config:
                del self.presets_config[name]
                self.delete_presets_config(name)
            return self.get_presets_list()

        def new_preset(self, name: str):
            unique_name = str(uuid.uuid4())
            self.presets_config[unique_name] = {"name": name}
            asyncio.run_coroutine_threadsafe(self.save_presets_config(unique_name, {"name": name}), base_loop)
            return unique_name

        def delete_presets_config(self, uuid: str, params: list[str] | None = None):
            if uuid in configs.presets_config.data:
                if params is not None:
                    for param in params:
                        if param in configs.presets_config.data[uuid]:
                            del configs.presets_config.data[uuid][param]
                else:
                    del configs.presets_config.data[uuid]
            configs.presets_config.save()

        async def save_presets_config(self, uuid: str, data: dict):
            if uuid in configs.presets_config.data:
                configs.presets_config.data[uuid] |= data
            else:
                configs.presets_config.data[uuid] = data
            configs.presets_config.save()

        def launch_url(self, url: str):
            webbrowser.open(url)

        def clipboard_get(self):
            return pyperclip.paste()

        def clipboard_set(self, text):
            pyperclip.copy(text)
            return True

        def get_preset(self, unique_name: str):
            return self.presets_config.get(unique_name)

        def update_presets_param(self, name: str, param: str, value):
            if name not in self.presets_config: return None

            self.presets_config[name][param] = value
            asyncio.run_coroutine_threadsafe(self.save_presets_config(name, {param: value}), base_loop)

            return self.presets_config[name]

        def reset_presets_params(self, name: str, params: list[str]):
            if name not in self.presets_config: return None

            self.delete_presets_config(name, params)

            return self.presets_config[name]

        def open_file(self, file: str):
            if platform.system() == "Windows":
                os.startfile(file)
            elif platform.system() == "Darwin":
                subprocess.run(["open", file])
            else:
                subprocess.run(["xdg-open", file])

        def open_folder_dialog(self, allow_multiple: bool = False):
            return webview.active_window().create_file_dialog(webview.FileDialog.FOLDER, allow_multiple=allow_multiple)

        def get_publish_files(self, name: str, types: list[str] = [".jpg", ".png", ".jpeg"], limit: int = 5, recursive_folders: bool = False):
            empty = {"file_paths": [], "unique_type": "image"}
            if name not in self.presets_config: return empty

            publish_path = self.presets_config[name].get("creo_path")
            if not publish_path or not os.path.isdir(publish_path): return empty

            files = []
            if recursive_folders:
                for root, _, filenames in os.walk(publish_path):
                    for filename in sorted(filenames):
                        if filename.lower().endswith(tuple(types)) and "_tmp." not in filename.lower():
                            files.append(os.path.join(root, filename))
            else:
                files = [os.path.join(publish_path, v) for v in sorted(os.listdir(publish_path)) if os.path.isfile(os.path.join(publish_path, v)) and v.lower().endswith(tuple(types))]

            is_video = any(v.lower().endswith(unique.VIDEO_EXTENSIONS) for v in files)

            return {"file_paths": files[:limit], "unique_type": "video" if is_video else "image"}

        def _video_preview(self, file: str):
            no_window = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            preview = {"data": "", "duration": "0:00", "file": file, "size_mb": round(os.path.getsize(file) / 1024 / 1024, 2)}

            try:
                duration = float(subprocess.run(
                    [unique.FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file],
                    capture_output=True, text=True, creationflags=no_window
                ).stdout.strip() or 0)
                preview["duration"] = f"{int(duration // 60)}:{int(duration % 60):02d}"

                frame = subprocess.run(
                    [unique.FFMPEG_PATH, "-v", "error", "-i", file, "-frames:v", "1", "-vf", "scale=328:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                    capture_output=True, creationflags=no_window
                ).stdout
                if frame:
                    preview["data"] = f"data:image/jpeg;base64,{base64.b64encode(frame).decode()}"
            except Exception:
                pass

            return preview

        def get_file_preview(self, file_path: list[str]):
            previews = []
            if not file_path: return previews

            for file in file_path:
                if not os.path.isfile(file): continue

                if file.lower().endswith((".photo.unique", ".video.unique")):
                    with open(file, "r", encoding="utf-8") as f:
                        try:
                            previews.append({"data": "", "duration": "", "size_mb": 0, "is_video": file.lower().endswith(".video.unique"), "is_layer": True, "layer_uuid": os.path.basename(file).split(".")[0], "layer": json.load(f)})
                        except Exception: pass
                elif file.lower().endswith((".png", ".jpg", ".jpeg")):
                    mime_type = mimetypes.guess_type(file)[0] or "image/png"

                    with open(file, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("utf-8")

                    previews.append({"data": f"data:{mime_type};base64,{encoded}", "duration": "", "file": file, "size_mb": round(os.path.getsize(file) / 1024 / 1024, 2)})
                elif file.lower().endswith(unique.VIDEO_EXTENSIONS):
                    previews.append(self._video_preview(file))

            return previews

        def get_unique_photo_layers(self):
            return unique.PHOTO_LAYERS

        def get_photo_editor_preview(self, layers: list):
            return base64.b64encode(unique.sync_get_preview(layers)).decode()

        def get_photo_editor_preview_url(self, layers: list):
            data = str(uuid.uuid4())
            unique_previews[data] = unique.sync_get_preview(layers)
            return data

        def _preset_creo_path(self, preset_name: str) -> Path | None:
            if preset_name not in self.presets_config: return None

            creo_path = self.presets_config[preset_name].get("creo_path")
            if not creo_path or not os.path.isdir(creo_path): return None

            return Path(creo_path)

        def normalize_layer_uuid(self, layer_uuid: str):
            name = Path(str(layer_uuid)).name

            for extension in (".photo.unique", ".video.unique"):
                if name.endswith(extension):
                    name = name[:-len(extension)]

            if "_" in name:
                index, rest = name.split("_", 1)
                if index.isdigit():
                    name = rest

            return name

        def _save_layer_to_preset(self, layer_uuid: str, layers: list, preset_name: str, extension: str):
            if not layer_uuid: return False

            base_path = self._preset_creo_path(preset_name)
            if base_path is None: return False

            layer_uuid = self.normalize_layer_uuid(layer_uuid)
            used_indexes = set()

            for file in base_path.glob(f"*{extension}"):
                if "_" not in file.name: continue

                index, rest = file.name.split("_", 1)
                if rest == f"{layer_uuid}{extension}":
                    with open(file, "w", encoding="utf-8") as f:
                        json.dump(layers, f, ensure_ascii=False)
                    return True

                if index.isdigit():
                    used_indexes.add(int(index))

            index = 0
            while index in used_indexes:
                index += 1

            with open(base_path / f"{index}_{layer_uuid}{extension}", "w", encoding="utf-8") as f:
                json.dump(layers, f, ensure_ascii=False)

            return True

        def save_photo_layer_to_preset(self, layer_uuid: str, layers: list, preset_name: str):
            return self._save_layer_to_preset(layer_uuid, layers, preset_name, ".photo.unique")

        def save_video_layer_to_preset(self, layer_uuid: str, layers: list, preset_name: str):
            return self._save_layer_to_preset(layer_uuid, layers, preset_name, ".video.unique")

        def _delete_layer_file(self, file: str, preset_name: str, extension: str):
            if not file: return False

            base_path = self._preset_creo_path(preset_name)
            if base_path is None: return False

            name = Path(file).name
            if not name.endswith(extension):
                name = f"{name}{extension}"

            if not (base_path / name).is_file(): return False

            try:
                os.unlink(base_path / name)
            except Exception: pass

            return True

        def delete_photo_layer_file(self, file: str, preset_name: str):
            return self._delete_layer_file(file, preset_name, ".photo.unique")

        def delete_video_layer_file(self, file: str, preset_name: str):
            return self._delete_layer_file(file, preset_name, ".video.unique")

        def _swap_layer_files(self, file_one: str, file_two: str, preset_name: str, extension: str):
            if not file_one or not file_two: return False

            base_path = self._preset_creo_path(preset_name)
            if base_path is None: return False

            name_one = Path(file_one).name
            name_two = Path(file_two).name
            if not name_one.endswith(extension): name_one = f"{name_one}{extension}"
            if not name_two.endswith(extension): name_two = f"{name_two}{extension}"

            path_one = base_path / name_one
            path_two = base_path / name_two
            if not path_one.is_file() or not path_two.is_file(): return False
            if "_" not in name_one or "_" not in name_two: return False

            index_one, rest_one = name_one.split("_", 1)
            index_two, rest_two = name_two.split("_", 1)
            if not index_one.isdigit() or not index_two.isdigit(): return False

            new_path_one = base_path / f"{index_two}_{rest_one}"
            new_path_two = base_path / f"{index_one}_{rest_two}"
            temp_path = base_path / f"__temp__{uuid.uuid4().hex}_{rest_one}"

            path_one.rename(temp_path)
            path_two.rename(new_path_two)
            temp_path.rename(new_path_one)

            return {
                "file_one": new_path_one.name.removesuffix(extension),
                "file_two": new_path_two.name.removesuffix(extension),
                "name_one": new_path_one.name,
                "name_two": new_path_two.name
            }

        def drag_drop_photo_layer_file(self, file_one: str, file_two: str, preset_name: str):
            return self._swap_layer_files(file_one, file_two, preset_name, ".photo.unique")

        def drag_drop_video_layer_file(self, file_one: str, file_two: str, preset_name: str):
            return self._swap_layer_files(file_one, file_two, preset_name, ".video.unique")

        def preview_video(self, preset: dict):
            return unique.preview_unique_video(preset)

        def start_unique(self, preset_name: str, output_dir: str, files_count: int, threads: int):
            if preset_name not in self.presets_config: return {"error": "preset_not_found"}

            job = self._unique_jobs.get(preset_name)
            if job is not None and job.running: return job.status()

            job = unique.UniqueJob(self.presets_config[preset_name], output_dir, files_count, threads)
            self._unique_jobs[preset_name] = job
            job.start()

            return job.status()

        def stop_unique(self, preset_name: str):
            job = self._unique_jobs.get(preset_name)
            if job is None: return None

            job.stop()
            return job.status()

        def get_unique_status(self, preset_name: str):
            job = self._unique_jobs.get(preset_name)
            if job is None: return None

            return job.status()


    def on_closed_event():

        for v in list(webview.windows):
            v.destroy()


    def on_loaded(window: webview.Window):

        window.events.closed += on_closed_event

        while True:
            try:
                hwnd = window.native.Handle.ToInt64()
                win32gui.ShowWindow(hwnd, 9)
                try:
                    win32gui.SetForegroundWindow(hwnd)
                    break
                except Exception:
                    pass

                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
                win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
                break
            except:
                time.sleep(0.1)


    def uvicorn_thread():

        logging.getLogger("uvicorn").disabled = True
        logging.getLogger("uvicorn.error").disabled = True
        logging.getLogger("uvicorn.access").disabled = True
        uvicorn.run(app, host="0.0.0.0", port=9090, log_level="error")


    def windows_sleep_disable():
        while True:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
            time.sleep(30)

    webview_api = WebViewAPI()

    if platform.system() == "Windows":
        threading.Thread(target=windows_sleep_disable, daemon=True).start()

    threading.Thread(target=start_loop, args=(base_loop,), daemon=True).start()
    threading.Thread(target=uvicorn_thread, daemon=True).start()

    configs.USER_INFORMATION = {"session": "local", "username": "local"}

    if not os.path.exists(configs.ROOT_PATH / "ffmpeg") and platform.system() != "Darwin":
        os.makedirs(configs.ROOT_PATH / "ffmpeg")
        os.makedirs(configs.ROOT_PATH / "ffmpeg/presets")
        os.makedirs(configs.ROOT_PATH / "ffmpeg/bin")

        print("Идет установка ffmpeg...")
        files = ["LICENSE", "README.txt", "presets/libvpx-360p.ffpreset", "presets/libvpx-720p.ffpreset", "bin/ffmpeg.exe",
                 "bin/ffplay.exe", "bin/ffprobe.exe", "presets/libvpx-720p50_60.ffpreset", "presets/libvpx-1080p.ffpreset",
                 "presets/libvpx-1080p50_60.ffpreset"]

        for file in files:
            print(f"Идет установка файла '{file}'")
            with open(configs.ROOT_PATH / f"ffmpeg" / file, "wb") as f:
                f.write(requests.get(f"https://api2.snaipix.com/static/ffmpeg/{file}", headers={"content-type": "text/plain", "user-agent": f"BelfortUniq Client {configs.CODE}"}, allow_redirects=True).content)

    if platform.system() == "Darwin" and shutil.which("ffmpeg") is None:
        print("Установка ffmpeg через brew...")

        if shutil.which("brew") is None:
            print(colorama.Fore.RED + "Brew не установлен. Установите его и повторите попытку." + colorama.Fore.RESET)
        else:
            subprocess.Popen(
                ["brew", "install", "ffmpeg"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ).wait()

    webview.settings["DRAG_REGION_DIRECT_TARGET_ONLY"] = True
    window = webview.create_window(
        "Belfort Unique",
        url=f"{configs.BASE_UI_URL}#/auth?unique=1",
        width=357,
        height=546,
        resizable=False,
        frameless=True,
        js_api=webview_api,
        easy_drag=False,
        text_select=True
    )
    webview.start(on_loaded, window, debug="http://" in configs.BASE_UI_URL, icon="icon.ico")