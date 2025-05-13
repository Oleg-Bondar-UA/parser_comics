import os
import json
import re


def generate_toomics_json(base_dirs):
    comics_data = []

    for base_dir in base_dirs:
        comic_name = os.path.basename(base_dir)

        comic_data = {
            "title": comic_name,
            "originalTitle": comic_name,
            "description": "Minsung is not a guy to be called handsome. He is fat, and looks old, but he got lucky "
                           "to get married to the hot and beautiful Yura Jung. Yumi Jung her 20-year-old sister lives "
                           "with them and really hates Minsung. One day he learns a disappointing secret. Check this "
                           "story to know what he learned and how everything will go.",
            "thumbnail": "thumbnail.jpg",
            "thumbnailBackground": "thumbnail_background.jpg" if os.path.exists(
                os.path.join(base_dir, "thumbnail_background.jpg")) else None,
            "previewThumbnail": "preview-thumbnail.jpg" if os.path.exists(
                os.path.join(base_dir, "preview-thumbnail.jpg")) else None,
            "genres": ["In-Law", "END"],
            "tags": ["#cheating", "#hardcore", "#kindred", "#training", "#sisters"],
            "episodes": []
        }

        episode_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and d.isdigit()]
        episode_dirs.sort(key=lambda x: int(x))

        for episode_dir in episode_dirs:
            episode_path = os.path.join(base_dir, episode_dir)
            episode_number = episode_dir

            episode_images = []
            if os.path.exists(episode_path):
                image_files = [f for f in os.listdir(episode_path) if
                               f.startswith(f"episode_{episode_number}_") and f.endswith(".jpg")]
                image_files.sort(key=lambda x: int(x.split("_")[-1].split(".")[0]))
                episode_images = image_files

            episode_data = {
                "isLocked": False,
                "parentTitle": comic_name,
                "title": f"episode {episode_number}",
                "date": "",
                "thumbnail": "thumbnail.jpg" if os.path.exists(os.path.join(episode_path, "thumbnail.jpg")) else None,
                "slag": f"episode-{episode_number}",
                "images": episode_images
            }

            comic_data["episodes"].append(episode_data)

        comics_data.append(comic_data)

    with open("toomics_training_sister.json", "w", encoding="utf-8") as f:
        json.dump(comics_data, f, indent=2, ensure_ascii=False)

    print(f"JSON файл успішно створено: toomics_training_sister.json")


base_dirs = [
    "Training Sister In Law Part-A",
    "Training Sister In Law Part-B",
    "Training Sister In Law Part-C",
    "Training Sister In Law Part-D"
]

generate_toomics_json(base_dirs)