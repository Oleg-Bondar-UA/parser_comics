import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiofiles
import aiohttp
import colorama
from aiohttp.client_exceptions import ClientError
from bs4 import BeautifulSoup
from colorama import Fore, Style
from dicttoxml import dicttoxml
from dotenv import load_dotenv
from xml.dom import minidom


colorama.init(autoreset=True)

try:
    load_dotenv()
except PermissionError as dotenv_error:
    print(f"{Fore.YELLOW}{Style.BRIGHT}Не вдалося прочитати .env файл: {dotenv_error}")


BASE_DOMAIN = "https://mangapark.io"
BASE_OUTPUT_DIR = Path("mangapark")
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}
IMAGE_PATTERN = re.compile(r"https://s\d+\.[a-z0-9.-]+/media/mpup/[^\"'<>\\s]+", re.IGNORECASE)
CHAPTER_PATTERN = re.compile(
    r"/title/[^\"'>\s]+/\d+[^\"'>\s]*-chapter-[^\"'>\s]+",
    re.IGNORECASE,
)


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sanitize_filename(text: str) -> str:
    safe = re.sub(r"[\\/:*?\"<>|]", " ", text)
    safe = re.sub(r"\s+", " ", safe).strip()
    return safe or "mangapark_comic"


def slug_to_label(slug: str) -> str:
    tail = slug.rsplit("/", 1)[-1]  # e.g. "9830813-chapter-1"
    if "-chapter-" in tail:
        _, chapter_part = tail.split("-chapter-", 1)
        chapter_part = chapter_part.replace("-", " ").strip()
        return f"Chapter {chapter_part}".strip().title()
    cleaned = tail.replace("-", " ").strip()
    if cleaned.lower().startswith("chapter"):
        return cleaned.title()
    return f"Chapter {cleaned}".title()


def chapter_sort_key(url: str) -> Tuple[float, str]:
    slug = url.rsplit("/", 1)[-1]
    tail = slug.split("chapter-", 1)[-1] if "chapter-" in slug else slug
    match = re.match(r"(\d+(?:\.\d+)?)", tail)
    if match:
        number = float(match.group(1))
        suffix = tail[match.end():]
        return number, suffix
    return float("inf"), tail


def extract_text(element: Optional[BeautifulSoup]) -> str:
    return element.get_text(" ", strip=True) if element else ""


def extract_chapter_links(html: str) -> List[Dict[str, str]]:
    seen: Dict[str, Dict[str, str]] = {}
    for match in CHAPTER_PATTERN.finditer(html):
        relative = match.group()
        full_url = BASE_DOMAIN + relative
        if full_url not in seen:
            seen[full_url] = {
                "url": full_url,
                "label": slug_to_label(relative),
                "order": chapter_sort_key(full_url),
            }
    chapters = sorted(seen.values(), key=lambda item: item["order"])
    return [{"url": item["url"], "label": item["label"]} for item in chapters]


def extract_image_urls(html: str) -> List[str]:
    seen: set[str] = set()
    ordered_urls: List[str] = []
    for match in IMAGE_PATTERN.finditer(html):
        url = match.group()
        if url not in seen:
            seen.add(url)
            ordered_urls.append(url)
    return ordered_urls


async def fetch_text(
    session: aiohttp.ClientSession,
    url: str,
    referer: Optional[str] = None,
    retries: int = 3,
    timeout: int = 60,
) -> str:
    headers = DEFAULT_HEADERS.copy()
    if referer:
        headers["Referer"] = referer

    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, headers=headers, timeout=timeout) as response:
                response.raise_for_status()
                return await response.text()
        except (ClientError, asyncio.TimeoutError) as error:
            if attempt == retries:
                raise
            delay = attempt * 2
            print(
                f"{Fore.YELLOW}{Style.BRIGHT}Повторю запит {url} (спроба {attempt}/{retries}) через {delay}s — {error}"
            )
            await asyncio.sleep(delay)
    return ""


async def download_file(
    session: aiohttp.ClientSession,
    url: str,
    destination: Path,
    referer: Optional[str] = None,
    retries: int = 3,
) -> Optional[Path]:
    ensure_directory(destination.parent)
    headers = DEFAULT_HEADERS.copy()
    headers["Accept"] = "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
    if referer:
        headers["Referer"] = referer

    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                async with aiofiles.open(destination, "wb") as file_handle:
                    async for chunk in response.content.iter_chunked(1 << 15):
                        await file_handle.write(chunk)
            return destination
        except (ClientError, asyncio.TimeoutError) as error:
            if attempt == retries:
                print(
                    f"{Fore.RED}{Style.BRIGHT}Не вдалося завантажити файл {url}: {error}"
                )
                return None
            await asyncio.sleep(attempt * 2)
    return None


async def download_images(
    session: aiohttp.ClientSession,
    image_urls: List[str],
    episode_folder: Path,
    episode_number: int,
    referer: str,
    concurrency: int = 10,
) -> List[str]:
    ensure_directory(episode_folder)
    semaphore = asyncio.Semaphore(concurrency)
    results: List[Optional[str]] = [None] * len(image_urls)

    async def worker(index: int, image_url: str) -> None:
        async with semaphore:
            parsed = image_url.split("?")[0]
            extension = Path(parsed).suffix.lower()
            if extension not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                extension = ".jpg"
            filename = f"episode_{episode_number:03d}_{index + 1:03d}{extension}"
            destination = episode_folder / filename
            downloaded = await download_file(
                session=session,
                url=image_url,
                destination=destination,
                referer=referer,
            )
            if downloaded is not None:
                results[index] = filename
            else:
                print(
                    f"{Fore.RED}{Style.BRIGHT}Зображення {index + 1} не завантажено: {image_url}"
                )

    tasks = [asyncio.create_task(worker(idx, url)) for idx, url in enumerate(image_urls)]
    await asyncio.gather(*tasks)
    return [name for name in results if name]


async def scrape_chapter(
    session: aiohttp.ClientSession,
    chapter_url: str,
    comic_dir: Path,
    episode_index: int,
    label: str,
) -> Dict[str, object]:
    print(
        f"  {Fore.GREEN}{Style.BRIGHT}Епізод {episode_index:03d}: {label or chapter_url}"
    )
    html = await fetch_text(session, chapter_url, referer=BASE_DOMAIN)
    soup = BeautifulSoup(html, "html.parser")
    image_urls = extract_image_urls(html)

    if not image_urls:
        raise RuntimeError("Не знайдено жодного зображення.")

    episode_folder = comic_dir / f"{episode_index:03d}"
    images = await download_images(
        session=session,
        image_urls=image_urls,
        episode_folder=episode_folder,
        episode_number=episode_index,
        referer=chapter_url,
    )

    episode_title = extract_text(soup.select_one("h6 span")) or label
    thumbnail = images[0] if images else ""

    return {
        "parentTitle": comic_dir.name,
        "title": f"episode {episode_index:03d}",
        "slag": f"episode-{episode_index:03d}",
        "date": "",
        "thumbnail": thumbnail,
        "images": images,
        "source": chapter_url,
        "label": episode_title,
    }


async def download_thumbnail(
    session: aiohttp.ClientSession,
    thumbnail_url: Optional[str],
    comic_dir: Path,
) -> str:
    if not thumbnail_url:
        return ""
    full_url = thumbnail_url
    if full_url.startswith("//"):
        full_url = f"https:{full_url}"
    elif full_url.startswith("/"):
        full_url = BASE_DOMAIN + full_url

    destination = comic_dir / "thumbnail.jpg"
    downloaded = await download_file(
        session=session,
        url=full_url,
        destination=destination,
        referer=BASE_DOMAIN,
    )
    return downloaded.name if downloaded else ""


def extract_genres(soup: BeautifulSoup) -> List[str]:
    genres = []
    for span in soup.select("div.flex.items-center.flex-wrap span.whitespace-nowrap"):
        text = span.get_text(strip=True)
        if text:
            genres.append(text)
    return genres


async def scrape_comic(
    session: aiohttp.ClientSession,
    url: str,
) -> Optional[Dict[str, object]]:
    print(f"{Fore.CYAN}{Style.BRIGHT}Обробка коміксу: {url}")
    start_time = time.time()

    try:
        html = await fetch_text(session, url)
    except Exception as error:
        print(f"{Fore.RED}{Style.BRIGHT}Не вдалося завантажити сторінку: {error}")
        return None

    soup = BeautifulSoup(html, "html.parser")
    title_element = soup.select_one("h3 a")
    title = extract_text(title_element) or "Unknown title"
    clean_title = sanitize_filename(title)
    comic_dir = BASE_OUTPUT_DIR / clean_title
    ensure_directory(comic_dir)

    description = ""
    description_block = soup.select_one(".limit-html")
    if description_block:
        description = extract_text(description_block)

    thumbnail_url = None
    thumbnail_img = soup.select_one("img[src*='/thumb/']")
    if thumbnail_img:
        thumbnail_url = thumbnail_img.get("src")

    thumbnail_local = await download_thumbnail(session, thumbnail_url, comic_dir)
    genres = extract_genres(soup)
    chapters = extract_chapter_links(html)

    if not chapters:
        print(f"{Fore.RED}{Style.BRIGHT}Не знайдено жодної глави на сторінці {url}")
        return None

    episodes: List[Dict[str, object]] = []
    for episode_index, chapter in enumerate(chapters, start=1):
        try:
            episode_data = await scrape_chapter(
                session=session,
                chapter_url=chapter["url"],
                comic_dir=comic_dir,
                episode_index=episode_index,
                label=chapter["label"],
            )
            episodes.append(episode_data)
        except Exception as error:
            print(
                f"{Fore.YELLOW}{Style.BRIGHT}Не вдалося обробити главу {chapter['url']}: {error}"
            )

    elapsed = time.time() - start_time
    print(
        f"{Fore.GREEN}{Style.BRIGHT}Завершено {title} за {elapsed:.1f} секунди. "
        f"Зібрано {len(episodes)} епізодів."
    )

    return {
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


def save_results(results: List[Dict[str, object]], failed: List[str]) -> None:
    if results:
        with open("mangapark.json", "w", encoding="utf-8") as json_file:
            json.dump(results, json_file, indent=2, ensure_ascii=False)

        xml = dicttoxml({"item": results}, root=False, attr_type=False, item_func=lambda _: "item")
        dom = minidom.parseString(xml)
        with open("mangapark.xml", "w", encoding="utf-8") as xml_file:
            xml_file.write(dom.toprettyxml(indent="  "))

    if failed:
        with open("failed_mangapark.json", "w", encoding="utf-8") as failed_file:
            json.dump(failed, failed_file, indent=2, ensure_ascii=False)
        print(
            f"{Fore.YELLOW}{Style.BRIGHT}Не вдалося обробити {len(failed)} коміксів. "
            f"Список у failed_mangapark.json"
        )


async def parse_mangapark(urls: List[str]) -> None:
    ensure_directory(BASE_OUTPUT_DIR)
    timeout = aiohttp.ClientTimeout(total=120)
    connector = aiohttp.TCPConnector(limit_per_host=5)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        comics: List[Dict[str, object]] = []
        failed: List[str] = []

        total = len(urls)
        for index, url in enumerate(urls, start=1):
            print(
                f"{Fore.CYAN}{Style.BRIGHT}Комікс {index}/{total}"
            )
            try:
                comic_data = await scrape_comic(session, url)
                if comic_data:
                    comics.append(comic_data)
                else:
                    failed.append(url)
            except Exception as error:
                print(f"{Fore.RED}{Style.BRIGHT}Помилка при обробці {url}: {error}")
                failed.append(url)

        save_results(comics, failed)


def read_urls_from_file(file_path: Path) -> List[str]:
    if not file_path.exists():
        raise FileNotFoundError(f"Файл {file_path} не існує")
    with open(file_path, "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Завантаження коміксів з mangapark.io"
    )
    parser.add_argument("--urls", nargs="+", help="Посилання на сторінки коміксів")
    parser.add_argument("--file", help="Файл із посиланнями (по одному на рядок)")
    parser.add_argument("--example", action="store_true", help="Запустити з демонстраційними посиланнями")

    args = parser.parse_args()

    url_list: List[str] = []
    if args.urls:
        url_list.extend(args.urls)
    if args.file:
        url_list.extend(read_urls_from_file(Path(args.file)))
    if args.example:
        url_list.extend([
            "https://mangapark.io/title/428367-en-my-landlady-noona-decensored",
        ])

    if not url_list:
        parser.print_help()
        raise SystemExit(0)

    asyncio.run(parse_mangapark(url_list))

