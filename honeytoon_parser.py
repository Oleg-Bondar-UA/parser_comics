import os
import time
import random
import base64
import json
import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import WebDriverException, TimeoutException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()


def is_valid_url(url):
    """Перевіряє чи є URL коректним"""
    try:
        if not url or not isinstance(url, str):
            return False
        url = url.strip()
        if not url:
            return False
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except:
        return False


def safe_navigate_to_url(driver, url, max_retries=3):
    """Безпечна навігація до URL з обробкою помилок"""
    if not url:
        print("❌ Порожній URL")
        return False

    url = url.strip()

    # Перевіряємо валідність URL
    if not is_valid_url(url):
        print(f"❌ Некоректний URL: {url}")
        return False

    for attempt in range(max_retries):
        try:
            print(f"🔄 Спроба {attempt + 1}/{max_retries} - завантаження URL: {url}")
            driver.get(url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            print(f"✅ Успішно завантажено: {url}")
            return True

        except WebDriverException as e:
            error_msg = str(e).lower()
            print(f"⚠️ WebDriver помилка (спроба {attempt + 1}): {error_msg}")

            if "unsupported protocol" in error_msg:
                print(f"❌ Невідповідний протокол в URL: {url}")
                return False
            elif "invalid argument" in error_msg or "invalid url" in error_msg:
                print(f"❌ Некоректний аргумент URL: {url}")
                return False

            if attempt < max_retries - 1:
                print(f"⏳ Очікування перед наступною спробою...")
                time.sleep(2 * (attempt + 1))
            else:
                print(f"❌ Всі спроби вичерпано для URL: {url}")

        except TimeoutException:
            print(f"⏰ Таймаут при завантаженні URL: {url}")
            if attempt < max_retries - 1:
                time.sleep(2)

        except Exception as e:
            print(f"❌ Несподівана помилка: {str(e)}")
            return False

    return False


session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
)
session.mount("https://", HTTPAdapter(max_retries=retries))

chrome_options = Options()
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 010.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

base_dir = "honeytoon"
os.makedirs(base_dir, exist_ok=True)

comics_data = []
failed_urls = []  # Для збереження невдалих URL

try:
    honeytoon_email = os.getenv("HONEYTOON_EMAIL")
    honeytoon_password = os.getenv("HONEYTOON_PASSWORD")

    # Login
    login_url = f"https://honeytoon.com/?email={honeytoon_email}&modal=sign-in"
    if not safe_navigate_to_url(driver, login_url):
        raise Exception("Не вдалося завантажити сторінку логіну")

    password_field = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "input.form-control.password"))
    )
    ActionChains(driver).move_to_element(password_field).perform()
    time.sleep(random.uniform(1, 3))

    for char in honeytoon_password:
        password_field.send_keys(char)
        time.sleep(random.uniform(0.2, 0.5))

    password_field.send_keys(Keys.RETURN)
    time.sleep(random.uniform(3, 5))

    with open(os.path.join(base_dir, "honeytoon_link_comics.txt"), "r", encoding="utf-8") as file:
        links = file.readlines()
        for link_index, link in enumerate(links, 1):
            link = link.strip()
            print(f"\n📖 Обробка коміксу {link_index}/{len(links)}: {link}")

            if not safe_navigate_to_url(driver, link):
                print(f"❌ Пропускаємо комікс через помилку завантаження: {link}")
                failed_urls.append({"type": "comic", "url": link, "reason": "Failed to load comic page"})
                continue

            try:
                comics = driver.find_elements(By.CLASS_NAME, "comic-book")
                if not comics:
                    print("⚠️ Не знайдено коміксів на сторінці")
                    continue

                for comic_index, comic in enumerate(comics, 1):
                    try:
                        original_title = comic.find_element(By.CLASS_NAME, "comic-book__title").text.strip()
                        print(f"🎭 Обробка коміксу: {original_title}")

                        # Format the title
                        display_title = original_title.replace("'", "")
                        display_title = ' '.join(word.capitalize() for word in display_title.split())

                        description = comic.find_element(By.CLASS_NAME, "comic-book__desc").text.strip()
                        genres = [genre.text.strip() for genre in
                                  comic.find_elements(By.CSS_SELECTOR, ".comic-book__labels .label__item")]
                        tags = [tag.text.strip() for tag in
                                comic.find_elements(By.CSS_SELECTOR, ".tags-wrapper .comic-tag")]
                        main_image = comic.find_element(By.CSS_SELECTOR, ".comic-book-img img").get_attribute("src")

                        # Clean directory name
                        dir_name = display_title
                        comic_dir = os.path.join(base_dir, dir_name)
                        os.makedirs(comic_dir, exist_ok=True)

                        # Create the comic data structure
                        comic_data = {
                            "title": display_title,
                            "originalTitle": original_title.upper(),
                            "description": description,
                            "thumbnail": "thumbnail.jpg",
                            "thumbnailBackground": "",
                            "previewThumbnail": "preview-thumbnail.jpg",
                            "genres": genres,
                            "tags": tags,
                            "episodes": []
                        }

                        # Збереження інформації про комікс
                        with open(os.path.join(comic_dir, "info.txt"), "w", encoding="utf-8") as file:
                            file.write(f"title: {display_title}\n")
                            file.write(f"original title: {original_title.upper()}\n")
                            file.write(f"description: {description}\n")
                            file.write(f"genres: {', '.join(genres) if genres else 'No genres found'}\n")
                            file.write(f"tags: {', '.join(tags) if tags else 'No tags found'}\n")

                        # Завантаження thumbnail
                        try:
                            image_path = os.path.join(comic_dir, "thumbnail.jpg")
                            response = session.get(main_image, stream=True, verify=False)
                            if response.status_code == 200:
                                with open(image_path, "wb") as img_file:
                                    for chunk in response.iter_content(1024):
                                        img_file.write(chunk)
                        except Exception as e:
                            print(f"⚠️ Не вдалося завантажити thumbnail: {e}")

                        # Пошук preview thumbnail
                        try:
                            search_field = WebDriverWait(driver, 20).until(
                                EC.presence_of_element_located((By.ID, "autoComplete"))
                            )

                            search_field.clear()
                            search_field.send_keys(original_title)
                            time.sleep(2)

                            search_result = WebDriverWait(driver, 20).until(
                                EC.presence_of_element_located((By.ID, "autoComplete_result_0"))
                            )
                            preview_image = search_result.find_element(By.TAG_NAME, "img").get_attribute("src")
                            preview_image_path = os.path.join(comic_dir, "preview-thumbnail.jpg")
                            response = requests.get(preview_image, stream=True)
                            if response.status_code == 200:
                                with open(preview_image_path, "wb") as img_file:
                                    for chunk in response.iter_content(1024):
                                        img_file.write(chunk)
                        except Exception as e:
                            print(f"⚠️ Не вдалося завантажити preview thumbnail: {e}")

                        # Збір посилань на епізоди
                        links_file_path = os.path.join(comic_dir, "links_episode.txt")
                        episode_thumbnails = {}

                        try:
                            with open(links_file_path, "w", encoding="utf-8") as links_file:
                                comic_list = driver.find_element(By.CSS_SELECTOR,
                                                                 "body > main > section.section.comic-list .comic-list-items")
                                episodes = comic_list.find_elements(By.CLASS_NAME, "comic-list__item")

                                for index, episode in enumerate(episodes, start=1):
                                    link = episode.get_attribute("href")
                                    if link and is_valid_url(link):
                                        try:
                                            image = episode.find_element(By.CSS_SELECTOR,
                                                                         ".comic-list__img img").get_attribute("src")
                                            episode_thumbnails[link] = image
                                        except:
                                            print(f"⚠️ Не вдалося знайти thumbnail для епізоду {index}")
                                        links_file.write(f"{link}\n")
                                    else:
                                        print(f"⚠️ Некоректне посилання на епізод {index}: {link}")
                        except Exception as e:
                            print(f"❌ Помилка при зборі посилань на епізоди: {e}")
                            continue

                        # Обробка епізодів
                        try:
                            with open(links_file_path, "r", encoding="utf-8") as links_file:
                                episode_links = links_file.readlines()
                                episode_counter = 1

                                for episode_index, episode_link in enumerate(episode_links, start=1):
                                    episode_link = episode_link.strip()

                                    print(f"📺 Обробка епізоду {episode_index}/{len(episode_links)}")

                                    # Безпечна навігація до епізоду
                                    if not safe_navigate_to_url(driver, episode_link):
                                        print(f"❌ Пропускаємо епізод через помилку завантаження: {episode_link}")
                                        failed_urls.append({
                                            "type": "episode",
                                            "url": episode_link,
                                            "comic": display_title,
                                            "reason": "Failed to load episode page"
                                        })
                                        continue

                                    try:
                                        time.sleep(5)

                                        header_title = driver.find_element(By.CLASS_NAME,
                                                                           "header-episode__title-number").text.strip()
                                        print(f"📄 Заголовок епізоду: {header_title}")

                                        # Пропускаємо прологи
                                        if "prologue" in header_title.lower():
                                            print(f"⏭️ Пропускаємо пролог: {header_title}")
                                            continue

                                        # Створюємо папку для епізоду
                                        episode_dir = os.path.join(comic_dir, f"{episode_counter:03d}")
                                        os.makedirs(episode_dir, exist_ok=True)

                                        # Завантажуємо thumbnail епізоду
                                        if episode_link in episode_thumbnails:
                                            try:
                                                image_path = os.path.join(episode_dir, "thumbnail.jpg")
                                                response = session.get(episode_thumbnails[episode_link], stream=True,
                                                                       verify=False)
                                                if response.status_code == 200:
                                                    with open(image_path, "wb") as img_file:
                                                        for chunk in response.iter_content(1024):
                                                            img_file.write(chunk)
                                            except Exception as e:
                                                print(f"⚠️ Не вдалося завантажити thumbnail епізоду: {e}")

                                        # Пошук зображень епізоду
                                        try:
                                            single_inner = WebDriverWait(driver, 20).until(
                                                EC.presence_of_element_located((By.CLASS_NAME, "single-inner"))
                                            )

                                            images = single_inner.find_elements(By.TAG_NAME, "img")
                                            episode_images = []

                                            for index, image in enumerate(images):
                                                image_url = driver.execute_script(
                                                    "return arguments[0].currentSrc || arguments[0].src;", image)
                                                image_filename = f"episode_{episode_counter:03d}_{index + 1:03d}.jpg"
                                                episode_images.append(image_filename)

                                                try:
                                                    if image_url.startswith("data:image/"):
                                                        header, encoded = image_url.split(",", 1)
                                                        image_data = base64.b64decode(encoded)
                                                        image_path = os.path.join(episode_dir, image_filename)
                                                        with open(image_path, "wb") as img_file:
                                                            img_file.write(image_data)
                                                    else:
                                                        response = session.get(image_url, stream=True, verify=False)
                                                        if response.status_code == 200:
                                                            image_path = os.path.join(episode_dir, image_filename)
                                                            with open(image_path, "wb") as img_file:
                                                                for chunk in response.iter_content(1024):
                                                                    img_file.write(chunk)

                                                    print(f"Saved image: {image_path} (URL: {image_url})")
                                                except requests.exceptions.SSLError as e:
                                                    print(f"SSL error for URL {image_url}: {e}")
                                                except Exception as e:
                                                    print(f"Failed to save image from URL {image_url}: {e}")

                                            # Add episode data to comic_data structure
                                            episode_data = {
                                                "parentTitle": display_title,
                                                "title": f"episode {episode_counter:03d}",
                                                "slag": f"episode-{episode_counter:03d}",
                                                "date": "",
                                                "thumbnail": "thumbnail.jpg",
                                                "images": episode_images
                                            }
                                            comic_data["episodes"].append(episode_data)

                                            episode_counter += 1

                                        except Exception as e:
                                            print(f"❌ Помилка при обробці зображень епізоду: {e}")
                                            continue

                                    except Exception as e:
                                        print(f"❌ Помилка при обробці епізоду {episode_link}: {e}")
                                        failed_urls.append({
                                            "type": "episode",
                                            "url": episode_link,
                                            "comic": display_title,
                                            "reason": f"Episode processing error: {str(e)}"
                                        })
                                        continue

                        except Exception as e:
                            print(f"❌ Помилка при читанні файлу з епізодами: {e}")

                        # Add the comic data to the comics_data list
                        comics_data.append(comic_data)
                        print(f"✅ Комікс '{display_title}' успішно оброблено")

                    except Exception as e:
                        print(f"❌ Помилка при обробці коміксу: {e}")
                        continue

            except Exception as e:
                print(f"❌ Загальна помилка при обробці сторінки коміксів: {e}")
                continue

    # Збереження результатів
    with open(os.path.join(base_dir, "stolen_taste.json"), "w", encoding="utf-8") as json_file:
        json.dump(comics_data, json_file, indent=2, ensure_ascii=False)

    # Збереження невдалих URL
    if failed_urls:
        with open(os.path.join(base_dir, "failed_urls.json"), "w", encoding="utf-8") as failed_file:
            json.dump(failed_urls, failed_file, indent=2, ensure_ascii=False)
        print(f"\n⚠️ {len(failed_urls)} URL не вдалося обробити. Збережено в failed_urls.json")

    print(f"\n✅ Програма завершена. Оброблено {len(comics_data)} коміксів.")

except Exception as e:
    print(f"❌ Критична помилка: {e}")
finally:
    driver.quit()
    print("🔒 Браузер закрито")