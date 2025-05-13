import os
import time
import json
import asyncio
import aiohttp
import aiofiles
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re

import colorama
from colorama import Fore, Style
from dicttoxml import dicttoxml
from playwright.async_api import async_playwright, Browser, Page

# Initialize colorama
colorama.init(autoreset=True)

load_dotenv()


async def delay(ms: int):
    """Delay execution for the given number of milliseconds."""
    await asyncio.sleep(ms / 1000)


async def download_image(url: str, filepath: str, session: aiohttp.ClientSession, retries: int = 5) -> str:
    """Download an image from the given URL and save it to the specified filepath."""
    for attempt in range(1, retries + 1):
        try:
            async with session.get(
                    url,
                    headers={"referer": "https://toomics.com"},
                    timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    raise Exception(f"HTTP error {response.status}")

                async with aiofiles.open(filepath, 'wb') as f:
                    await f.write(await response.read())

                return filepath
        except Exception as e:
            if attempt == retries:
                raise Exception(f"Failed to download after {retries} attempts: {str(e)}")
            print(f"{Fore.YELLOW}{Style.BRIGHT}Retrying download ({attempt}/{retries})...")
            await asyncio.sleep(attempt)  # Exponential backoff
            return None
    return None


async def login_to_toomics(page: Page) -> None:
    """Login to Toomics website."""
    await page.goto('https://toomics.com/en', wait_until='load')

    # Execute popup login
    await page.evaluate("Base.popup('modal-login-header', 'modal-login', '/en', 'N')")
    await asyncio.sleep(1)

    await page.evaluate("Base.changeSignInForm()")

    # Fill the login form
    await page.wait_for_selector('#user_id')
    await page.fill('#user_id', os.getenv('TOOMICS_LOGIN'))
    await page.fill('#user_pw', os.getenv('TOOMICS_PASSWORD'))

    # Handle popups if they exist
    try:
        popup = await page.wait_for_selector('#coin-discount-promo .close_popup', timeout=5000)
        if popup:
            await popup.click()
            await asyncio.sleep(2)
    except:
        pass

    try:
        popup = await page.wait_for_selector('#first-pay-sale .close_popup', timeout=5000)
        if popup:
            await popup.click()
            await asyncio.sleep(2)
    except:
        pass

    # Submit login form
    await page.click('#login_fieldset button[type="submit"]')
    await asyncio.sleep(10)


def progress_bar(current: int, total: int) -> str:
    """Create a text progress bar."""
    width = 30
    progress = round((current / total) * width)
    bar = '█' * progress + '░' * (width - progress)
    return f"[{bar}] {current}/{total}"


def update_console_output(comic_progress, title, total_ep, current_ep, total_ep_count, current_img=0, total_img=0):
    """Update the console with progress information."""
    # Clear screen and move cursor to home position
    print('\033[2J\033[0f', end='')

    # Write new status
    print(f"""
Comic Number: {progress_bar(comic_progress['current'], comic_progress['total'])}
Title: {title}
Total Episodes: {total_ep}
Episode Number: {progress_bar(current_ep, total_ep_count) if current_ep > 0 else 'Waiting...'}
Episode Images: {progress_bar(current_img, total_img) if current_img > 0 else 'Waiting...'}
""")


async def download_images_with_queue(
        images: List[str],
        episode_folder: str,
        image_episode_title: str,
        update_progress: Callable[[int], None],
        session: aiohttp.ClientSession,
        concurrency: int = 20
) -> List[str]:
    """Download images concurrently with a queue system."""
    results = [None] * len(images)
    failed_attempts = {}
    sem = asyncio.Semaphore(concurrency)

    async def process_image(index: int):
        max_retries = 3
        nonlocal completed

        async with sem:
            image = images[index]
            attempts = 0

            while attempts < max_retries:
                try:
                    image_extension = image.split('.')[-1]
                    if 'com' in image_extension:
                        image_extension = 'jpg'

                    image_filename = f"{episode_folder}/episode_{image_episode_title}_{index + 1}.{image_extension}"

                    await download_image(image, image_filename, session)
                    results[index] = f"episode_{image_episode_title}_{index + 1}.{image_extension}"

                    completed += 1
                    update_progress(completed)
                    return
                except Exception as e:
                    attempts += 1
                    failed_attempts[index] = attempts

                    if attempts < max_retries:
                        print(
                            f"{Fore.YELLOW}{Style.BRIGHT}Retrying image {index + 1} (attempt {attempts}/{max_retries})...")
                        await asyncio.sleep(attempts * 2)  # Exponential backoff
                    else:
                        print(
                            f"{Fore.RED}{Style.BRIGHT}Failed to download image {index + 1} after {max_retries} queue attempts: {str(e)}")
                        completed += 1
                        update_progress(completed)
                        return

    completed = 0
    tasks = [process_image(i) for i in range(len(images))]
    await asyncio.gather(*tasks)

    return [r for r in results if r]


async def parse_toomics(urls: List[str], progress_callback=None):
    """Main function to parse and download honeytoon from Toomics."""
    comics = []
    failed_comics = []
    total_comics = len(urls)
    current_comic = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-notifications",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--disable-dev-shm-usage",
            ]
        )
        print(f"{Fore.GREEN}{Style.BRIGHT}Browser launched successfully")

        try:
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()

            # Set timeouts
            print(f"{Fore.GREEN}{Style.BRIGHT}Setting page timeouts")
            page.set_default_timeout(120000)
            page.set_default_navigation_timeout(120000)

            # Login once before processing honeytoon
            print(f"{Fore.GREEN}{Style.BRIGHT}Attempting to login to Toomics")
            await login_to_toomics(page)
            print(f"{Fore.GREEN}{Style.BRIGHT}Login completed")

            # Load existing honeytoon from JSON file
            existing_comics = []
            if os.path.exists('toomics.json'):
                try:
                    with open('toomics.json', 'r', encoding='utf-8') as f:
                        existing_comics = json.load(f)
                except:
                    print(f"{Fore.RED}{Style.BRIGHT}Existing honeytoon file is not a JSON")
                    existing_comics = []

            async with aiohttp.ClientSession() as session:
                for url in urls:
                    current_comic += 1
                    comic_progress = {'current': current_comic, 'total': total_comics}
                    update_console_output(comic_progress, "Loading...", 0, 0, 0)

                    try:
                        await page.goto(url, wait_until='load')
                        await asyncio.sleep(1)

                        # Get comic details
                        title = await page.eval_on_selector('#glo_contents > section h2', 'el => el.innerText')
                        content = await page.eval_on_selector('#glo_contents > section > div > div > div > div',
                                                              'el => el.innerText')
                        thumbnail = await page.eval_on_selector('#glo_contents > section > div > img', 'el => el.src')
                        thumbnail_background = await page.eval_on_selector('#glo_contents > section > img',
                                                                           'el => el.src')
                        genres = await page.eval_on_selector_all(
                            '#glo_contents > section > div > div > div.mt-auto > dl > div:nth-child(2) > dd',
                            'els => els.map(el => el.textContent)')

                        update_console_output(comic_progress, title, 0, 0, 0)

                        # Оригінальний заголовок без змін
                        original_title = title

                        # Очищений заголовок без зайвих символів
                        clean_title = re.sub(r'[,\'\-\"\.\!\?\:\;]', '', title)

                        comic_folder = f"./toomics/{clean_title}"
                        os.makedirs(comic_folder, exist_ok=True)

                        # Split genres by / and remove spaces
                        genres = [genre.strip() for genre in genres[0].split('/')]

                        thumbnail_extension = thumbnail.split('.')[-1]
                        thumbnail_filename = f"thumbnail.{thumbnail_extension}"
                        await download_image(thumbnail, f"{comic_folder}/{thumbnail_filename}", session)

                        thumbnail_background_extension = thumbnail_background.split('.')[-1]
                        thumbnail_background_filename = f"thumbnail_background.{thumbnail_background_extension}"
                        await download_image(thumbnail_background, f"{comic_folder}/{thumbnail_background_filename}",
                                             session)

                        await asyncio.sleep(1)

                        # Map episodes
                        episodes = await page.eval_on_selector_all('.list-ep li a', '''
                            (els, parentTitle) => {
                                return els.map(el => {
                                    const episodeNumber = el.querySelector('div.cell-num > span')?.textContent.trim() || '';
                                    const epTitle = `episode ${episodeNumber}`.trim();
                                    const epSlug = `episode-${episodeNumber}`.trim();
                                    let dateElem = el.querySelector('div.cell-time > time');

                                    // After login, we can consider all episodes as accessible
                                    // We'll try to access each one regardless of this flag
                                    let isLocked = false;

                                    let url;
                                    if (el.getAttribute('onclick').includes("location.href='")) {
                                        url = el.getAttribute('onclick').split("location.href='")[1].split("'")[0];
                                    }
                                    else if (el.getAttribute('onclick').includes("popupForStat('modal-login', 'login', '")) {
                                        url = el.getAttribute('onclick').split("popupForStat('modal-login', 'login', '")[1].split("'")[0];
                                    }

                                    url = `https://toomics.com${url}`;

                                    let thumbnail = el.querySelector('div.cell-thumb .thumb img').src;
                                    if (thumbnail.includes('base64')) {
                                        thumbnail = el.querySelector('div.cell-thumb .thumb img').getAttribute('data-original');
                                    }

                                    return {
                                        isLocked,
                                        parentTitle,
                                        title: epTitle,
                                        date: dateElem ? dateElem.innerText : '',
                                        thumbnail,
                                        slag: epSlug,
                                        url
                                    };
                                }).filter(item => item !== null);
                            }
                        ''', clean_title)

                        # Get preview thumbnail
                        preview_thumbnail_filename = None
                        try:
                            await page.goto('https://toomics.com/en/webtoon/search?', wait_until='load')
                            await asyncio.sleep(1)
                            await page.fill('#search-term', title)
                            await page.evaluate("Search.ajax_search()")
                            await asyncio.sleep(1)

                            await page.wait_for_selector('#search-list-items li a img', timeout=10000)
                            preview_thumbnail = await page.eval_on_selector('#search-list-items li a img',
                                                                            'el => el.src')
                            print(f"{Fore.GREEN}{Style.BRIGHT}Preview Thumbnail: {preview_thumbnail}")

                            preview_thumbnail_extension = preview_thumbnail.split('.')[-1]
                            preview_thumbnail_filename = f"preview_thumbnail.{preview_thumbnail_extension}"
                            await download_image(preview_thumbnail, f"{comic_folder}/{preview_thumbnail_filename}",
                                                 session)
                        except Exception as e:
                            print(f"{Fore.YELLOW}{Style.BRIGHT}Couldn't find preview thumbnail: {str(e)}")
                            preview_thumbnail = None
                            preview_thumbnail_filename = None

                        total_episodes = len(episodes)
                        current_episode = 0
                        update_console_output(comic_progress, title, total_episodes, current_episode, total_episodes)

                        # For each episode, navigate to its page and extract all images
                        for episode in episodes:
                            current_episode += 1
                            update_console_output(comic_progress, title, total_episodes, current_episode,
                                                  total_episodes)

                            # Extract just the number from episode title for directory name
                            episode_number = episode['title'].replace('episode ', '')
                            episode_folder = f"./toomics/{clean_title}/{episode_number}"
                            os.makedirs(episode_folder, exist_ok=True)

                            episode_thumbnail = episode['thumbnail']
                            episode_thumbnail_extension = episode_thumbnail.split('.')[-1]
                            episode_thumbnail_filename = f"thumbnail.{episode_thumbnail_extension}"
                            await download_image(episode_thumbnail, f"{episode_folder}/{episode_thumbnail_filename}",
                                                 session)

                            # Change thumbnail to local file reference
                            episode['thumbnail'] = episode_thumbnail_filename

                            # Attempt to access episodes regardless of isLocked flag
                            # After login, we should be able to access all of them
                            if not episode.get('url'):
                                # Skip only if no URL is available
                                episode['images'] = []
                                continue

                            try:
                                await page.goto(episode['url'], wait_until='load')

                                # Check if URL contains popup_type/register
                                if 'popup_type/register' in page.url:
                                    print(
                                        f"{Fore.RED}{Style.BRIGHT}Need to register to view episode {episode['title']}")
                                    episode['images'] = []
                                    # Set episode as locked since we couldn't access it
                                    episode['isLocked'] = True
                                    continue

                                # Check if age verification is needed
                                if 'age_verification' in page.url:
                                    await page.wait_for_selector('.section_age_verif .button_yes')
                                    await page.click('.section_age_verif .button_yes')
                                    await asyncio.sleep(5)
                                    await page.goto(episode['url'], wait_until='load')

                                images = await page.eval_on_selector_all('#viewer-img div img',
                                                                         'els => els.map(el => el.src.includes("base64") ? el.getAttribute("data-original") : el.src)')

                                episode['images'] = images
                                del episode['url']  # Remove URL after use

                                # Extract just the number from episode title for filename
                                episode_number = episode['title'].replace('episode ', '')
                                image_episode_title = re.sub(r'[^a-zA-Z0-9_]', '', episode_number)
                                total_images = len(images)
                                current_image = 0

                                def update_image_progress(completed):
                                    nonlocal current_image
                                    current_image = completed
                                    update_console_output(comic_progress, title, total_episodes, current_episode,
                                                          total_episodes,
                                                          current_image, total_images)

                                episode['images'] = await download_images_with_queue(
                                    images,
                                    episode_folder,
                                    image_episode_title,
                                    update_image_progress,
                                    session
                                )
                            except Exception as ep_error:
                                print(
                                    f"{Fore.RED}{Style.BRIGHT}Error processing episode {episode['title']}: {str(ep_error)}")
                                episode['images'] = []
                                continue

                        comic_data = {
                            'title': clean_title,
                            'originalTitle': original_title,
                            'description': content,
                            'thumbnail': thumbnail_filename,
                            'thumbnailBackground': thumbnail_background_filename,
                            'previewThumbnail': preview_thumbnail_filename,
                            'genres': genres,
                            'tags': [],
                            'episodes': episodes
                        }

                        comics.append(comic_data)
                        existing_comics.append(comic_data)

                        # Save to JSON file after each comic
                        with open('toomics.json', 'w', encoding='utf-8') as f:
                            json.dump(existing_comics, f, indent=2)

                        print(f"{Fore.GREEN}{Style.BRIGHT}Successfully parsed comic: {title}")

                        # Call progress callback
                        if progress_callback:
                            progress_callback(current_comic, total_comics)

                    except Exception as error:
                        # Clear screen before showing error
                        print('\033[2J\033[0f', end='')
                        print(f"{Fore.RED}{Style.BRIGHT}Failed to parse comic at URL: {url}")
                        print(f"{Fore.RED}{Style.BRIGHT}Error: {str(error)}")
                        failed_comics.append(url)
                        continue

            # Clear screen before finishing
            print('\033[2J\033[0f', end='')

        except Exception as e:
            # Clear screen before showing error
            print('\033[2J\033[0f', end='')
            print(f"{Fore.RED}{Style.BRIGHT}Fatal error: {str(e)}")
        finally:
            await browser.close()

    # Save failed honeytoon to a separate file
    if failed_comics:
        with open('failed_comics.json', 'w', encoding='utf-8') as f:
            json.dump(failed_comics, f, indent=2)
        print(
            f"{Fore.YELLOW}{Style.BRIGHT}{len(failed_comics)} honeytoon failed to parse. URLs saved to failed_comics.json")

    # Save the result to an XML file
    xml = dicttoxml(
        {'item': comics},
        root=False,
        attr_type=False,
        item_func=lambda x: 'item'
    )

    # Make XML pretty
    dom = minidom.parseString(xml)
    pretty_xml = dom.toprettyxml(indent="  ")

    with open('toomics.xml', 'w', encoding='utf-8') as f:
        f.write(pretty_xml)

    return failed_comics


async def main():
    # Example usage
    urls = [
        "https://toomics.com/en/webtoon/episode/toon/8250",
        # Add more URLs here
    ]

    try:
        await parse_toomics(urls)
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Error in main(): {str(e)}")


if __name__ == "__main__":
    # Setup command line interface to input URLs
    import argparse

    parser = argparse.ArgumentParser(description='Download honeytoon from Toomics.com')
    parser.add_argument('--urls', nargs='+', help='URLs to parse')
    parser.add_argument('--file', help='File containing URLs (one per line)')
    parser.add_argument('--example', action='store_true', help='Run with an example URL')

    args = parser.parse_args()

    urls = []
    if args.urls:
        urls.extend(args.urls)

    if args.file:
        try:
            with open(args.file, 'r') as f:
                file_urls = [line.strip() for line in f if line.strip()]
                urls.extend(file_urls)
        except Exception as e:
            print(f"{Fore.RED}{Style.BRIGHT}Error reading file: {str(e)}")

    if args.example:
        print(f"{Fore.GREEN}{Style.BRIGHT}Running with example URL...")
        urls = ["https://toomics.com/en/webtoon/episode/toon/8250",
                "https://toomics.com/en/webtoon/episode/toon/8039",
                "https://toomics.com/en/webtoon/episode/toon/8248",
                "https://toomics.com/en/webtoon/episode/toon/8140",
                "https://toomics.com/en/webtoon/episode/toon/6868"]

    if not urls:
        print(f"{Fore.YELLOW}{Style.BRIGHT}No URLs provided. Please use --urls, --file, or --example")
        parser.print_help()
        exit(1)

    try:
        asyncio.run(parse_toomics(urls))
    except KeyboardInterrupt:
        print(f"{Fore.YELLOW}{Style.BRIGHT}\nScript interrupted by user. Exiting...")
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Unhandled error: {str(e)}")
