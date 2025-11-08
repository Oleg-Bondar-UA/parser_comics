import os
import re
import time
import json
from pathlib import Path
from typing import List, Dict, Optional

import requests
from requests.exceptions import RequestException
from dotenv import load_dotenv

import colorama
from colorama import Fore, Style
from dicttoxml import dicttoxml
from xml.dom import minidom

from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException


colorama.init(autoreset=True)

try:
    load_dotenv()
except PermissionError as dotenv_error:
    print(f"{Fore.YELLOW}{Style.BRIGHT}Не вдалося прочитати .env файл: {dotenv_error}")

BASE_OUTPUT_DIR = Path("toongod")
PROFILE_DIR = Path("selenium_profile")
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

TITLE_SELECTORS = [
    "h1.post-title",
    "h1.entry-title",
    "h1.series-name",
    "h1.series-title",
    "header h1",
    "h1[itemprop='name']",
    "h1.heading",
]

DESCRIPTION_SELECTORS = [
    "div.series-desc",
    "div.summary__content",
    "div.description p",
    "div.entry-content p",
    "div[itemprop='description']",
]

THUMBNAIL_SELECTORS = [
    "div.series-thumb img",
    "div.summary_image img",
    "div.comic-thumb img",
    "figure img",
]

GENRES_SELECTORS = [
    "div.genres a",
    "div.summary_content span a",
    "div.data span a",
]

CONTENT_CHECK_SELECTORS = [
    "ul.main.version-chap",
    "ul.chapter-list",
    "div#chapterlist",
    "div.listing-chapters",
    "div.summary_image",
    "div.series-thumb",
    "div.entry-content",
    "article",
]

EPISODE_LINK_SELECTORS = [
    "ul.main.version-chap li a",
    "ul.chapter-list li a",
    "div#chapterlist li a",
    "div.listing-chapters li a",
    "div.chapter-item a",
]

EPISODE_CONTAINER_SELECTORS = [
    "ul.main.version-chap li",
    "ul.chapter-list li",
    "div#chapterlist li",
    "div.listing-chapters li",
    "div.chapter-item",
]

IMAGE_SELECTORS = [
    "div.reading-content img",
    "div#chapter-content img",
    "div.entry-content img",
    "div.page-break img",
    "img.wp-manga-chapter-img",
]


def create_driver() -> Driver:
    proxy = os.getenv("TOONGOD_PROXY")
    locale = os.getenv("TOONGOD_LOCALE", "en-US")

    driver = Driver(
        browser="chrome",
        uc=True,
        locale_code=locale,
        proxy=proxy,
        headless=False,
        user_data_dir=str(PROFILE_DIR.resolve()),
        incognito=False,
        block_images=False,
    )
    driver.set_page_load_timeout(120)
    driver.set_script_timeout(120)

    if USER_AGENT:
        try:
            driver.execute_cdp_cmd(
                "Network.setUserAgentOverride",
                {"userAgent": USER_AGENT},
            )
        except Exception as override_error:
            print(f"{Fore.YELLOW}{Style.BRIGHT}Не вдалося встановити user-agent через CDP: {override_error}")

    return driver


def manual_cloudflare_wait(
    driver: Driver,
    wait_seconds: int = 40,
    save_path: Optional[Path] = None,
) -> None:
    print(f"Browser launched. You have {wait_seconds} seconds to resolve Cloudflare...")
    for _ in range(wait_seconds, 0, -1):
        time.sleep(1)

    page_source = driver.page_source or ""
    if save_path:
        ensure_directory(save_path.parent)
        with open(save_path, "w", encoding="utf-8") as snapshot:
            snapshot.write(page_source)
        print(f"Saved page source length {len(page_source)}")


def sanitize_filename(text: str) -> str:
    text = re.sub(r"[\s\-]+", " ", text.strip())
    cleaned = re.sub(r"[^a-zA-Z0-9 _\-]", "", text)
    return cleaned.strip() or "toongod_comic"


def get_first_text(driver: Driver, selectors: List[str]) -> str:
    for selector in selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            text = element.text.strip()
            if text:
                return text
        except NoSuchElementException:
            continue
    return ""


def get_all_text(driver: Driver, selectors: List[str]) -> List[str]:
    collected: List[str] = []
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            elements = []
        for element in elements:
            value = element.text.strip()
            if value and value not in collected:
                collected.append(value)
        if collected:
            break
    return collected


def get_first_attribute(driver: Driver, selectors: List[str], attribute: str) -> Optional[str]:
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            elements = []
        for element in elements:
            value = element.get_attribute(attribute)
            if value:
                return value
    return None


def page_has_any(driver: Driver, selectors: List[str]) -> bool:
    for selector in selectors:
        try:
            if driver.find_elements(By.CSS_SELECTOR, selector):
                return True
        except Exception:
            continue
    return False


def collect_episode_links(driver: Driver) -> List[Dict[str, str]]:
    episodes: List[Dict[str, str]] = []
    seen_urls = set()

    for selector in EPISODE_LINK_SELECTORS:
        try:
            links = driver.find_elements(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            links = []

        for link in links:
            href = link.get_attribute("href")
            if not href or href in seen_urls:
                continue

            raw_title = link.text.strip() or (link.get_attribute("title") or "").strip()
            date_text = ""
            for date_selector in [
                ".chapter-release-date",
                ".episode-date",
                "time",
                "span.chapter-release-date",
            ]:
                try:
                    date_elem = link.find_element(By.CSS_SELECTOR, date_selector)
                    date_text = date_elem.text.strip()
                    break
                except NoSuchElementException:
                    continue

            seen_urls.add(href)
            episodes.append({
                "url": href,
                "label": raw_title,
                "date": date_text,
            })

        if episodes:
            break

    if not episodes:
        for container_selector in EPISODE_CONTAINER_SELECTORS:
            try:
                containers = driver.find_elements(By.CSS_SELECTOR, container_selector)
            except NoSuchElementException:
                containers = []

            for container in containers:
                try:
                    anchor = container.find_element(By.CSS_SELECTOR, "a")
                except NoSuchElementException:
                    continue

                href = anchor.get_attribute("href")
                if not href or href in seen_urls:
                    continue

                raw_title = anchor.text.strip() or (anchor.get_attribute("title") or "").strip()
                date_text = ""
                for date_selector in [
                    ".chapter-release-date",
                    ".episode-date",
                    "time",
                    "span.chapter-release-date",
                ]:
                    try:
                        date_elem = container.find_element(By.CSS_SELECTOR, date_selector)
                        date_text = date_elem.text.strip()
                        break
                    except NoSuchElementException:
                        continue

                seen_urls.add(href)
                episodes.append({
                    "url": href,
                    "label": raw_title,
                    "date": date_text,
                })

            if episodes:
                break

    return list(reversed(episodes))


def extract_image_urls(driver: Driver) -> List[str]:
    image_urls: List[str] = []
    seen = set()

    for selector in IMAGE_SELECTORS:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            elements = []

        for element in elements:
            for attr in ["data-src", "data-original", "data-lazy-src", "src"]:
                url = (element.get_attribute(attr) or "").strip()
                if url and not url.startswith("data:image"):
                    if url not in seen:
                        seen.add(url)
                        image_urls.append(url)
                        break

        if image_urls:
            break

    return image_urls


def build_session_from_driver(driver: Driver) -> requests.Session:
    session = requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain"),
            path=cookie.get("path"),
        )
    try:
        user_agent = driver.execute_script("return navigator.userAgent")
    except Exception:
        user_agent = USER_AGENT
    session.headers.update({
        "User-Agent": user_agent,
        "Referer": "https://www.toongod.org/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    })
    return session


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download_file(
    session: requests.Session,
    url: str,
    destination: Path,
    referer: Optional[str] = None,
    retries: int = 3,
    timeout: int = 60,
) -> Optional[Path]:
    ensure_directory(destination.parent)
    headers = {"Referer": referer} if referer else {}

    for attempt in range(1, retries + 1):
        try:
            with session.get(url, headers=headers, stream=True, timeout=timeout) as response:
                response.raise_for_status()
                with open(destination, "wb") as output:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            output.write(chunk)
            return destination
        except RequestException as error:
            print(
                f"{Fore.YELLOW}{Style.BRIGHT}Не вдалося завантажити {url} (спроба {attempt}/{retries}): {error}"
            )
            time.sleep(attempt)

    print(f"{Fore.RED}{Style.BRIGHT}Повністю провалено завантаження: {url}")
    return None


def scrape_episode(
    driver: Driver,
    session: requests.Session,
    episode_meta: Dict[str, str],
    comic_dir: Path,
    episode_index: int,
) -> Dict[str, object]:
    episode_url = episode_meta["url"]
    driver.get(episode_url)

    if not page_has_any(driver, IMAGE_SELECTORS):
        print(
            f"{Fore.YELLOW}{Style.BRIGHT}Після очікування зображення епізоду поки не знайдені. Продовжую..."
        )

    time.sleep(2)
    session = build_session_from_driver(driver)

    episode_folder = comic_dir / f"{episode_index:03d}"
    ensure_directory(episode_folder)

    image_urls = extract_image_urls(driver)
    if not image_urls:
        print(f"{Fore.RED}{Style.BRIGHT}Не знайдено зображень для епізоду: {episode_url}")

    downloaded_images: List[str] = []
    for image_position, image_url in enumerate(image_urls, start=1):
        extension = os.path.splitext(image_url.split("?")[0])[1].lower() or ".jpg"
        if extension not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            extension = ".jpg"
        filename = f"episode_{episode_index:03d}_{image_position:03d}{extension}"
        destination = episode_folder / filename
        result = download_file(session, image_url, destination, referer=episode_url)
        if result:
            downloaded_images.append(filename)

    thumbnail_name = downloaded_images[0] if downloaded_images else ""

    return {
        "parentTitle": comic_dir.name,
        "title": f"episode {episode_index:03d}",
        "slag": f"episode-{episode_index:03d}",
        "date": episode_meta.get("date", ""),
        "thumbnail": thumbnail_name,
        "images": downloaded_images,
        "source": episode_url,
        "label": episode_meta.get("label", ""),
    }


def scrape_comic(driver: Driver, session: requests.Session, url: str) -> Optional[Dict[str, object]]:
    print(f"{Fore.CYAN}{Style.BRIGHT}Обробка коміксу: {url}")
    driver.get(url)

    manual_cloudflare_wait(driver, wait_seconds=40, save_path=Path("toongod_live.html"))

    if not page_has_any(driver, CONTENT_CHECK_SELECTORS):
        print(
            f"{Fore.YELLOW}{Style.BRIGHT}Після очікування контент коміксу не знайдено. Можливо, Cloudflare ще активний."
        )

    title = get_first_text(driver, TITLE_SELECTORS) or driver.title.strip()
    clean_title = sanitize_filename(title)
    comic_dir = BASE_OUTPUT_DIR / clean_title
    ensure_directory(comic_dir)

    description_lines: List[str] = []
    for selector in DESCRIPTION_SELECTORS:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            elements = []
        for element in elements:
            value = element.text.strip()
            if value:
                description_lines.append(value)
        if description_lines:
            break
    description = "\n".join(description_lines)

    genres = get_all_text(driver, GENRES_SELECTORS)

    thumbnail_url = get_first_attribute(driver, THUMBNAIL_SELECTORS, "src")
    thumbnail_local = ""
    if thumbnail_url:
        session = build_session_from_driver(driver)
        extension = os.path.splitext(thumbnail_url.split("?")[0])[1] or ".jpg"
        destination = comic_dir / f"thumbnail{extension}"
        if download_file(session, thumbnail_url, destination, referer=url):
            thumbnail_local = destination.name

    episodes_meta = collect_episode_links(driver)
    if not episodes_meta:
        print(f"{Fore.RED}{Style.BRIGHT}Не знайдено жодного епізоду для {url}")
        return None

    episodes: List[Dict[str, object]] = []
    for index, episode_meta in enumerate(episodes_meta, start=1):
        print(
            f"  {Fore.GREEN}{Style.BRIGHT}Епізод {index:03d}: {episode_meta.get('label', '').strip() or episode_meta['url']}"
        )
        episode_data = scrape_episode(driver, session, episode_meta, comic_dir, index)
        episodes.append(episode_data)

    comic_data = {
        "title": clean_title,
        "originalTitle": title,
        "description": description,
        "thumbnail": thumbnail_local,
        "thumbnailBackground": "",
        "genres": genres,
        "tags": [],
        "episodes": episodes,
        "source": url,
    }

    return comic_data


def save_results(comics: List[Dict[str, object]], failed: List[str]) -> None:
    if comics:
        with open("toongod.json", "w", encoding="utf-8") as json_file:
            json.dump(comics, json_file, indent=2, ensure_ascii=False)

        xml = dicttoxml({"item": comics}, root=False, attr_type=False, item_func=lambda _: "item")
        dom = minidom.parseString(xml)
        with open("toongod.xml", "w", encoding="utf-8") as xml_file:
            xml_file.write(dom.toprettyxml(indent="  "))

    if failed:
        with open("failed_toongod.json", "w", encoding="utf-8") as failed_file:
            json.dump(failed, failed_file, indent=2, ensure_ascii=False)
        print(
            f"{Fore.YELLOW}{Style.BRIGHT}Не вдалося обробити {len(failed)} коміксів. Список у failed_toongod.json"
        )


def parse_toongod(urls: List[str]) -> None:
    ensure_directory(BASE_OUTPUT_DIR)
    driver = create_driver()

    comics: List[Dict[str, object]] = []
    failed: List[str] = []

    try:
        for index, url in enumerate(urls, start=1):
            print(f"{Fore.CYAN}{Style.BRIGHT}Комікс {index}/{len(urls)}")
            try:
                session = build_session_from_driver(driver)
                comic_data = scrape_comic(driver, session, url)
                if comic_data:
                    comics.append(comic_data)
            except Exception as error:
                print(f"{Fore.RED}{Style.BRIGHT}Помилка при обробці {url}: {error}")
                failed.append(url)
    finally:
        driver.quit()

    save_results(comics, failed)


def read_urls_from_file(file_path: Path) -> List[str]:
    if not file_path.exists():
        raise FileNotFoundError(f"Файл {file_path} не існує")
    with open(file_path, "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Завантаження коміксів з toongod.org за допомогою SeleniumBase (undetected Chrome)"
    )
    parser.add_argument("--urls", nargs="+", help="Посилання на сторінки коміксів")
    parser.add_argument("--file", help="Файл із посиланнями (по одному в рядку)")
    parser.add_argument("--example", action="store_true", help="Запустити з демонстраційним посиланням")

    args = parser.parse_args()

    url_list: List[str] = []
    if args.urls:
        url_list.extend(args.urls)
    if args.file:
        url_list.extend(read_urls_from_file(Path(args.file)))
    if args.example:
        example_urls = [
            "https://www.toongod.org/webtoon/boarding-diary-uncensored-manhwa/",
            "https://www.toongod.org/webtoon/stepmother-friends-uncensored-manhwa/",
            "https://www.toongod.org/webtoon/is-there-an-empty-room-uncensored/",
            "https://www.toongod.org/webtoon/fitness-uncensored-manhwa/",
            "https://www.toongod.org/webtoon/change-wife-uncensored-manhwa/",
            "https://www.toongod.org/webtoon/secret-class-uncensored-manhwa/",
            "https://www.toongod.org/webtoon/my-stepmom-uncensored-manhwa/",
        ]
        url_list.extend(example_urls)

    if not url_list:
        parser.print_help()
        raise SystemExit(0)

    parse_toongod(url_list)
