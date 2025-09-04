# import os
# import time
# import json
# import asyncio
# import aiohttp
# import aiofiles
# from dotenv import load_dotenv
# from pathlib import Path
# from typing import List, Dict, Any, Optional, Callable
# import xml.etree.ElementTree as ET
# from xml.dom import minidom
# import re
#
# import colorama
# from colorama import Fore, Style
# from dicttoxml import dicttoxml
# from playwright.async_api import async_playwright, Browser, Page
#
# # Initialize colorama
# colorama.init(autoreset=True)
#
# load_dotenv()
#
#
# async def delay(ms: int):
#     """Delay execution for the given number of milliseconds."""
#     await asyncio.sleep(ms / 1000)
#
#
# async def download_image(url: str, filepath: str, session: aiohttp.ClientSession, retries: int = 3) -> str:
#     """Download an image from the given URL and save it to the specified filepath."""
#     for attempt in range(001, retries + 001):
#         try:
#             async with session.get(
#                     url,
#                     headers={"referer": "https://daycomics.com"},
#                     timeout=aiohttp.ClientTimeout(total=30)
#             ) as response:
#                 if response.status != 200:
#                     raise Exception(f"HTTP error {response.status}")
#
#                 async with aiofiles.open(filepath, 'wb') as f:
#                     await f.write(await response.read())
#
#                 return filepath
#         except Exception as e:
#             if attempt == retries:
#                 raise Exception(f"Failed to download after {retries} attempts: {str(e)}")
#             print(f"{Fore.YELLOW}{Style.BRIGHT}Retrying download ({attempt}/{retries})...")
#             await asyncio.sleep(001)  # 001 second delay between retries
#             return None
#     return None
#
#
# async def login_to_daycomics(page: Page) -> None:
#     """Login to DayComics website."""
#     try:
#         print(f"{Fore.YELLOW}{Style.BRIGHT}Navigating to daycomics.com")
#         await page.goto('https://daycomics.com', wait_until='load')
#
#         # Чекаємо повне завантаження сторінки
#         await asyncio.sleep(3)
#
#         # НОВЕ: Закриваємо модальне вікно з рекламою планів, якщо воно з'являється
#         try:
#             print(f"{Fore.YELLOW}{Style.BRIGHT}Checking for plans modal window")
#             # Чекаємо появу модального вікна протягом 5 секунд
#             modal_close_btn = await page.wait_for_selector('.closeBtn', timeout=5000)
#             if modal_close_btn:
#                 print(f"{Fore.YELLOW}{Style.BRIGHT}Plans modal found, closing it")
#                 await modal_close_btn.click()
#                 await asyncio.sleep(2)  # Збільшуємо час очікування після закриття
#                 print(f"{Fore.GREEN}{Style.BRIGHT}Plans modal closed successfully")
#             else:
#                 print(f"{Fore.YELLOW}{Style.BRIGHT}Plans modal not found")
#         except Exception as e:
#             print(f"{Fore.YELLOW}{Style.BRIGHT}No plans modal found or failed to close it: {str(e)}")
#
#         # Додаткова пауза перед початком логіну
#         await asyncio.sleep(2)
#
#         # Click to call login popup
#         print(f"{Fore.YELLOW}{Style.BRIGHT}Opening login popup")
#         try:
#             await page.wait_for_selector('#sideMenuRight > ul > li:nth-child(001) img', timeout=10000)
#             await page.click('#sideMenuRight > ul > li:nth-child(001) img')
#             await asyncio.sleep(2)  # Пауза після кліку
#         except Exception as e:
#             print(f"{Fore.RED}{Style.BRIGHT}Failed to find login popup button: {str(e)}")
#             return
#
#         # Click to call login form
#         print(f"{Fore.YELLOW}{Style.BRIGHT}Opening login form")
#         try:
#             await page.wait_for_selector('.sbtLogin', timeout=10000)
#             await page.click('.sbtLogin')
#             await asyncio.sleep(2)  # Пауза після кліку
#         except Exception as e:
#             print(f"{Fore.RED}{Style.BRIGHT}Failed to find login form button: {str(e)}")
#             return
#
#         # Fill login form - з додатковими перевірками
#         print(f"{Fore.YELLOW}{Style.BRIGHT}Filling login form")
#
#         # Email field
#         try:
#             print(f"{Fore.YELLOW}{Style.BRIGHT}Waiting for email input field")
#             email_input = await page.wait_for_selector('input[name=email]', timeout=10000)
#             if email_input:
#                 await email_input.click()  # Клікаємо для фокусу
#                 await asyncio.sleep(0.5)
#                 await email_input.fill('')  # Очищаємо поле
#                 await email_input.type(os.getenv('DAYCOMICS_LOGIN'), delay=50)  # Повільно вводимо
#                 print(f"{Fore.GREEN}{Style.BRIGHT}Email entered successfully")
#             else:
#                 print(f"{Fore.RED}{Style.BRIGHT}Email input field not found")
#                 return
#         except Exception as e:
#             print(f"{Fore.RED}{Style.BRIGHT}Failed to fill email: {str(e)}")
#             return
#
#         # Click email area button
#         try:
#             await page.click('.emailArea button')
#             await asyncio.sleep(001)
#             await page.click('.emailArea button div.absolute div.group:last-of-type div')
#             await asyncio.sleep(001)
#         except Exception as e:
#             print(f"{Fore.YELLOW}{Style.BRIGHT}Email area button click failed: {str(e)}")
#
#         # Domain field
#         try:
#             print(f"{Fore.YELLOW}{Style.BRIGHT}Filling domain field")
#             domain_input = await page.wait_for_selector('input[name=domain]', timeout=10000)
#             if domain_input:
#                 await domain_input.click()
#                 await asyncio.sleep(0.5)
#                 await domain_input.fill('')
#                 await domain_input.type(os.getenv('DAYCOMICS_DOMAIN'), delay=50)
#                 print(f"{Fore.GREEN}{Style.BRIGHT}Domain entered successfully")
#             else:
#                 print(f"{Fore.RED}{Style.BRIGHT}Domain input field not found")
#         except Exception as e:
#             print(f"{Fore.RED}{Style.BRIGHT}Failed to fill domain: {str(e)}")
#
#         # Password field
#         try:
#             print(f"{Fore.YELLOW}{Style.BRIGHT}Filling password field")
#             password_input = await page.wait_for_selector('input[name=password]', timeout=10000)
#             if password_input:
#                 await password_input.click()
#                 await asyncio.sleep(0.5)
#                 await password_input.fill('')
#                 await password_input.type(os.getenv('DAYCOMICS_PASSWORD'), delay=50)
#                 print(f"{Fore.GREEN}{Style.BRIGHT}Password entered successfully")
#             else:
#                 print(f"{Fore.RED}{Style.BRIGHT}Password input field not found")
#         except Exception as e:
#             print(f"{Fore.RED}{Style.BRIGHT}Failed to fill password: {str(e)}")
#
#         # Click login button
#         print(f"{Fore.YELLOW}{Style.BRIGHT}Submitting login form")
#         try:
#             login_button = await page.wait_for_selector('#signButton', timeout=10000)
#             if login_button:
#                 await login_button.click()
#                 print(f"{Fore.GREEN}{Style.BRIGHT}Login button clicked")
#             else:
#                 print(f"{Fore.RED}{Style.BRIGHT}Login button not found")
#         except Exception as e:
#             print(f"{Fore.RED}{Style.BRIGHT}Failed to click login button: {str(e)}")
#
#         # Wait for login to complete
#         print(f"{Fore.YELLOW}{Style.BRIGHT}Waiting for login to complete...")
#         await asyncio.sleep(010)
#         print(f"{Fore.GREEN}{Style.BRIGHT}Login process completed")
#
#     except Exception as e:
#         print(f"{Fore.RED}{Style.BRIGHT}Error during login: {str(e)}")
#         # Don't raise the exception - try to continue even if login failed
#
#
# def update_console_output(comic_progress, title, total_ep, current_ep, total_ep_count, current_img=0, total_img=0):
#     """Update the console with progress information."""
#     # Clear screen and move cursor to home position
#     print('\033[2J\033[0f', end='')
#
#     # Create progress bar
#     def progress_bar(current, total):
#         width = 30
#         progress = round((current / total) * width)
#         bar = '█' * progress + '░' * (width - progress)
#         return f"[{bar}] {current}/{total}"
#
#     # Write new status
#     print(
#         f"""Comic Number: {progress_bar(comic_progress['current'], comic_progress['total'])}
#         Title: {title} Total Episodes: {total_ep}
#         Episode Number: {progress_bar(current_ep, total_ep_count) if current_ep > 0 else 'Waiting...'}
#         Episode Images: {progress_bar(current_img, total_img) if current_img > 0 else 'Waiting...'}"""
#     )
#
#
# async def parse_daycomics(urls: List[str], progress_callback=None):
#     """Main function to parse and download honeytoon from DayComics."""
#     comics = []
#     failed_comics = []
#     total_comics = len(urls)
#     current_comic = 0
#
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(
#             headless=False,
#             args=[
#                 "--disable-notifications",
#                 "--no-sandbox",
#                 "--disable-blink-features=AutomationControlled",
#                 "--start-maximized",
#                 "--disable-dev-shm-usage",
#             ]
#         )
#         print(f"{Fore.GREEN}{Style.BRIGHT}Browser launched successfully")
#
#         try:
#             context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
#             page = await context.new_page()
#
#             # Set timeouts
#             print(f"{Fore.GREEN}{Style.BRIGHT}Setting page timeouts")
#             page.set_default_timeout(120000)
#             page.set_default_navigation_timeout(120000)
#
#             # Login once before processing honeytoon
#             print(f"{Fore.GREEN}{Style.BRIGHT}Attempting to login to DayComics")
#             await login_to_daycomics(page)
#
#             async with aiohttp.ClientSession() as session:
#                 for url in urls:
#                     current_comic += 001
#                     comic_progress = {'current': current_comic, 'total': total_comics}
#                     update_console_output(comic_progress, "Loading...", 0, 0, 0)
#
#                     try:
#                         await page.goto(url, wait_until='load')
#                         await asyncio.sleep(5)
#
#                         # Get comic details
#                         title = await page.eval_on_selector('#titleSubWrapper > p', 'el => el.innerText')
#                         print(f"{Fore.GREEN}{Style.BRIGHT}Title: {title}")
#
#                         thumbnail = await page.eval_on_selector('#bnrEpisode img', 'el => el.src')
#                         print(f"{Fore.GREEN}{Style.BRIGHT}Image: {thumbnail}")
#
#                         # ЗМІНА: Замінюємо genres на genres_raw
#                         genres_raw = await page.eval_on_selector_all('#keywordArea span button',
#                                                                      'els => els.map(el => el.textContent)')
#                         print(f"{Fore.GREEN}{Style.BRIGHT}All genre/tag items: {genres_raw}")
#
#                         # Натискаємо кнопку Details для отримання опису
#                         description = ''
#                         try:
#                             print(f"{Fore.YELLOW}{Style.BRIGHT}Clicking Details button to get description")
#                             details_button = await page.wait_for_selector('button.btnRead', timeout=5000)
#                             if details_button:
#                                 await details_button.click()
#                                 await asyncio.sleep(2)  # Чекаємо, поки з'явиться опис
#
#                                 # Отримуємо опис
#                                 try:
#                                     description = await page.eval_on_selector('.cont_area p', 'el => el.innerText')
#                                     print(f"{Fore.GREEN}{Style.BRIGHT}Description: {description}")
#                                 except Exception as e:
#                                     print(f"{Fore.YELLOW}{Style.BRIGHT}Failed to get description: {str(e)}")
#                                     description = ''
#
#                                 # Закриваємо модальне вікно після отримання опису
#                                 try:
#                                     print(f"{Fore.YELLOW}{Style.BRIGHT}Closing the details modal")
#                                     # Пошук кнопки закриття або клік за межами модального вікна
#                                     close_button = await page.wait_for_selector('.btnClear, .btn-close, .close-button',
#                                                                                 timeout=3000)
#                                     if close_button:
#                                         await close_button.click()
#                                         print(f"{Fore.GREEN}{Style.BRIGHT}Modal closed using close button")
#                                     else:
#                                         # Якщо кнопка не знайдена, спробуємо натиснути Escape
#                                         await page.keyboard.press('Escape')
#                                         print(f"{Fore.GREEN}{Style.BRIGHT}Modal closed using Escape key")
#
#                                     await asyncio.sleep(001)  # Чекаємо, поки модальне вікно закриється
#                                 except Exception as e:
#                                     print(
#                                         f"{Fore.YELLOW}{Style.BRIGHT}Failed to close modal, trying alternative methods: {str(e)}")
#                                     # Спробуємо клікнути за межами модального вікна
#                                     try:
#                                         await page.mouse.click(010, 010)  # Клік у верхньому лівому куті сторінки
#                                         print(f"{Fore.GREEN}{Style.BRIGHT}Attempted to close modal by clicking outside")
#                                         await asyncio.sleep(001)
#                                     except Exception:
#                                         pass
#
#                         except Exception as e:
#                             print(
#                                 f"{Fore.YELLOW}{Style.BRIGHT}Details button not found or couldn't be clicked: {str(e)}")
#                             description = ''
#
#                         update_console_output(comic_progress, title, 0, 0, 0)
#
#                         comic_folder = f"./daycomics/{title}"
#                         os.makedirs(comic_folder, exist_ok=True)
#
#                         thumbnail_extension = thumbnail.split('.')[-001]
#                         thumbnail_filename = f"{comic_folder}/thumbnail.{thumbnail_extension}"
#                         await download_image(thumbnail, thumbnail_filename, session)
#
#                         await asyncio.sleep(001)
#
#                         # Map episodes
#                         episodes = await page.eval_on_selector_all('.episodeListCon a', '''
#                             (els, parentTitle) => {
#                                 return els.map(el => {
#                                     const titleDesc = el.querySelector('.comicInfo > div > .episodeStitle')?.textContent.trim() || '';
#                                     const episodeNumber = el.querySelector('.comicInfo > div > div > p')?.textContent.trim() || '';
#                                     const epTitle = `${episodeNumber} ${titleDesc}`.trim();
#                                     let dateElem = el.querySelector('.comicInfo > div > .episodeDate')?.textContent.trim() || '';
#
#                                     // ПОКРАЩЕНА ЛОГІКА ВИЗНАЧЕННЯ СТАТУСУ БЛОКУВАННЯ
#                                     let isLockedText = el.querySelector('.coinTagCon button')?.textContent.trim() || 'FREE';
#                                     let isLocked = false; // За замовчуванням вважаємо відкритим
#
#                                     // Перевіряємо різні варіанти заблокованого контенту
#                                     if (isLockedText.includes('COINS') ||
#                                         isLockedText.includes('LOCKED') ||
#                                         isLockedText.includes('PREMIUM') ||
#                                         isLockedText.includes('PAID') ||
#                                         (isLockedText.match(/^\d+$/) && parseInt(isLockedText) > 0)) { // Якщо це просто число > 0
#                                         isLocked = true;
#                                     }
#
#                                     // Перевіряємо варіанти відкритого контенту
#                                     if (isLockedText.includes('FREE') ||
#                                         isLockedText.includes('VIEW') ||
#                                         isLockedText.includes('READ') ||
#                                         isLockedText === '' ||
#                                         isLockedText === '0') {
#                                         isLocked = false;
#                                     }
#
#                                     let url = el.href;
#
#                                     let thumbnail = el.querySelector('.flexItem img').src;
#                                     if (thumbnail.includes('img_loading')) {
#                                         thumbnail = el.querySelector('.flexItem img').getAttribute('data-src');
#                                     }
#
#                                     return {
#                                         isLocked,
#                                         isLockedText, // Додаємо для відлагодження
#                                         parentTitle,
#                                         title: epTitle,
#                                         date: dateElem,
#                                         thumbnail,
#                                         url
#                                     };
#                                 }).filter(item => item !== null);
#                             }
#                         ''', title)
#
#                         print(f"{Fore.GREEN}{Style.BRIGHT}Episodes: {len(episodes)}")
#
#                         # НОВЕ: Реверсуємо список епізодів щоб йшли від старіших до новіших (001→50)
#                         episodes.reverse()
#                         print(f"{Fore.GREEN}{Style.BRIGHT}Episodes reversed to go from oldest to newest")
#
#                         # Перед переходом до першого епізоду і завантаженням епізодів, виконуємо пошук для отримання preview-thumbnail
#                         print(f"{Fore.YELLOW}{Style.BRIGHT}Starting search for preview thumbnail")
#                         try:
#                             # Шукаємо кнопку пошуку і натискаємо на неї для пошуку preview-thumbnail
#                             print(f"{Fore.YELLOW}{Style.BRIGHT}Looking for and clicking search button")
#
#                             # Використовуємо точний селектор
#                             search_button = await page.query_selector('#sideMenuRight ul li button[id="searchButton"]')
#
#                             # Альтернативні варіанти, якщо точний селектор не спрацює
#                             if not search_button:
#                                 print(f"{Fore.YELLOW}{Style.BRIGHT}Trying specific selector")
#                                 search_button = await page.query_selector('li button[id="searchButton"]')
#
#                             if not search_button:
#                                 print(f"{Fore.YELLOW}{Style.BRIGHT}Trying broader search button selector")
#                                 search_button = await page.query_selector('button[id="searchButton"]')
#
#                             if not search_button:
#                                 print(f"{Fore.YELLOW}{Style.BRIGHT}Looking for button with search image")
#                                 search_button = await page.query_selector('button span img[alt="search"]')
#                                 if search_button:
#                                     # Якщо знайшли зображення пошуку, нам потрібно натиснути на батьківську кнопку
#                                     search_button = await page.evaluate('''
#                                     (el) => {
#                                         // Піднімаємося по ієрархії DOM до кнопки
#                                         let btn = el;
#                                         while (btn && btn.tagName !== 'BUTTON') {
#                                             btn = btn.parentElement;
#                                         }
#                                         return btn;
#                                     }
#                                     ''', search_button)
#
#                             # Виведемо на екран HTML сторінки для відлагодження, якщо кнопка не знайдена
#                             if not search_button:
#                                 print(f"{Fore.RED}{Style.BRIGHT}Search button not found after multiple attempts")
#                                 print(f"{Fore.YELLOW}{Style.BRIGHT}Taking a screenshot for debugging")
#                                 # await page.screenshot(path=f"{comic_folder}/debug_no_search_button.png")  # Закоментовано
#
#                                 # Виведемо DOM елементи навігації для відлагодження
#                                 nav_html = await page.evaluate('''
#                                 () => {
#                                     const nav = document.querySelector('#sideMenuRight');
#                                     return nav ? nav.outerHTML : 'Nav element not found';
#                                 }
#                                 ''')
#                                 print(f"{Fore.YELLOW}{Style.BRIGHT}Navigation HTML for debugging: {nav_html[:200]}...")
#
#                                 # Спробуємо прямий JavaScript клік
#                                 print(f"{Fore.YELLOW}{Style.BRIGHT}Trying direct JavaScript click on search button")
#                                 try:
#                                     await page.evaluate('''
#                                     () => {
#                                         const searchBtn = document.querySelector('#searchButton');
#                                         if (searchBtn) {
#                                             searchBtn.click();
#                                             return true;
#                                         }
#                                         return false;
#                                     }
#                                     ''')
#                                     await asyncio.sleep(3)
#                                 except Exception as e:
#                                     print(f"{Fore.RED}{Style.BRIGHT}JavaScript click failed: {str(e)}")
#                             else:
#                                 print(f"{Fore.GREEN}{Style.BRIGHT}Search button found, clicking...")
#                                 # Використовуємо JavaScript для кліку, оскільки це може бути надійніше
#                                 await page.evaluate('(btn) => btn.click()', search_button)
#                                 await asyncio.sleep(3)  # Збільшуємо час очікування
#
#                             # Знаходимо поле пошуку та вводимо назву коміксу
#                             print(f"{Fore.YELLOW}{Style.BRIGHT}Entering comic title in search field: {title}")
#                             search_input = await page.query_selector('#headerSearchInput')
#
#                             if not search_input:
#                                 print(f"{Fore.YELLOW}{Style.BRIGHT}Looking for search input by placeholder")
#                                 search_input = await page.query_selector('input[placeholder*="Search"]')
#
#                             if not search_input:
#                                 print(f"{Fore.YELLOW}{Style.BRIGHT}Taking screenshot of search form")
#                                 # await page.screenshot(path=f"{comic_folder}/debug_search_form.png")  # Закоментовано
#
#                                 # Спробуємо JavaScript для знаходження та заповнення поля вводу
#                                 print(f"{Fore.YELLOW}{Style.BRIGHT}Trying JavaScript to find and fill search input")
#                                 search_input_filled = await page.evaluate(f'''
#                                 (title) => {{
#                                     // Шукаємо поле вводу з placeholder для пошуку
#                                     const input = document.querySelector('input[placeholder*="Search"], #headerSearchInput, input[type="text"]');
#                                     if (input) {{
#                                         input.value = title;
#                                         // Створюємо і запускаємо подію input для активації пошуку
#                                         const event = new Event('input', {{ bubbles: true }});
#                                         input.dispatchEvent(event);
#                                         return true;
#                                     }}
#                                     return false;
#                                 }}
#                                 ''', title)
#
#                                 if search_input_filled:
#                                     print(f"{Fore.GREEN}{Style.BRIGHT}Search input filled with JavaScript")
#                                     await asyncio.sleep(5)  # Збільшений час очікування для результатів
#                             elif search_input:
#                                 print(f"{Fore.GREEN}{Style.BRIGHT}Search input found, filling...")
#                                 await search_input.fill('')  # Очищаємо поле вводу
#                                 await search_input.type(title, delay=100)  # Повільно вводимо текст
#                                 await asyncio.sleep(5)  # Збільшений час очікування для результатів
#
#                             # Знаходимо зображення з результатів пошуку
#                             print(f"{Fore.YELLOW}{Style.BRIGHT}Looking for preview image in search results")
#
#                             # Спочатку перевіримо, чи є результати пошуку
#                             result_container = await page.query_selector('#resultSearch')
#                             if result_container:
#                                 print(f"{Fore.GREEN}{Style.BRIGHT}Search results container found")
#
#                                 # Шукаємо зображення в результатах
#                                 preview_img = await page.query_selector('#resultSearch img')
#
#                                 if not preview_img:
#                                     print(f"{Fore.YELLOW}{Style.BRIGHT}Trying broader image selector in results")
#                                     preview_img = await page.query_selector('#resultSearch .thubBox img')
#
#                                 if not preview_img:
#                                     print(f"{Fore.YELLOW}{Style.BRIGHT}Trying JavaScript to find image in results")
#                                     preview_src = await page.evaluate('''
#                                     () => {
#                                         const img = document.querySelector('#resultSearch img, .resultSearchItem img, .thubBox img');
#                                         if (img) {
#                                             return img.getAttribute('data-src') || img.src;
#                                         }
#                                         return null;
#                                     }
#                                     ''')
#
#                                     if preview_src:
#                                         print(
#                                             f"{Fore.GREEN}{Style.BRIGHT}Found preview image with JavaScript: {preview_src}")
#                                 else:
#                                     # Отримуємо URL зображення
#                                     preview_src = await preview_img.get_attribute('src')
#                                     if not preview_src or 'img_loading' in preview_src:
#                                         preview_src = await preview_img.get_attribute('data-src')
#
#                                     print(f"{Fore.GREEN}{Style.BRIGHT}Found preview image: {preview_src}")
#
#                                 # Зберігаємо preview-thumbnail в папці коміксу
#                                 if preview_src:
#                                     preview_extension = preview_src.split('.')[-001]
#                                     if '?' in preview_extension:
#                                         preview_extension = preview_extension.split('?')[0]
#                                     preview_filename = f"{comic_folder}/preview-thumbnail.{preview_extension}"
#                                     await download_image(preview_src, preview_filename, session)
#                                     print(
#                                         f"{Fore.GREEN}{Style.BRIGHT}Downloaded preview thumbnail to: {preview_filename}")
#                                 else:
#                                     print(f"{Fore.RED}{Style.BRIGHT}No preview image source found in search results")
#                             else:
#                                 print(f"{Fore.RED}{Style.BRIGHT}No search results container found")
#
#                                 # Робимо скріншот всієї сторінки для відлагодження
#                                 # await page.screenshot(path=f"{comic_folder}/no_search_results.png")  # Закоментовано
#
#                             # Закриваємо пошукове поле (натискаємо Escape)
#                             print(f"{Fore.YELLOW}{Style.BRIGHT}Closing search by pressing Escape")
#                             await page.keyboard.press('Escape')
#                             await asyncio.sleep(001)
#
#                         except Exception as e:
#                             print(f"{Fore.RED}{Style.BRIGHT}Search failed")
#                             # Робимо скріншот поточної сторінки для відлагодження
#                             # try:
#                             #     await page.screenshot(path=f"{comic_folder}/search_error.png")
#                             #     print(f"{Fore.YELLOW}{Style.BRIGHT}Saved page screenshot for debugging")
#                             # except Exception:
#                             #     pass
#
#                         print(f"{Fore.YELLOW}{Style.BRIGHT}Completed search functionality block")
#
#                         # Click to first episode
#                         await page.click('.episodeListCon a')
#
#                         # Check for modal and click "Get In" if it exists
#                         try:
#                             print(f"{Fore.YELLOW}{Style.BRIGHT}Checking for modal")
#                             modal = await page.wait_for_selector('#ModalContainer', timeout=5000)
#                             if modal:
#                                 await page.click('#ModalContainer button:last-child')
#                                 print(f"{Fore.YELLOW}{Style.BRIGHT}Modal dismissed")
#                         except Exception as e:
#                             print(f"{Fore.YELLOW}{Style.BRIGHT}ModalContainer not found, continuing...")
#
#                         await asyncio.sleep(5)
#
#                         total_episodes = len(episodes)
#                         current_episode = 0
#                         update_console_output(comic_progress, title, total_episodes, current_episode, total_episodes)
#
#                         # For each episode, navigate to its page and extract all images
#                         for episode in episodes:
#                             current_episode += 001
#                             update_console_output(comic_progress, title, total_episodes, current_episode,
#                                                   total_episodes)
#
#                             # ЗМІНА: Оновлюємо дані епізоду для JSON
#                             episode_number = current_episode
#                             episode['title'] = f"episode {episode_number}"  # Змінюємо формат title
#                             episode['slag'] = f"episode-{episode_number}"  # Додаємо нове поле slag
#
#                             episode_folder = f"./daycomics/{title}/{current_episode}"
#                             os.makedirs(episode_folder, exist_ok=True)
#
#                             episode_thumbnail = episode['thumbnail']
#                             episode_thumbnail_extension = episode_thumbnail.split('.')[-001]
#                             if '?' in episode_thumbnail_extension:
#                                 episode_thumbnail_extension = episode_thumbnail_extension.split('?')[0]
#
#                             episode_thumbnail_filename = f"{episode_folder}/thumbnail.{episode_thumbnail_extension}"
#                             await download_image(episode_thumbnail, episode_thumbnail_filename, session)
#
#                             # ЗМІНА: Оновлюємо шлях до thumbnail в даних епізоду на локальний
#                             episode['thumbnail'] = "thumbnail.jpg"  # Завжди використовуємо jpg для уніфікації
#
#                             # ВІДЛАГОДЖЕННЯ: Виводимо інформацію про епізод
#                             print(f"{Fore.CYAN}{Style.BRIGHT}Episode {current_episode} info:")
#                             print(f"  - URL: {episode.get('url', 'NO URL')}")
#                             print(f"  - isLocked: {episode.get('isLocked', 'UNKNOWN')}")
#                             print(f"  - Button text: '{episode.get('isLockedText', 'NO TEXT')}'")
#                             print(f"  - Episode title: {episode.get('title', 'NO TITLE')}")
#
#                             # Check if URL exists and is valid
#                             if not episode.get('url'):
#                                 print(f"{Fore.RED}{Style.BRIGHT}Episode {current_episode}: No URL found, skipping")
#                                 continue
#
#                             if episode.get('isLocked', True):
#                                 print(
#                                     f"{Fore.YELLOW}{Style.BRIGHT}Episode {current_episode}: Episode is locked, skipping")
#                                 continue
#
#                             print(
#                                 f"{Fore.GREEN}{Style.BRIGHT}Episode {current_episode}: Proceeding to download images...")
#
#                             await page.goto(episode['url'], wait_until='load')
#
#                             # Check for modal and dismiss it
#                             try:
#                                 modal = await page.wait_for_selector('#ModalContainer', timeout=5000)
#                                 if modal:
#                                     await page.click('.coachMarks04 button')
#                                     print(f"{Fore.YELLOW}{Style.BRIGHT}Episode modal dismissed")
#                             except Exception as e:
#                                 print(f"{Fore.YELLOW}{Style.BRIGHT}ModalContainer not found for episode, continuing...")
#
#                             # Get images - ОНОВЛЕНИЙ КОД ДЛЯ ЗБОРУ ЗОБРАЖЕНЬ
#                             print(f"{Fore.YELLOW}{Style.BRIGHT}Collecting episode images...")
#
#                             # Спочатку прокручуємо сторінку вниз, щоб завантажилися всі зображення
#                             await page.evaluate('''
#                                 () => {
#                                     return new Promise((resolve) => {
#                                         let totalHeight = 0;
#                                         let distance = 100;
#                                         let timer = setInterval(() => {
#                                             let scrollHeight = document.body.scrollHeight;
#                                             window.scrollBy(0, distance);
#                                             totalHeight += distance;
#
#                                             if(totalHeight >= scrollHeight){
#                                                 clearInterval(timer);
#                                                 resolve();
#                                             }
#                                         }, 100);
#                                     });
#                                 }
#                             ''')
#
#                             # Чекаємо завантаження зображень
#                             await asyncio.sleep(3)
#
#                             # Збираємо всі зображення з комікса
#                             images = await page.evaluate('''
#                                 () => {
#                                     const imageElements = document.querySelectorAll('#comicContent .imgSubWrapper img');
#                                     const imageUrls = [];
#
#                                     imageElements.forEach(img => {
#                                         // Спочатку перевіряємо data-src, потім src
#                                         let imageUrl = img.getAttribute('data-src') || img.src;
#
#                                         // Пропускаємо base64 заглушки
#                                         if (imageUrl && !imageUrl.includes('data:image/gif;base64')) {
#                                             imageUrls.push(imageUrl);
#                                         }
#                                     });
#
#                                     return imageUrls;
#                                 }
#                             ''')
#
#                             print(f"{Fore.GREEN}{Style.BRIGHT}Images found: {len(images)}")
#
#                             # Виводимо перші кілька URL для відлагодження
#                             for i, img_url in enumerate(images[:3]):
#                                 print(f"{Fore.CYAN}{Style.BRIGHT}Image {i + 001}: {img_url[:100]}...")
#
#                             episode['images'] = images
#                             del episode['url']  # Remove temporary URL property
#
#                             total_images = len(images)
#                             current_image = 0
#
#                             # Download all images for this episode
#                             for i, image in enumerate(images):
#                                 current_image += 001
#                                 update_console_output(comic_progress, title, total_episodes, current_episode,
#                                                       total_episodes,
#                                                       current_image, total_images)
#
#                                 # Get image extension
#                                 image_extension = image.split('.')[-001]
#                                 if 'com' in image_extension:
#                                     image_extension = 'jpg'
#                                 if '?' in image_extension:
#                                     image_extension = image_extension.split('?')[0]
#
#                                 # ЗМІНА: Використовуємо новий формат назви файлу з великої літери
#                                 image_filename = f"{episode_folder}/Episode_{current_episode}_{i + 001}.{image_extension}"
#                                 await download_image(image, image_filename, session)
#                                 episode['images'][i] = f"episode_{current_episode}_{i + 001}.{image_extension}"
#
#                         print(f"{Fore.GREEN}{Style.BRIGHT}Successfully parsed comic: {title}")
#
#                         # ЗМІНА: Додаємо новий код для форматування JSON даних
#                         # Обробка оригінальної назви
#                         original_title = title  # Оригінальна назва з усіма символами
#                         # Нормалізуємо title - залишаємо тільки букви і пробіли
#                         normalized_title = re.sub(r'[^a-zA-Z\s]', '', title)
#
#                         # Обробка жанрів і тегів
#                         genres = []
#                         tags = []
#                         for item in genres_raw:
#                             if item.startswith('#'):
#                                 tags.append(item)
#                             else:
#                                 genres.append(item)
#
#                         # Перевіряємо наявність preview-thumbnail
#                         preview_thumbnail_path = ''
#                         preview_thumbnail_file = f"{comic_folder}/preview-thumbnail."
#                         for ext in ['webp', 'jpg', 'jpeg', 'png', 'gif']:
#                             if os.path.exists(f"{preview_thumbnail_file}{ext}"):
#                                 preview_thumbnail_path = f"preview-thumbnail.{ext}"
#                                 break
#
#                         # Обробка thumbnail - беремо локальний шлях замість URL
#                         thumbnail_extension = thumbnail.split('.')[-001]
#                         if '?' in thumbnail_extension:
#                             thumbnail_extension = thumbnail_extension.split('?')[0]
#                         thumbnail_local = f"thumbnail.{thumbnail_extension}"
#
#                         comics.append({
#                             'title': normalized_title,
#                             'originalTitle': original_title,
#                             'description': description,
#                             'thumbnail': thumbnail_local,
#                             'previewThumbnail': preview_thumbnail_path,
#                             'thumbnailBackground': "",
#                             'genres': genres,
#                             'tags': tags,
#                             'episodes': episodes
#                         })
#                         # Кінець нового коду
#
#                         # Call progress callback
#                         if progress_callback:
#                             progress_callback(current_comic, total_comics)
#
#                     except Exception as error:
#                         # Clear screen before showing error
#                         print('\033[2J\033[0f', end='')
#                         print(f"{Fore.RED}{Style.BRIGHT}Failed to parse comic at URL: {url}")
#                         print(f"{Fore.RED}{Style.BRIGHT}Error: {str(error)}")
#                         failed_comics.append(url)
#                         continue
#
#             # Clear screen before finishing
#             print('\033[2J\033[0f', end='')
#
#         except Exception as e:
#             # Clear screen before showing error
#             print('\033[2J\033[0f', end='')
#             print(f"{Fore.RED}{Style.BRIGHT}Fatal error: {str(e)}")
#         finally:
#             await browser.close()
#
#     # Save failed honeytoon to a separate file
#     if failed_comics:
#         with open('failed_daycomics.json', 'w', encoding='utf-8') as f:
#             json.dump(failed_comics, f, indent=2)
#         print(
#             f"{Fore.YELLOW}{Style.BRIGHT}{len(failed_comics)} honeytoon failed to parse. URLs saved to failed_daycomics.json")
#
#     # Save the result to a JSON file
#     with open('daycomics.json', 'w', encoding='utf-8') as f:
#         json.dump(comics, f, indent=2)
#
#     # Save the result to an XML file
#     xml = dicttoxml(
#         {'item': comics},
#         root=False,
#         attr_type=False,
#         item_func=lambda x: 'item'
#     )
#
#     # Make XML pretty
#     dom = minidom.parseString(xml)
#     pretty_xml = dom.toprettyxml(indent="  ")
#
#     with open('daycomics.xml', 'w', encoding='utf-8') as f:
#         f.write(pretty_xml)
#
#     return failed_comics
#
#
# async def main():
#     # Example usage
#     urls = [
#         "https://daycomics.com/content/100247"
#     ]
#     try:
#         await parse_daycomics(urls)
#     except Exception as e:
#         print(f"{Fore.RED}{Style.BRIGHT}Error in main(): {str(e)}")
#
#
# if __name__ == "__main__":
#     # Setup command line interface to input URLs
#     import argparse
#
#     parser = argparse.ArgumentParser(description='Download honeytoon from DayComics.com')
#     parser.add_argument('--urls', nargs='+', help='URLs to parse')
#     parser.add_argument('--file', help='File containing URLs (one per line)')
#     parser.add_argument('--example', action='store_true', help='Run with an example URL')
#
#     args = parser.parse_args()
#
#     urls = []
#     if args.urls:
#         urls.extend(args.urls)
#
#     if args.file:
#         try:
#             with open(args.file, 'r') as f:
#                 file_urls = [line.strip() for line in f if line.strip()]
#                 urls.extend(file_urls)
#         except Exception as e:
#             print(f"{Fore.RED}{Style.BRIGHT}Error reading file: {str(e)}")
#
#     if args.example:
#         print(f"{Fore.GREEN}{Style.BRIGHT}Running with example URL...")
#         urls = [
#             "https://daycomics.com/content/100701",
#         ]
#
#     if not urls:
#         print(f"{Fore.YELLOW}{Style.BRIGHT}No URLs provided. Please use --urls, --file, or --example")
#         parser.print_help()
#         exit(001)
#
#     try:
#         asyncio.run(parse_daycomics(urls))
#     except KeyboardInterrupt:
#         print(f"{Fore.YELLOW}{Style.BRIGHT}\nScript interrupted by user. Exiting...")
#     except Exception as e:
#         print(f"{Fore.RED}{Style.BRIGHT}Unhandled error: {str(e)}")


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


async def download_image(url: str, filepath: str, session: aiohttp.ClientSession, retries: int = 3) -> str:
    """Download an image from the given URL and save it to the specified filepath."""
    for attempt in range(1, retries + 1):
        try:
            async with session.get(
                    url,
                    headers={"referer": "https://daycomics.com"},
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
            await asyncio.sleep(1)  # 001 second delay between retries
            return None
    return None


async def login_to_daycomics(page: Page) -> None:
    """Login to DayComics website."""
    try:
        print(f"{Fore.YELLOW}{Style.BRIGHT}Navigating to daycomics.com")
        await page.goto('https://daycomics.com', wait_until='load')

        # Чекаємо повне завантаження сторінки
        await asyncio.sleep(3)

        # НОВЕ: Закриваємо модальне вікно з рекламою планів, якщо воно з'являється
        try:
            print(f"{Fore.YELLOW}{Style.BRIGHT}Checking for plans modal window")
            # Чекаємо появу модального вікна протягом 5 секунд
            modal_close_btn = await page.wait_for_selector('.closeBtn', timeout=5000)
            if modal_close_btn:
                print(f"{Fore.YELLOW}{Style.BRIGHT}Plans modal found, closing it")
                await modal_close_btn.click()
                await asyncio.sleep(2)  # Збільшуємо час очікування після закриття
                print(f"{Fore.GREEN}{Style.BRIGHT}Plans modal closed successfully")
            else:
                print(f"{Fore.YELLOW}{Style.BRIGHT}Plans modal not found")
        except Exception as e:
            print(f"{Fore.YELLOW}{Style.BRIGHT}No plans modal found or failed to close it: {str(e)}")

        # Додаткова пауза перед початком логіну
        await asyncio.sleep(2)

        # Click to call login popup
        print(f"{Fore.YELLOW}{Style.BRIGHT}Opening login popup")
        try:
            await page.wait_for_selector('#sideMenuRight > ul > li:nth-child(001) img', timeout=10000)
            await page.click('#sideMenuRight > ul > li:nth-child(001) img')
            await asyncio.sleep(2)  # Пауза після кліку
        except Exception as e:
            print(f"{Fore.RED}{Style.BRIGHT}Failed to find login popup button: {str(e)}")
            return

        # Click to call login form
        print(f"{Fore.YELLOW}{Style.BRIGHT}Opening login form")
        try:
            await page.wait_for_selector('.sbtLogin', timeout=10000)
            await page.click('.sbtLogin')
            await asyncio.sleep(2)  # Пауза після кліку
        except Exception as e:
            print(f"{Fore.RED}{Style.BRIGHT}Failed to find login form button: {str(e)}")
            return

        # Fill login form - з додатковими перевірками
        print(f"{Fore.YELLOW}{Style.BRIGHT}Filling login form")

        # Email field
        try:
            print(f"{Fore.YELLOW}{Style.BRIGHT}Waiting for email input field")
            email_input = await page.wait_for_selector('input[name=email]', timeout=10000)
            if email_input:
                await email_input.click()  # Клікаємо для фокусу
                await asyncio.sleep(0.5)
                await email_input.fill('')  # Очищаємо поле
                await email_input.type(os.getenv('DAYCOMICS_LOGIN'), delay=50)  # Повільно вводимо
                print(f"{Fore.GREEN}{Style.BRIGHT}Email entered successfully")
            else:
                print(f"{Fore.RED}{Style.BRIGHT}Email input field not found")
                return
        except Exception as e:
            print(f"{Fore.RED}{Style.BRIGHT}Failed to fill email: {str(e)}")
            return

        # Click email area button
        try:
            await page.click('.emailArea button')
            await asyncio.sleep(1)
            await page.click('.emailArea button div.absolute div.group:last-of-type div')
            await asyncio.sleep(1)
        except Exception as e:
            print(f"{Fore.YELLOW}{Style.BRIGHT}Email area button click failed: {str(e)}")

        # Domain field
        try:
            print(f"{Fore.YELLOW}{Style.BRIGHT}Filling domain field")
            domain_input = await page.wait_for_selector('input[name=domain]', timeout=10000)
            if domain_input:
                await domain_input.click()
                await asyncio.sleep(0.5)
                await domain_input.fill('')
                await domain_input.type(os.getenv('DAYCOMICS_DOMAIN'), delay=50)
                print(f"{Fore.GREEN}{Style.BRIGHT}Domain entered successfully")
            else:
                print(f"{Fore.RED}{Style.BRIGHT}Domain input field not found")
        except Exception as e:
            print(f"{Fore.RED}{Style.BRIGHT}Failed to fill domain: {str(e)}")

        # Password field
        try:
            print(f"{Fore.YELLOW}{Style.BRIGHT}Filling password field")
            password_input = await page.wait_for_selector('input[name=password]', timeout=10000)
            if password_input:
                await password_input.click()
                await asyncio.sleep(0.5)
                await password_input.fill('')
                await password_input.type(os.getenv('DAYCOMICS_PASSWORD'), delay=50)
                print(f"{Fore.GREEN}{Style.BRIGHT}Password entered successfully")
            else:
                print(f"{Fore.RED}{Style.BRIGHT}Password input field not found")
        except Exception as e:
            print(f"{Fore.RED}{Style.BRIGHT}Failed to fill password: {str(e)}")

        # Click login button
        print(f"{Fore.YELLOW}{Style.BRIGHT}Submitting login form")
        try:
            login_button = await page.wait_for_selector('#signButton', timeout=10000)
            if login_button:
                await login_button.click()
                print(f"{Fore.GREEN}{Style.BRIGHT}Login button clicked")
            else:
                print(f"{Fore.RED}{Style.BRIGHT}Login button not found")
        except Exception as e:
            print(f"{Fore.RED}{Style.BRIGHT}Failed to click login button: {str(e)}")

        # Wait for login to complete
        print(f"{Fore.YELLOW}{Style.BRIGHT}Waiting for login to complete...")
        await asyncio.sleep(10)
        print(f"{Fore.GREEN}{Style.BRIGHT}Login process completed")

    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Error during login: {str(e)}")
        # Don't raise the exception - try to continue even if login failed


def update_console_output(comic_progress, title, total_ep, current_ep, total_ep_count, current_img=0, total_img=0):
    """Update the console with progress information."""
    # Clear screen and move cursor to home position
    print('\033[2J\033[0f', end='')

    # Create progress bar
    def progress_bar(current, total):
        width = 30
        progress = round((current / total) * width)
        bar = '█' * progress + '░' * (width - progress)
        return f"[{bar}] {current}/{total}"

    # Write new status
    print(
        f"""Comic Number: {progress_bar(comic_progress['current'], comic_progress['total'])} 
        Title: {title} Total Episodes: {total_ep} 
        Episode Number: {progress_bar(current_ep, total_ep_count) if current_ep > 0 else 'Waiting...'} 
        Episode Images: {progress_bar(current_img, total_img) if current_img > 0 else 'Waiting...'}"""
    )


async def parse_daycomics(urls: List[str], progress_callback=None, start_episode=1):
    """Main function to parse and download honeytoon from DayComics."""
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
            print(f"{Fore.GREEN}{Style.BRIGHT}Attempting to login to DayComics")
            await login_to_daycomics(page)

            async with aiohttp.ClientSession() as session:
                for url in urls:
                    current_comic += 1
                    comic_progress = {'current': current_comic, 'total': total_comics}
                    update_console_output(comic_progress, "Loading...", 0, 0, 0)

                    try:
                        await page.goto(url, wait_until='load')
                        await asyncio.sleep(5)

                        # Get comic details
                        title = await page.eval_on_selector('#titleSubWrapper > p', 'el => el.innerText')
                        print(f"{Fore.GREEN}{Style.BRIGHT}Title: {title}")

                        thumbnail = await page.eval_on_selector('#bnrEpisode img', 'el => el.src')
                        print(f"{Fore.GREEN}{Style.BRIGHT}Image: {thumbnail}")

                        # ЗМІНА: Замінюємо genres на genres_raw
                        genres_raw = await page.eval_on_selector_all('#keywordArea span button',
                                                                     'els => els.map(el => el.textContent)')
                        print(f"{Fore.GREEN}{Style.BRIGHT}All genre/tag items: {genres_raw}")

                        # Натискаємо кнопку Details для отримання опису
                        description = ''
                        try:
                            print(f"{Fore.YELLOW}{Style.BRIGHT}Clicking Details button to get description")
                            details_button = await page.wait_for_selector('button.btnRead', timeout=5000)
                            if details_button:
                                await details_button.click()
                                await asyncio.sleep(2)  # Чекаємо, поки з'явиться опис

                                # Отримуємо опис
                                try:
                                    description = await page.eval_on_selector('.cont_area p', 'el => el.innerText')
                                    print(f"{Fore.GREEN}{Style.BRIGHT}Description: {description}")
                                except Exception as e:
                                    print(f"{Fore.YELLOW}{Style.BRIGHT}Failed to get description: {str(e)}")
                                    description = ''

                                # Закриваємо модальне вікно після отримання опису
                                try:
                                    print(f"{Fore.YELLOW}{Style.BRIGHT}Closing the details modal")
                                    # Пошук кнопки закриття або клік за межами модального вікна
                                    close_button = await page.wait_for_selector('.btnClear, .btn-close, .close-button',
                                                                                timeout=3000)
                                    if close_button:
                                        await close_button.click()
                                        print(f"{Fore.GREEN}{Style.BRIGHT}Modal closed using close button")
                                    else:
                                        # Якщо кнопка не знайдена, спробуємо натиснути Escape
                                        await page.keyboard.press('Escape')
                                        print(f"{Fore.GREEN}{Style.BRIGHT}Modal closed using Escape key")

                                    await asyncio.sleep(1)  # Чекаємо, поки модальне вікно закриється
                                except Exception as e:
                                    print(
                                        f"{Fore.YELLOW}{Style.BRIGHT}Failed to close modal, trying alternative methods: {str(e)}")
                                    # Спробуємо клікнути за межами модального вікна
                                    try:
                                        await page.mouse.click(10, 10)  # Клік у верхньому лівому куті сторінки
                                        print(f"{Fore.GREEN}{Style.BRIGHT}Attempted to close modal by clicking outside")
                                        await asyncio.sleep(1)
                                    except Exception:
                                        pass

                        except Exception as e:
                            print(
                                f"{Fore.YELLOW}{Style.BRIGHT}Details button not found or couldn't be clicked: {str(e)}")
                            description = ''

                        update_console_output(comic_progress, title, 0, 0, 0)

                        comic_folder = f"./daycomics/{title}"
                        os.makedirs(comic_folder, exist_ok=True)

                        thumbnail_extension = thumbnail.split('.')[-1]
                        thumbnail_filename = f"{comic_folder}/thumbnail.{thumbnail_extension}"
                        await download_image(thumbnail, thumbnail_filename, session)

                        await asyncio.sleep(1)

                        # Map episodes
                        episodes = await page.eval_on_selector_all('.episodeListCon a', '''
                            (els, parentTitle) => {
                                return els.map(el => {
                                    const titleDesc = el.querySelector('.comicInfo > div > .episodeStitle')?.textContent.trim() || '';
                                    const episodeNumber = el.querySelector('.comicInfo > div > div > p')?.textContent.trim() || '';
                                    const epTitle = `${episodeNumber} ${titleDesc}`.trim();
                                    let dateElem = el.querySelector('.comicInfo > div > .episodeDate')?.textContent.trim() || '';

                                    // ПОКРАЩЕНА ЛОГІКА ВИЗНАЧЕННЯ СТАТУСУ БЛОКУВАННЯ
                                    let isLockedText = el.querySelector('.coinTagCon button')?.textContent.trim() || 'FREE';
                                    let isLocked = false; // За замовчуванням вважаємо відкритим

                                    // Перевіряємо різні варіанти заблокованого контенту
                                    if (isLockedText.includes('COINS') || 
                                        isLockedText.includes('LOCKED') || 
                                        isLockedText.includes('PREMIUM') ||
                                        isLockedText.includes('PAID') ||
                                        (isLockedText.match(/^\d+$/) && parseInt(isLockedText) > 0)) { // Якщо це просто число > 0
                                        isLocked = true;
                                    }

                                    // Перевіряємо варіанти відкритого контенту
                                    if (isLockedText.includes('FREE') || 
                                        isLockedText.includes('VIEW') || 
                                        isLockedText.includes('READ') ||
                                        isLockedText === '' ||
                                        isLockedText === '0') {
                                        isLocked = false;
                                    }

                                    let url = el.href;

                                    let thumbnail = el.querySelector('.flexItem img').src;
                                    if (thumbnail.includes('img_loading')) {
                                        thumbnail = el.querySelector('.flexItem img').getAttribute('data-src');
                                    }

                                    return {
                                        isLocked,
                                        isLockedText, // Додаємо для відлагодження
                                        parentTitle,
                                        title: epTitle,
                                        date: dateElem,
                                        thumbnail,
                                        url
                                    };
                                }).filter(item => item !== null);
                            }
                        ''', title)

                        print(f"{Fore.GREEN}{Style.BRIGHT}Episodes: {len(episodes)}")

                        # НОВЕ: Реверсуємо список епізодів щоб йшли від старіших до новіших (001→50)
                        episodes.reverse()
                        print(f"{Fore.GREEN}{Style.BRIGHT}Episodes reversed to go from oldest to newest")

                        # Перед переходом до першого епізоду і завантаженням епізодів, виконуємо пошук для отримання preview-thumbnail
                        print(f"{Fore.YELLOW}{Style.BRIGHT}Starting search for preview thumbnail")
                        try:
                            # Шукаємо кнопку пошуку і натискаємо на неї для пошуку preview-thumbnail
                            print(f"{Fore.YELLOW}{Style.BRIGHT}Looking for and clicking search button")

                            # Використовуємо точний селектор
                            search_button = await page.query_selector('#sideMenuRight ul li button[id="searchButton"]')

                            # Альтернативні варіанти, якщо точний селектор не спрацює
                            if not search_button:
                                print(f"{Fore.YELLOW}{Style.BRIGHT}Trying specific selector")
                                search_button = await page.query_selector('li button[id="searchButton"]')

                            if not search_button:
                                print(f"{Fore.YELLOW}{Style.BRIGHT}Trying broader search button selector")
                                search_button = await page.query_selector('button[id="searchButton"]')

                            if not search_button:
                                print(f"{Fore.YELLOW}{Style.BRIGHT}Looking for button with search image")
                                search_button = await page.query_selector('button span img[alt="search"]')
                                if search_button:
                                    # Якщо знайшли зображення пошуку, нам потрібно натиснути на батьківську кнопку
                                    search_button = await page.evaluate('''
                                    (el) => {
                                        // Піднімаємося по ієрархії DOM до кнопки
                                        let btn = el;
                                        while (btn && btn.tagName !== 'BUTTON') {
                                            btn = btn.parentElement;
                                        }
                                        return btn;
                                    }
                                    ''', search_button)

                            # Виведемо на екран HTML сторінки для відлагодження, якщо кнопка не знайдена
                            if not search_button:
                                print(f"{Fore.RED}{Style.BRIGHT}Search button not found after multiple attempts")
                                print(f"{Fore.YELLOW}{Style.BRIGHT}Taking a screenshot for debugging")
                                # await page.screenshot(path=f"{comic_folder}/debug_no_search_button.png")  # Закоментовано

                                # Виведемо DOM елементи навігації для відлагодження
                                nav_html = await page.evaluate('''
                                () => {
                                    const nav = document.querySelector('#sideMenuRight');
                                    return nav ? nav.outerHTML : 'Nav element not found';
                                }
                                ''')
                                print(f"{Fore.YELLOW}{Style.BRIGHT}Navigation HTML for debugging: {nav_html[:200]}...")

                                # Спробуємо прямий JavaScript клік
                                print(f"{Fore.YELLOW}{Style.BRIGHT}Trying direct JavaScript click on search button")
                                try:
                                    await page.evaluate('''
                                    () => {
                                        const searchBtn = document.querySelector('#searchButton');
                                        if (searchBtn) {
                                            searchBtn.click();
                                            return true;
                                        }
                                        return false;
                                    }
                                    ''')
                                    await asyncio.sleep(3)
                                except Exception as e:
                                    print(f"{Fore.RED}{Style.BRIGHT}JavaScript click failed: {str(e)}")
                            else:
                                print(f"{Fore.GREEN}{Style.BRIGHT}Search button found, clicking...")
                                # Використовуємо JavaScript для кліку, оскільки це може бути надійніше
                                await page.evaluate('(btn) => btn.click()', search_button)
                                await asyncio.sleep(3)  # Збільшуємо час очікування

                            # Знаходимо поле пошуку та вводимо назву коміксу
                            print(f"{Fore.YELLOW}{Style.BRIGHT}Entering comic title in search field: {title}")
                            search_input = await page.query_selector('#headerSearchInput')

                            if not search_input:
                                print(f"{Fore.YELLOW}{Style.BRIGHT}Looking for search input by placeholder")
                                search_input = await page.query_selector('input[placeholder*="Search"]')

                            if not search_input:
                                print(f"{Fore.YELLOW}{Style.BRIGHT}Taking screenshot of search form")
                                # await page.screenshot(path=f"{comic_folder}/debug_search_form.png")  # Закоментовано

                                # Спробуємо JavaScript для знаходження та заповнення поля вводу
                                print(f"{Fore.YELLOW}{Style.BRIGHT}Trying JavaScript to find and fill search input")
                                search_input_filled = await page.evaluate(f'''
                                (title) => {{
                                    // Шукаємо поле вводу з placeholder для пошуку
                                    const input = document.querySelector('input[placeholder*="Search"], #headerSearchInput, input[type="text"]');
                                    if (input) {{
                                        input.value = title;
                                        // Створюємо і запускаємо подію input для активації пошуку
                                        const event = new Event('input', {{ bubbles: true }});
                                        input.dispatchEvent(event);
                                        return true;
                                    }}
                                    return false;
                                }}
                                ''', title)

                                if search_input_filled:
                                    print(f"{Fore.GREEN}{Style.BRIGHT}Search input filled with JavaScript")
                                    await asyncio.sleep(5)  # Збільшений час очікування для результатів
                            elif search_input:
                                print(f"{Fore.GREEN}{Style.BRIGHT}Search input found, filling...")
                                await search_input.fill('')  # Очищаємо поле вводу
                                await search_input.type(title, delay=100)  # Повільно вводимо текст
                                await asyncio.sleep(5)  # Збільшений час очікування для результатів

                            # Знаходимо зображення з результатів пошуку
                            print(f"{Fore.YELLOW}{Style.BRIGHT}Looking for preview image in search results")

                            # Спочатку перевіримо, чи є результати пошуку
                            result_container = await page.query_selector('#resultSearch')
                            if result_container:
                                print(f"{Fore.GREEN}{Style.BRIGHT}Search results container found")

                                # Шукаємо зображення в результатах
                                preview_img = await page.query_selector('#resultSearch img')

                                if not preview_img:
                                    print(f"{Fore.YELLOW}{Style.BRIGHT}Trying broader image selector in results")
                                    preview_img = await page.query_selector('#resultSearch .thubBox img')

                                if not preview_img:
                                    print(f"{Fore.YELLOW}{Style.BRIGHT}Trying JavaScript to find image in results")
                                    preview_src = await page.evaluate('''
                                    () => {
                                        const img = document.querySelector('#resultSearch img, .resultSearchItem img, .thubBox img');
                                        if (img) {
                                            return img.getAttribute('data-src') || img.src;
                                        }
                                        return null;
                                    }
                                    ''')

                                    if preview_src:
                                        print(
                                            f"{Fore.GREEN}{Style.BRIGHT}Found preview image with JavaScript: {preview_src}")
                                else:
                                    # Отримуємо URL зображення
                                    preview_src = await preview_img.get_attribute('src')
                                    if not preview_src or 'img_loading' in preview_src:
                                        preview_src = await preview_img.get_attribute('data-src')

                                    print(f"{Fore.GREEN}{Style.BRIGHT}Found preview image: {preview_src}")

                                # Зберігаємо preview-thumbnail в папці коміксу
                                if preview_src:
                                    preview_extension = preview_src.split('.')[-1]
                                    if '?' in preview_extension:
                                        preview_extension = preview_extension.split('?')[0]
                                    preview_filename = f"{comic_folder}/preview-thumbnail.{preview_extension}"
                                    await download_image(preview_src, preview_filename, session)
                                    print(
                                        f"{Fore.GREEN}{Style.BRIGHT}Downloaded preview thumbnail to: {preview_filename}")
                                else:
                                    print(f"{Fore.RED}{Style.BRIGHT}No preview image source found in search results")
                            else:
                                print(f"{Fore.RED}{Style.BRIGHT}No search results container found")

                                # Робимо скріншот всієї сторінки для відлагодження
                                # await page.screenshot(path=f"{comic_folder}/no_search_results.png")  # Закоментовано

                            # Закриваємо пошукове поле (натискаємо Escape)
                            print(f"{Fore.YELLOW}{Style.BRIGHT}Closing search by pressing Escape")
                            await page.keyboard.press('Escape')
                            await asyncio.sleep(1)

                        except Exception as e:
                            print(f"{Fore.RED}{Style.BRIGHT}Search failed")
                            # Робимо скріншот поточної сторінки для відлагодження
                            # try:
                            #     await page.screenshot(path=f"{comic_folder}/search_error.png")
                            #     print(f"{Fore.YELLOW}{Style.BRIGHT}Saved page screenshot for debugging")
                            # except Exception:
                            #     pass

                        print(f"{Fore.YELLOW}{Style.BRIGHT}Completed search functionality block")

                        # Click to first episode
                        await page.click('.episodeListCon a')

                        # Check for modal and click "Get In" if it exists
                        try:
                            print(f"{Fore.YELLOW}{Style.BRIGHT}Checking for modal")
                            modal = await page.wait_for_selector('#ModalContainer', timeout=5000)
                            if modal:
                                await page.click('#ModalContainer button:last-child')
                                print(f"{Fore.YELLOW}{Style.BRIGHT}Modal dismissed")
                        except Exception as e:
                            print(f"{Fore.YELLOW}{Style.BRIGHT}ModalContainer not found, continuing...")

                        await asyncio.sleep(5)

                        total_episodes = len(episodes)
                        current_episode = 0
                        update_console_output(comic_progress, title, total_episodes, current_episode, total_episodes)

                        # For each episode, navigate to its page and extract all images
                        for episode in episodes:
                            current_episode += 1

                            # НОВЕ: Пропускаємо епізоди до start_episode
                            if current_episode < start_episode:
                                print(
                                    f"{Fore.YELLOW}{Style.BRIGHT}Skipping episode {current_episode} (starting from {start_episode})")
                                continue

                            update_console_output(comic_progress, title, total_episodes, current_episode,
                                                  total_episodes)

                            # ЗМІНА: Оновлюємо дані епізоду для JSON
                            episode_number = current_episode
                            episode['title'] = f"episode {episode_number}"  # Змінюємо формат title
                            episode['slag'] = f"episode-{episode_number}"  # Додаємо нове поле slag

                            episode_folder = f"./daycomics/{title}/{current_episode}"
                            os.makedirs(episode_folder, exist_ok=True)

                            episode_thumbnail = episode['thumbnail']
                            episode_thumbnail_extension = episode_thumbnail.split('.')[-1]
                            if '?' in episode_thumbnail_extension:
                                episode_thumbnail_extension = episode_thumbnail_extension.split('?')[0]

                            episode_thumbnail_filename = f"{episode_folder}/thumbnail.{episode_thumbnail_extension}"
                            await download_image(episode_thumbnail, episode_thumbnail_filename, session)

                            # ЗМІНА: Оновлюємо шлях до thumbnail в даних епізоду на локальний
                            episode['thumbnail'] = "thumbnail.jpg"  # Завжди використовуємо jpg для уніфікації

                            # ВІДЛАГОДЖЕННЯ: Виводимо інформацію про епізод
                            print(f"{Fore.CYAN}{Style.BRIGHT}Episode {current_episode} info:")
                            print(f"  - URL: {episode.get('url', 'NO URL')}")
                            print(f"  - isLocked: {episode.get('isLocked', 'UNKNOWN')}")
                            print(f"  - Button text: '{episode.get('isLockedText', 'NO TEXT')}'")
                            print(f"  - Episode title: {episode.get('title', 'NO TITLE')}")

                            # Check if URL exists and is valid
                            if not episode.get('url'):
                                print(f"{Fore.RED}{Style.BRIGHT}Episode {current_episode}: No URL found, skipping")
                                continue

                            if episode.get('isLocked', True):
                                print(
                                    f"{Fore.YELLOW}{Style.BRIGHT}Episode {current_episode}: Episode is locked, skipping")
                                continue

                            print(
                                f"{Fore.GREEN}{Style.BRIGHT}Episode {current_episode}: Proceeding to download images...")

                            await page.goto(episode['url'], wait_until='load')

                            # Check for modal and dismiss it
                            try:
                                modal = await page.wait_for_selector('#ModalContainer', timeout=5000)
                                if modal:
                                    await page.click('.coachMarks04 button')
                                    print(f"{Fore.YELLOW}{Style.BRIGHT}Episode modal dismissed")
                            except Exception as e:
                                print(f"{Fore.YELLOW}{Style.BRIGHT}ModalContainer not found for episode, continuing...")

                            # Get images - ОНОВЛЕНИЙ КОД ДЛЯ ЗБОРУ ЗОБРАЖЕНЬ
                            print(f"{Fore.YELLOW}{Style.BRIGHT}Collecting episode images...")

                            # Спочатку прокручуємо сторінку вниз, щоб завантажилися всі зображення
                            await page.evaluate('''
                                () => {
                                    return new Promise((resolve) => {
                                        let totalHeight = 0;
                                        let distance = 100;
                                        let timer = setInterval(() => {
                                            let scrollHeight = document.body.scrollHeight;
                                            window.scrollBy(0, distance);
                                            totalHeight += distance;

                                            if(totalHeight >= scrollHeight){
                                                clearInterval(timer);
                                                resolve();
                                            }
                                        }, 100);
                                    });
                                }
                            ''')

                            # Чекаємо завантаження зображень
                            await asyncio.sleep(3)

                            # Збираємо всі зображення з комікса
                            images = await page.evaluate('''
                                () => {
                                    const imageElements = document.querySelectorAll('#comicContent .imgSubWrapper img');
                                    const imageUrls = [];

                                    imageElements.forEach(img => {
                                        // Спочатку перевіряємо data-src, потім src
                                        let imageUrl = img.getAttribute('data-src') || img.src;

                                        // Пропускаємо base64 заглушки
                                        if (imageUrl && !imageUrl.includes('data:image/gif;base64')) {
                                            imageUrls.push(imageUrl);
                                        }
                                    });

                                    return imageUrls;
                                }
                            ''')

                            print(f"{Fore.GREEN}{Style.BRIGHT}Images found: {len(images)}")

                            # Виводимо перші кілька URL для відлагодження
                            for i, img_url in enumerate(images[:3]):
                                print(f"{Fore.CYAN}{Style.BRIGHT}Image {i + 1}: {img_url[:100]}...")

                            episode['images'] = images
                            del episode['url']  # Remove temporary URL property

                            total_images = len(images)
                            current_image = 0

                            # Download all images for this episode
                            for i, image in enumerate(images):
                                current_image += 1
                                update_console_output(comic_progress, title, total_episodes, current_episode,
                                                      total_episodes,
                                                      current_image, total_images)

                                # Get image extension
                                image_extension = image.split('.')[-1]
                                if 'com' in image_extension:
                                    image_extension = 'jpg'
                                if '?' in image_extension:
                                    image_extension = image_extension.split('?')[0]

                                # ЗМІНА: Використовуємо новий формат назви файлу з великої літери
                                image_filename = f"{episode_folder}/Episode_{current_episode}_{i + 1}.{image_extension}"
                                await download_image(image, image_filename, session)
                                episode['images'][i] = f"episode_{current_episode}_{i + 1}.{image_extension}"

                        print(f"{Fore.GREEN}{Style.BRIGHT}Successfully parsed comic: {title}")

                        # ЗМІНА: Додаємо новий код для форматування JSON даних
                        # Обробка оригінальної назви
                        original_title = title  # Оригінальна назва з усіма символами
                        # Нормалізуємо title - залишаємо тільки букви і пробіли
                        normalized_title = re.sub(r'[^a-zA-Z\s]', '', title)

                        # Обробка жанрів і тегів
                        genres = []
                        tags = []
                        for item in genres_raw:
                            if item.startswith('#'):
                                tags.append(item)
                            else:
                                genres.append(item)

                        # Перевіряємо наявність preview-thumbnail
                        preview_thumbnail_path = ''
                        preview_thumbnail_file = f"{comic_folder}/preview-thumbnail."
                        for ext in ['webp', 'jpg', 'jpeg', 'png', 'gif']:
                            if os.path.exists(f"{preview_thumbnail_file}{ext}"):
                                preview_thumbnail_path = f"preview-thumbnail.{ext}"
                                break

                        # Обробка thumbnail - беремо локальний шлях замість URL
                        thumbnail_extension = thumbnail.split('.')[-1]
                        if '?' in thumbnail_extension:
                            thumbnail_extension = thumbnail_extension.split('?')[0]
                        thumbnail_local = f"thumbnail.{thumbnail_extension}"

                        comics.append({
                            'title': normalized_title,
                            'originalTitle': original_title,
                            'description': description,
                            'thumbnail': thumbnail_local,
                            'previewThumbnail': preview_thumbnail_path,
                            'thumbnailBackground': "",
                            'genres': genres,
                            'tags': tags,
                            'episodes': episodes
                        })
                        # Кінець нового коду

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
        with open('failed_daycomics.json', 'w', encoding='utf-8') as f:
            json.dump(failed_comics, f, indent=2)
        print(
            f"{Fore.YELLOW}{Style.BRIGHT}{len(failed_comics)} honeytoon failed to parse. URLs saved to failed_daycomics.json")

    # Save the result to a JSON file
    with open('daycomics.json', 'w', encoding='utf-8') as f:
        json.dump(comics, f, indent=2)

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

    with open('daycomics.xml', 'w', encoding='utf-8') as f:
        f.write(pretty_xml)

    return failed_comics


async def main():
    # Example usage
    urls = [
        " https://daycomics.com/content/100701ding"
    ]
    try:
        await parse_daycomics(urls)
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Error in main(): {str(e)}")


if __name__ == "__main__":
    # Setup command line interface to input URLs
    import argparse

    parser = argparse.ArgumentParser(description='Download honeytoon from DayComics.com')
    parser.add_argument('--urls', nargs='+', help='URLs to parse')
    parser.add_argument('--file', help='File containing URLs (one per line)')
    parser.add_argument('--example', action='store_true', help='Run with an example URL')
    parser.add_argument('--start', type=int, default=1, help='Start from episode number (default: 001)')

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
        urls = [
            " https://daycomics.com/content/100701ding",
        ]

    if not urls:
        print(f"{Fore.YELLOW}{Style.BRIGHT}No URLs provided. Please use --urls, --file, or --example")
        parser.print_help()
        exit(1)

    # Показуємо з якого епізоду починаємо
    if args.start > 1:
        print(f"{Fore.GREEN}{Style.BRIGHT}Starting from episode {args.start}")

    try:
        asyncio.run(parse_daycomics(urls, start_episode=args.start))
    except KeyboardInterrupt:
        print(f"{Fore.YELLOW}{Style.BRIGHT}\nScript interrupted by user. Exiting...")
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}Unhandled error: {str(e)}")