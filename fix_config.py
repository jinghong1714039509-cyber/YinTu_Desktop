# fix_config.py
import os
import json
from pathlib import Path

# 1. 找到用户目录
config_dir = Path.home() / ".qfluentwidgets"
config_dir.mkdir(parents=True, exist_ok=True)

# 2. 强制写入配置：backend = PySide6
config_file = config_dir / "config.json"

data = {
    "backend": "PySide6",
    "themeColor": "#009faa",
    "theme": "dark"
}

with open(config_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)

print(f"✅ 配置文件已生成: {config_file}")
print(f"内容: {data}")
print("现在库应该知道该用谁了。")