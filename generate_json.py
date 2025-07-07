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
            "description": "",
            "thumbnail": "thumbnail.jpg",
            "thumbnailBackground": "thumbnail_background.jpg" if os.path.exists(
                os.path.join(base_dir, "thumbnail_background.jpg")) else None,
            "previewThumbnail": "preview-thumbnail.jpg" if os.path.exists(
                os.path.join(base_dir, "preview-thumbnail.jpg")) else None,
            "genres": [],
            "tags": ["#Outdoors", "#Cougar"],
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
                               f.startswith(f"episode_{episode_number}_") and f.endswith(".webp")]
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

    with open(f"{comic_name}.json", "w", encoding="utf-8") as f:
        json.dump(comics_data, f, indent=2, ensure_ascii=False)

    print(f"JSON файл успішно створено: toomics_training_sister.json")


base_dirs = [
    "Study Dates",
]

generate_toomics_json(base_dirs)