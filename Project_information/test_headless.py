# test_headless.py
# Diagnostic: visible browser, capture HTML + metadata at every interval into JSON

import json
import sys
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from datetime import datetime


URL = 'https://eng.stat.gov.tw/np.asp?ctNode=1553'
OUTPUT_JSON = 'snapshots.json'

# Intervals in seconds (cumulative from page load)
INTERVALS = [3, 8, 15, 25, 40, 60]


def get_chrome_ver():
    if sys.platform == 'win32':
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Google\Chrome\BLBeacon',
            )
            return int(winreg.QueryValueEx(key, 'version')[0].split('.')[0])
        except Exception:
            return None
    return None


def collect_snapshot(driver, label):
    """Collect all diagnostic info into a dict."""
    src = driver.page_source
    lower = src.lower()

    # Find cf-turnstile-response dynamically (ID changes each load)
    turnstile_val = None
    try:
        els = driver.find_elements(By.CSS_SELECTOR, 'input[name="cf-turnstile-response"]')
        if els:
            val = els[0].get_attribute('value') or ''
            turnstile_val = f'{len(val)} chars' if val else 'EMPTY'
    except Exception:
        pass

    # Iframes
    iframes = []
    try:
        for f in driver.find_elements(By.TAG_NAME, 'iframe'):
            iframes.append(f.get_attribute('src') or '')
    except Exception:
        pass

    # Div visibility
    divs = {}
    for div_id in ['challenge-success-text', 'challenge-error-text']:
        try:
            el = driver.find_element(By.ID, div_id)
            divs[div_id] = el.is_displayed()
        except Exception:
            divs[div_id] = None

    # JS environment
    js_checks = {}
    try:
        js_checks = driver.execute_script("""
            return {
                userAgent: navigator.userAgent,
                webdriver: navigator.webdriver,
                plugins_count: navigator.plugins.length,
                languages: navigator.languages,
                hardwareConcurrency: navigator.hardwareConcurrency,
                deviceMemory: navigator.deviceMemory || 'undefined',
                platform: navigator.platform,
                webgl_vendor: (function() {
                    try {
                        var c = document.createElement('canvas');
                        var gl = c.getContext('webgl');
                        var ext = gl.getExtension('WEBGL_debug_renderer_info');
                        return gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
                    } catch(e) { return 'error: ' + e.message; }
                })(),
                webgl_renderer: (function() {
                    try {
                        var c = document.createElement('canvas');
                        var gl = c.getContext('webgl');
                        var ext = gl.getExtension('WEBGL_debug_renderer_info');
                        return gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
                    } catch(e) { return 'error: ' + e.message; }
                })(),
                chrome_obj: typeof window.chrome !== 'undefined',
                permissions_query: typeof navigator.permissions !== 'undefined',
            };
        """)
    except Exception as e:
        js_checks = {'error': str(e)}

    # Console logs
    console_logs = []
    try:
        logs = driver.get_log('browser')
        for log in logs[-15:]:
            console_logs.append({'level': log['level'], 'message': log['message'][:300]})
    except Exception:
        pass

    snapshot = {
        'label': label,
        'timestamp': datetime.now().isoformat(),
        'title': driver.title,
        'url': driver.current_url,
        'html_length': len(src),
        'has_just_a_moment': 'just a moment' in lower,
        'has_turnstile': 'turnstile' in lower,
        'has_challenge_success': 'challenge-success' in lower,
        'iframe_count': len(iframes),
        'iframe_srcs': iframes,
        'turnstile_response': turnstile_val,
        'div_visibility': divs,
        'js_environment': js_checks,
        'console_logs': console_logs,
        'html': src,
    }

    # Print summary
    print(f'\n--- {label} ---')
    print(f'  Title: {snapshot["title"]}')
    print(f'  URL:   {snapshot["url"]}')
    print(f'  HTML:  {snapshot["html_length"]} chars')
    print(f'  CF challenge: {snapshot["has_just_a_moment"]}')
    print(f'  Iframes: {snapshot["iframe_count"]}')
    print(f'  Turnstile response: {snapshot["turnstile_response"]}')
    print(f'  success div: {divs.get("challenge-success-text")}')
    ua = js_checks.get('userAgent', '?')
    print(f'  UA: {ua}')
    if console_logs:
        print(f'  Console ({len(console_logs)}):')
        for l in console_logs[-5:]:
            print(f'    [{l["level"]}] {l["message"][:150]}')

    return snapshot


def main():
    ver = get_chrome_ver()
    print(f'Chrome version: {ver}')
    print(f'Mode: HEADLESS + patched UA')
    print(f'Intervals: {INTERVALS}s')

    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    # Patch UA to remove "Headless" — match visible browser fingerprint
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/147.0.0.0 Safari/537.36'
    )

    driver = uc.Chrome(options=options, version_main=ver)
    driver.set_page_load_timeout(120)

    results = {
        'mode': 'headless_patched_ua',
        'chrome_version': ver,
        'url': URL,
        'start_time': datetime.now().isoformat(),
        'intervals': INTERVALS,
        'snapshots': [],
    }

    try:
        print(f'\nNavigating to: {URL}')
        driver.get(URL)

        elapsed = 0
        for target in INTERVALS:
            sleep_time = target - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            elapsed = target

            snap = collect_snapshot(driver, f'{target}s')
            results['snapshots'].append(snap)

            # If past Cloudflare, stop early
            if not snap['has_just_a_moment']:
                print(f'\n  => Cloudflare resolved at {target}s!')
                break
        else:
            print(f'\n  => Still on challenge page after {INTERVALS[-1]}s')

        results['end_time'] = datetime.now().isoformat()
        results['resolved'] = not results['snapshots'][-1]['has_just_a_moment']

    finally:
        # Save JSON
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f'\nSaved all snapshots to {OUTPUT_JSON}')

        driver.quit()
        print('Done')


if __name__ == '__main__':
    main()
