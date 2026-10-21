from pathlib import Path
import platform, os, json

USER_INFORMATION = {}
BASE_UI_URL = "https://ios-ui.snaipix.com/"
CODE = 1000000

ROOT_PATH = Path("C:/BelfortUniq2")
if platform.system() == "Darwin": ROOT_PATH = Path.home() / "BelfortUniq2"
if not ROOT_PATH.exists(): ROOT_PATH.mkdir(parents=True)

class Config:

    def __init__(self, file, dir=None):
        if dir is None:
            dir = ROOT_PATH / "configs"

        self.data = {}
        self.file = file
        self.dir = dir

        if not os.path.exists(dir):
            os.makedirs(dir)

    def edit(self, key, value):
        self.data[key] = value
        self.save()

    def get(self, key, default_value):
        return self.data.get(key, default_value)

    def to_json(self):
        return json.dumps(self.data, indent=4)

    def from_json(self, data):
        try:
            self.data = json.loads(data)
        except Exception:
            self.data = {}

        return self

    def delete(self):
        if os.path.exists(self.dir / self.file):
            os.remove(self.dir / self.file)
            self.data = {}

        return self

    def save(self):
        if not self.file.endswith(".json"):
            self.file += ".json"

        with open(self.dir / self.file, "w") as f:
            f.write(self.to_json())

        return self

    def load(self):
        if not self.file.endswith(".json"):
            self.file += ".json"

        if os.path.exists(self.dir / self.file):
            with open(self.dir / self.file, "r") as f:
                self.from_json(f.read())

        return self


presets_config = Config("presets.json").load()
