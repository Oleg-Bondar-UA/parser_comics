import os
import re
import shutil


def rename_directories_and_images(base_dir):
    try:
        dir_list = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]

        dir_list.sort(key=lambda x: int(x) if x.isdigit() else float('inf'))

        print(f"Знайдено директорії: {dir_list}")

        dir_mapping = {}
        for new_index, old_dir in enumerate(dir_list, start=1):
            dir_mapping[old_dir] = str(new_index)

        print(f"Мапа перейменування: {dir_mapping}")

        for old_dir, new_dir in dir_mapping.items():
            old_path = os.path.join(base_dir, old_dir)
            temp_path = os.path.join(base_dir, f"temp_{new_dir}")
            new_path = os.path.join(base_dir, new_dir)

            print(f"Перейменовую директорію {old_dir} → {new_dir}")

            shutil.move(old_path, temp_path)

            os.makedirs(new_path, exist_ok=True)

            for filename in os.listdir(temp_path):
                old_file_path = os.path.join(temp_path, filename)

                new_filename = re.sub(r'[Ee]pisode_(\d+)_(\d+)', f'episode_{new_dir}_\\2', filename)
                new_file_path = os.path.join(new_path, new_filename)

                print(f"  Перейменовую файл {filename} → {new_filename}")

                shutil.move(old_file_path, new_file_path)

            shutil.rmtree(temp_path, ignore_errors=True)

        print(f"Успішно перейменовані директорії та файли в {base_dir}")

    except Exception as e:
        print(f"Помилка: {str(e)}")


# Приклад використання
comic_dir = "Training Sister In Law Part-D"
rename_directories_and_images(comic_dir)