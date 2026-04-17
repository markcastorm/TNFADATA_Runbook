# scraper.py
# Downloads the Table 6 "Assets Structure for Households Sector" Excel file
# from the Taiwan DGBAS National Statistics site.
# Uses undetected-chromedriver (primary) or selenium+stealth (fallback)
# to bypass Cloudflare Turnstile protection.

import os
import sys
import time
import glob
import logging
import random
import subprocess

import config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Chrome version detection (Windows dev + Linux Docker)
# ─────────────────────────────────────────────────────────────────────────────

def get_chrome_version():
    """Detect Chrome major version — works on Windows (dev) and Linux (Docker)."""
    if sys.platform == 'win32':
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Google\Chrome\BLBeacon',
            )
            return winreg.QueryValueEx(key, 'version')[0].split('.')[0]
        except Exception:
            pass
    for cmd in ['google-chrome', 'google-chrome-stable',
                'chromium', 'chromium-browser']:
        try:
            out = subprocess.check_output(
                [cmd, '--version'], stderr=subprocess.DEVNULL
            ).decode()
            return out.strip().split()[-1].split('.')[0]
        except Exception:
            continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def _human_delay(lo=0.4, hi=1.2):
    """Small random pause to mimic human speed."""
    time.sleep(random.uniform(lo, hi))


def _wait_and_click(driver, by, value, timeout=None, description='element'):
    """Wait for an element to be clickable, scroll into view, then click."""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    timeout = timeout or config.WAIT_TIMEOUT
    wait = WebDriverWait(driver, timeout)
    el = wait.until(EC.element_to_be_clickable((by, value)))
    driver.execute_script('arguments[0].scrollIntoView({block:"center"});', el)
    _human_delay()
    el.click()
    logger.debug(f'Clicked: {description}')
    return el


def _wait_for(driver, by, value, timeout=None, description='element'):
    """Wait for element presence and return it."""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    timeout = timeout or config.WAIT_TIMEOUT
    wait = WebDriverWait(driver, timeout)
    el = wait.until(EC.presence_of_element_located((by, value)))
    logger.debug(f'Found: {description}')
    return el


# ─────────────────────────────────────────────────────────────────────────────
# Driver builder — undetected-chromedriver (primary) with stealth fallback
# ─────────────────────────────────────────────────────────────────────────────

def _build_driver(download_dir):
    """
    Create a Chrome driver that can bypass Cloudflare.
    Tries undetected-chromedriver first (best Cloudflare bypass),
    falls back to selenium + selenium_stealth.
    """
    abs_dl = os.path.abspath(download_dir)
    os.makedirs(abs_dl, exist_ok=True)

    chrome_ver = get_chrome_version()
    chrome_ver_int = int(chrome_ver) if chrome_ver else None

    # ── Try undetected-chromedriver first ────────────────────────────────
    try:
        import undetected_chromedriver as uc

        options = uc.ChromeOptions()

        if config.HEADLESS_MODE:
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
            # Patch UA to remove "HeadlessChrome" — Cloudflare blocks on this
            chrome_ua_ver = chrome_ver or '131'
            options.add_argument(
                f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                f'AppleWebKit/537.36 (KHTML, like Gecko) '
                f'Chrome/{chrome_ua_ver}.0.0.0 Safari/537.36'
            )

        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')

        prefs = {
            'download.default_directory': abs_dl,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': False,
        }
        options.add_experimental_option('prefs', prefs)

        driver = uc.Chrome(
            options=options,
            version_main=chrome_ver_int,
        )
        driver.set_page_load_timeout(config.WAIT_TIMEOUT * 2)

        logger.info(
            f'undetected-chromedriver ready (Chrome {chrome_ver or "auto"}) '
            f'— download dir: {abs_dl}'
        )
        return driver

    except ImportError:
        logger.warning(
            'undetected-chromedriver not installed — '
            'falling back to selenium + stealth'
        )
    except Exception as e:
        logger.warning(
            f'undetected-chromedriver failed: {e} — '
            f'falling back to selenium + stealth'
        )

    # ── Fallback: selenium + selenium_stealth ────────────────────────────
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    try:
        from selenium_stealth import stealth
    except ImportError:
        stealth = None

    chrome_ver = chrome_ver or '131'

    opts = Options()
    if config.HEADLESS_MODE:
        opts.add_argument('--headless=new')
        opts.add_argument('--disable-gpu')

    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument(
        f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        f'AppleWebKit/537.36 (KHTML, like Gecko) '
        f'Chrome/{chrome_ver}.0.0.0 Safari/537.36'
    )

    prefs = {
        'download.default_directory': abs_dl,
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
        'safebrowsing.enabled': False,
    }
    opts.add_experimental_option('prefs', prefs)
    opts.add_experimental_option('excludeSwitches', ['enable-automation'])
    opts.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(config.WAIT_TIMEOUT * 2)

    if stealth is not None:
        stealth(
            driver,
            languages=['en-US', 'en'],
            vendor='Google Inc.',
            platform='Win32',
            webgl_vendor='Intel Inc.',
            renderer='Intel Iris OpenGL Engine',
            fix_hairline=True,
        )
        logger.info('Selenium stealth applied')

    driver.execute_cdp_cmd(
        'Page.addScriptToEvaluateOnNewDocument',
        {'source': 'Object.defineProperty(navigator,"webdriver",'
                    '{get:()=>undefined})'},
    )

    logger.info(f'Chrome driver ready (stealth fallback) — download dir: {abs_dl}')
    return driver


# ─────────────────────────────────────────────────────────────────────────────
# Cloudflare handling
# ─────────────────────────────────────────────────────────────────────────────

def _is_site_loaded(page_source):
    """Check if the actual site content has loaded (past Cloudflare)."""
    lower = page_source.lower()
    # Keywords that appear ONLY on the actual DGBAS statistics pages,
    # NOT on the Cloudflare challenge page.
    indicators = [
        'directorate-general',
        'national accounts',
        'national wealth',
        'statistical database',
        'important indicators',
    ]
    return any(kw in lower for kw in indicators)


def _click_turnstile_checkbox(driver):
    """
    Find the Cloudflare Turnstile iframe and click the checkbox inside it.
    Uses ActionChains for a human-like click at the element coordinates.
    Returns True if the click was attempted.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains

    try:
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        for iframe in iframes:
            src = iframe.get_attribute('src') or ''
            if 'challenges.cloudflare.com' in src or 'turnstile' in src:
                # Human-like: move to the iframe area and click the checkbox
                # The checkbox is roughly in the center-left of the iframe
                _human_delay(0.5, 1.0)

                # Method 1: Use ActionChains to click within the iframe element
                # This clicks the iframe at its visible position (where the checkbox is)
                actions = ActionChains(driver)
                actions.move_to_element(iframe).click().perform()
                logger.info('Clicked Turnstile checkbox via ActionChains')
                _human_delay(1.0, 2.0)
                return True
    except Exception as e:
        logger.debug(f'ActionChains click failed: {e}')

    # Method 2: Switch into iframe and click the inner checkbox element
    try:
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        for iframe in iframes:
            src = iframe.get_attribute('src') or ''
            if 'challenges.cloudflare.com' in src or 'turnstile' in src:
                driver.switch_to.frame(iframe)
                _human_delay(0.3, 0.6)
                try:
                    # Try clicking the visible checkbox/label area
                    body = driver.find_element(By.TAG_NAME, 'body')
                    ActionChains(driver).move_to_element(body).click().perform()
                    logger.info('Clicked inside Turnstile iframe body')
                except Exception:
                    pass
                driver.switch_to.default_content()
                _human_delay(1.0, 2.0)
                return True
    except Exception as e:
        logger.debug(f'Iframe switch click failed: {e}')
        try:
            driver.switch_to.default_content()
        except Exception:
            pass

    return False


def _handle_cloudflare(driver):
    """
    Solve the Cloudflare Turnstile challenge by clicking the checkbox.
    The Turnstile challenge is always present on this site.
    With undetected-chromedriver, clicking the checkbox should pass verification.
    """
    logger.info('Waiting for Cloudflare Turnstile challenge...')

    start = time.time()
    clicked = False

    while time.time() - start < config.CLOUDFLARE_WAIT:
        page_source = driver.page_source

        # Check if site content has loaded (challenge solved)
        if _is_site_loaded(page_source):
            elapsed = time.time() - start
            logger.info(f'Cloudflare passed — site content loaded ({elapsed:.1f}s)')
            return True

        lower = page_source.lower()

        # Cloudflare challenge page detected
        if 'verify you are human' in lower or 'just a moment' in lower:
            if not clicked:
                # Wait a moment for the Turnstile widget to fully render
                logger.info('Turnstile challenge detected — waiting for widget to load...')
                _human_delay(2.0, 3.0)

                # Click the checkbox
                logger.info('Attempting to click Turnstile checkbox...')
                clicked = _click_turnstile_checkbox(driver)

                if clicked:
                    # Give time for verification to process
                    logger.info('Checkbox clicked — waiting for verification...')
                    _human_delay(3.0, 5.0)
                else:
                    logger.warning('Could not find Turnstile checkbox')
            else:
                # Already clicked, check if we need to retry
                elapsed = time.time() - start
                if elapsed > 15 and not _is_site_loaded(driver.page_source):
                    # Retry clicking after some time
                    logger.info('Retrying Turnstile checkbox click...')
                    clicked = False

            _human_delay(2.0, 3.0)
            continue

        # Page in transition
        _human_delay(1.0, 2.0)

    # Final check
    if _is_site_loaded(driver.page_source):
        logger.info('Cloudflare passed after extended wait')
        return True

    logger.warning(
        f'Cloudflare challenge did not resolve within {config.CLOUDFLARE_WAIT}s'
    )
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Navigation steps
# ─────────────────────────────────────────────────────────────────────────────

def _find_and_click_link(driver, link_text, timeout=None):
    """
    Dynamically find a link by its title attribute or visible text
    (partial match) and click it.
    """
    from selenium.webdriver.common.by import By

    timeout = timeout or config.WAIT_TIMEOUT
    logger.info(f'Looking for link: "{link_text}"')

    start = time.time()
    while time.time() - start < timeout:
        # Search by title attribute (most reliable for this site)
        links = driver.find_elements(By.CSS_SELECTOR, f'a[title*="{link_text}"]')
        for link in links:
            try:
                if link.is_displayed():
                    href = link.get_attribute('href') or ''
                    logger.info(f'Found link: "{link_text}" -> {href}')
                    driver.execute_script(
                        'arguments[0].scrollIntoView({block:"center"});', link
                    )
                    _human_delay()
                    link.click()
                    _human_delay(1.5, 3.0)
                    return True
            except Exception:
                continue

        # Fallback: search by visible text
        links = driver.find_elements(By.PARTIAL_LINK_TEXT, link_text)
        for link in links:
            try:
                if link.is_displayed():
                    href = link.get_attribute('href') or ''
                    logger.info(f'Found link (text match): "{link_text}" -> {href}')
                    driver.execute_script(
                        'arguments[0].scrollIntoView({block:"center"});', link
                    )
                    _human_delay()
                    link.click()
                    _human_delay(1.5, 3.0)
                    return True
            except Exception:
                continue

        time.sleep(1)

    raise RuntimeError(f'Link not found: "{link_text}"')


def _navigate_to_category(driver):
    """
    On the main page, find the National Wealth Statistics category
    and click its link to navigate to the category page.
    """
    category = config.NAV_CATEGORY_TITLE
    logger.info(f'Navigating to category: {category}')

    _find_and_click_link(driver, category)
    time.sleep(config.PAGE_LOAD_DELAY)
    logger.info(f'Navigated to: {category}')


def _navigate_to_statistical_tables(driver):
    """
    On the category page, find and click "Statistical Tables".
    """
    target = config.NAV_STATISTICAL_TABLES
    logger.info(f'Navigating to: {target}')

    _find_and_click_link(driver, target)
    time.sleep(config.PAGE_LOAD_DELAY)
    logger.info(f'Navigated to: {target}')


def _find_excel_download_url(driver):
    """
    On the Statistical Tables page, find the Excel download link for
    "Table 6 Assets Structure for Households Sector".
    Returns the direct download URL.
    """
    from selenium.webdriver.common.by import By

    table_title = config.NAV_TABLE_TITLE
    logger.info(f'Looking for Excel link for: {table_title}')

    # The page has <p> elements with table descriptions and <a class="xlsx"> links
    # Find all xlsx links and match the one near "Table 6" text
    xlsx_links = driver.find_elements(By.CSS_SELECTOR, 'a.xlsx')
    logger.info(f'Found {len(xlsx_links)} xlsx links on page')

    for link in xlsx_links:
        try:
            parent = link.find_element(By.XPATH, '..')
            parent_text = parent.text or ''

            if 'Table 6' in parent_text and 'Assets Structure' in parent_text:
                href = link.get_attribute('href')
                logger.info(f'Found Table 6 Excel URL: {href}')
                return href
        except Exception:
            continue

    # Fallback: search all links with xlsx extension
    all_links = driver.find_elements(By.TAG_NAME, 'a')
    for link in all_links:
        href = link.get_attribute('href') or ''
        if 'table6' in href.lower() and href.endswith('.xlsx'):
            logger.info(f'Found Table 6 Excel URL (fallback): {href}')
            return href

    raise RuntimeError(f'Excel download link not found for: {table_title}')


def _download_file_via_requests(url, download_dir, cookies):
    """Download a file using requests with browser cookies."""
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    logger.info(f'Downloading via requests: {url}')
    os.makedirs(download_dir, exist_ok=True)

    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    chrome_ver = get_chrome_version() or '131'
    headers = {
        'User-Agent': (
            f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            f'AppleWebKit/537.36 (KHTML, like Gecko) '
            f'Chrome/{chrome_ver}.0.0.0 Safari/537.36'
        ),
        'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,'
                  'application/octet-stream,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://eng.stat.gov.tw/',
    }

    # verify=False for DGBAS download server (self-signed/misconfigured cert)
    response = session.get(
        url, headers=headers, timeout=config.DOWNLOAD_WAIT_TIME, verify=False
    )
    response.raise_for_status()

    # Extract filename from URL
    filename = url.split('/')[-1]
    file_path = os.path.join(download_dir, filename)

    with open(file_path, 'wb') as f:
        f.write(response.content)

    file_size = os.path.getsize(file_path)
    logger.info(f'Downloaded: {filename} ({file_size:,} bytes)')
    return file_path


def _download_file_via_browser(driver, url, download_dir):
    """
    Download file by navigating to the URL directly in the browser.
    Fallback for when requests-based download fails.
    """
    logger.info(f'Downloading via browser navigation: {url}')

    # Navigate to the download URL directly
    driver.get(url)
    _human_delay(2.0, 4.0)

    # Wait for the file to appear in the download directory
    return _wait_for_downloaded_file(download_dir)


def _wait_for_downloaded_file(download_dir, timeout=None):
    """
    Poll the download directory until an .xlsx file appears
    (and no partial downloads remain).
    """
    timeout = timeout or config.DOWNLOAD_WAIT_TIME
    abs_dir = os.path.abspath(download_dir)
    logger.info(f'Waiting for download in: {abs_dir} (timeout={timeout}s)')

    start = time.time()
    while time.time() - start < timeout:
        partials = (
            glob.glob(os.path.join(abs_dir, '*.crdownload'))
            + glob.glob(os.path.join(abs_dir, '*.tmp'))
        )
        xlsx_files = glob.glob(os.path.join(abs_dir, '*.xlsx'))

        if xlsx_files and not partials:
            xlsx_files.sort(key=os.path.getmtime, reverse=True)
            result = xlsx_files[0]
            file_size = os.path.getsize(result)
            logger.info(
                f'Download complete: {os.path.basename(result)} '
                f'({file_size:,} bytes)'
            )
            return result

        time.sleep(2)

    raise RuntimeError(
        f'Download timed out after {timeout}s — '
        f'no .xlsx file found in {abs_dir}'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def download():
    """
    Full scraping workflow:
      1. Navigate to main page, handle Cloudflare
      2. Click through to National Wealth Statistics -> Statistical Tables
      3. Find Table 6 Excel link and download
    Returns the local path to the downloaded .xlsx file.
    """
    download_dir = config.DOWNLOAD_RUN_DIR
    os.makedirs(download_dir, exist_ok=True)

    driver = None
    try:
        driver = _build_driver(download_dir)

        # ── Step 1: Navigate to main page ─────────────────────────────────
        logger.info(f'Navigating to: {config.BASE_URL}')
        driver.get(config.BASE_URL)
        time.sleep(config.PAGE_LOAD_DELAY)

        # ── Step 2: Handle Cloudflare ─────────────────────────────────────
        cf_passed = _handle_cloudflare(driver)
        if not cf_passed:
            logger.warning('Cloudflare not resolved — attempting navigation anyway')

        # ── Step 3: Navigate to National Wealth Statistics ────────────────
        _navigate_to_category(driver)

        # ── Step 4: Click Statistical Tables ──────────────────────────────
        _navigate_to_statistical_tables(driver)

        # ── Step 5: Find Excel download URL for Table 6 ──────────────────
        excel_url = _find_excel_download_url(driver)

        # ── Step 6: Download the Excel file ───────────────────────────────
        cookies = driver.get_cookies()
        try:
            file_path = _download_file_via_requests(
                excel_url, download_dir, cookies
            )
        except Exception as e:
            logger.warning(f'Requests download failed: {e} — trying browser')
            file_path = _download_file_via_browser(
                driver, excel_url, download_dir
            )

        return file_path

    finally:
        if driver:
            driver.quit()
            logger.info('Browser closed')
