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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
)
session.mount("https://", HTTPAdapter(max_retries=retries))

chrome_options = Options()
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)
service = Service("chromedrivers/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)

base_dir = "honeytoon"
os.makedirs(base_dir, exist_ok=True)

comics_data = []

try:
    honeytoon_email = os.getenv("HONEYTOON_EMAIL")
    honeytoon_password = os.getenv("HONEYTOON_PASSWORD")
    # Login
    driver.get(f"https://honeytoon.com/?email={honeytoon_email}&modal=sign-in")
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

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
        for link in links:
            driver.get(link.strip())
            comics = driver.find_elements(By.CLASS_NAME, "comic-book")

            for comic in comics:
                original_title = comic.find_element(By.CLASS_NAME, "comic-book__title").text.strip()

                # Format the title as in your example: "Stepmoms sisters" style
                # Remove apostrophes and convert to title case for display title
                display_title = original_title.replace("'", "")
                # Make first letter of each word capital, rest lowercase
                display_title = ' '.join(word.capitalize() for word in display_title.split())

                description = comic.find_element(By.CLASS_NAME, "comic-book__desc").text.strip()
                genres = [genre.text.strip() for genre in
                          comic.find_elements(By.CSS_SELECTOR, ".comic-book__labels .label__item")]
                tags = [tag.text.strip() for tag in comic.find_elements(By.CSS_SELECTOR, ".tags-wrapper .comic-tag")]
                main_image = comic.find_element(By.CSS_SELECTOR, ".comic-book-img img").get_attribute("src")

                # Clean directory name by removing apostrophes
                dir_name = display_title
                comic_dir = os.path.join(base_dir, dir_name)
                os.makedirs(comic_dir, exist_ok=True)

                # Create the comic data structure
                comic_data = {
                    "title": display_title,  # "Stepmoms sisters" format
                    "originalTitle": original_title.upper(),  # "STEPMOM'S SISTERS" format
                    "description": description,
                    "thumbnail": "thumbnail.jpg",
                    "thumbnailBackground":"",
                    "previewThumbnail": "preview-thumbnail.jpg",
                    "genres": genres,
                    "tags": tags,
                    "episodes": []
                }

                with open(os.path.join(comic_dir, "info.txt"), "w", encoding="utf-8") as file:
                    file.write(f"Title: {display_title}\n")
                    file.write(f"Original Title: {original_title.upper()}\n")
                    file.write(f"Description: {description}\n")
                    file.write(f"Genres: {', '.join(genres) if genres else 'No genres found'}\n")
                    file.write(f"Tags: {', '.join(tags) if tags else 'No tags found'}\n")

                image_path = os.path.join(comic_dir, "thumbnail.jpg")
                response = session.get(main_image, stream=True, verify=False)
                if response.status_code == 200:
                    with open(image_path, "wb") as img_file:
                        for chunk in response.iter_content(1024):
                            img_file.write(chunk)

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

                links_file_path = os.path.join(comic_dir, "links_episode.txt")
                episode_thumbnails = {}  # Словник для зберігання посилань на зображення
                
                with open(links_file_path, "w", encoding="utf-8") as links_file:
                    comic_list = driver.find_element(By.CSS_SELECTOR,
                                                     "body > main > section.section.comic-list .comic-list-items")
                    episodes = comic_list.find_elements(By.CLASS_NAME, "comic-list__item")

                    for index, episode in enumerate(episodes, start=1):
                        link = episode.get_attribute("href")
                        try:
                            image = episode.find_element(By.CSS_SELECTOR, ".comic-list__img img").get_attribute("src")
                            episode_thumbnails[link] = image
                        except:
                            print(f"Could not find thumbnail for episode {index}")
                        links_file.write(f"{link}\n")

                with open(links_file_path, "r", encoding="utf-8") as links_file:
                    episode_links = links_file.readlines()
                    episode_counter = 1  # Лічильник для правильної нумерації папок

                    for episode_index, episode_link in enumerate(episode_links, start=1):
                        episode_link = episode_link.strip()
                        driver.get(episode_link)
                        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                        time.sleep(5)

                        header_title = driver.find_element(By.CLASS_NAME, "header-episode__title-number").text.strip()
                        print(f"Header title: {header_title}")

                        # Пропускаємо прологи
                        if "prologue" in header_title.lower():
                            print(f"Skipping prologue: {header_title}")
                            continue

                        # Створюємо папку для епізоду тільки якщо це не пролог
                        episode_dir = os.path.join(comic_dir, str(episode_counter))
                        os.makedirs(episode_dir, exist_ok=True)

                        # Завантажуємо thumbnail тільки для не-прологів
                        if episode_link in episode_thumbnails:
                            image_path = os.path.join(episode_dir, "thumbnail.jpg")
                            response = session.get(episode_thumbnails[episode_link], stream=True, verify=False)
                            if response.status_code == 200:
                                with open(image_path, "wb") as img_file:
                                    for chunk in response.iter_content(1024):
                                        img_file.write(chunk)

                        single_inner = WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "single-inner"))
                        )

                        images = single_inner.find_elements(By.TAG_NAME, "img")
                        episode_images = []

                        for index, image in enumerate(images):
                            image_url = driver.execute_script("return arguments[0].currentSrc || arguments[0].src;", image)
                            image_filename = f"episode_{episode_counter}_{index + 1}.jpg"
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
                            "title": f"episode {episode_counter}",
                            "slag": f"episode-{episode_counter}",
                            "date": "",
                            "thumbnail": "thumbnail.jpg",
                            "images": episode_images
                        }
                        comic_data["episodes"].append(episode_data)
                        
                        episode_counter += 1  # Збільшуємо лічильник тільки після успішного оброблення епізоду

                # Add the comic data to the comics_data list
                comics_data.append(comic_data)

    # Write all comics data to a single JSON file in the root directory
    with open(os.path.join(base_dir, "all_comics.json"), "w", encoding="utf-8") as json_file:
        json.dump(comics_data, json_file, indent=2, ensure_ascii=False)

finally:
    driver.quit()
