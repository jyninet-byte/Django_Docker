"""
Selenium test: login with correct and incorrect credentials.

Test case
---------
Pre-requisites: access to the website, a valid user account (created in setUp).

 1. Open a web browser and navigate to the homepage of the website.
 2. Click on the "Login" button in the top right corner of the page.
 3. Enter valid login credentials (username = email, password).
 4. Click the "Login" button.
 5. Verify that the user is successfully logged in to the website.
 6. Click on the "Logout" button in the top right corner of the page.
 7. Verify that the user has successfully logged out of the account.
 8. Enter invalid login credentials.
 9. Click the "Login" button.
10. Verify that the user is not able to log in and receives an appropriate error message.

Run (from the folder with manage.py):
    python manage.py test selenium_tests

Settings through environment variables (PowerShell: $env:NAME="value"):
    SELENIUM_HEADLESS=1   - run without a visible browser window
    SELENIUM_PAUSE=1.5    - pause in seconds after every step (default 1, good for a video)
    SELENIUM_BROWSER=edge - use Microsoft Edge instead of Google Chrome
    SELENIUM_SCREENSHOTS=1 - save a screenshot of every step to ../screenshots/selenium
"""
import os
import time
from pathlib import Path

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from authentication.models import CustomUser

VALID_EMAIL = 'reader@library.com'
VALID_PASSWORD = 'reader123'
INVALID_EMAIL = 'nobody@library.com'
INVALID_PASSWORD = 'wrong-password'
ERROR_MESSAGE = 'Wrong email or password.'

HEADLESS = os.environ.get('SELENIUM_HEADLESS') == '1'
PAUSE = float(os.environ.get('SELENIUM_PAUSE', '0' if HEADLESS else '1'))
BROWSER = os.environ.get('SELENIUM_BROWSER', 'chrome').lower()
SCREENSHOTS_DIR = (Path(__file__).resolve().parent.parent.parent / 'screenshots' / 'selenium'
                   if os.environ.get('SELENIUM_SCREENSHOTS') == '1' else None)


def create_driver():
    """Start Chrome (or Edge). Selenium Manager downloads the right driver automatically."""
    if BROWSER == 'edge':
        options = webdriver.EdgeOptions()
    else:
        options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument('--headless=new')
    options.add_argument('--window-size=1280,900')
    options.add_argument('--lang=en-US')
    # Turn off "Save password?" and "Change your password - found in a data breach" pop-ups:
    # they cover the page and block clicks in Chrome / Edge on Windows.
    options.add_experimental_option('prefs', {
        'credentials_enable_service': False,
        'profile.password_manager_enabled': False,
        'profile.password_manager_leak_detection': False,
    })
    options.add_argument('--disable-features=PasswordLeakDetection,PasswordManagerOnboarding')
    options.add_argument('--disable-save-password-bubble')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    if os.environ.get('CHROME_BINARY'):          # optional: custom browser path
        options.binary_location = os.environ['CHROME_BINARY']
    if os.environ.get('SELENIUM_NO_SANDBOX'):    # needed only inside Linux containers
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

    if BROWSER == 'edge':
        return webdriver.Edge(options=options)
    service = webdriver.ChromeService(executable_path=os.environ['CHROMEDRIVER']) \
        if os.environ.get('CHROMEDRIVER') else webdriver.ChromeService()
    return webdriver.Chrome(options=options, service=service)


class LoginSeleniumTest(StaticLiveServerTestCase):
    """Django starts a test server with a separate test database; Selenium drives a real browser."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.browser = create_driver()
        cls.browser.implicitly_wait(2)
        cls.wait = WebDriverWait(cls.browser, 10)

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def tearDown(self):
        # if a test failed, save what the browser showed: library/selenium_failure_<test>.png
        outcome = getattr(self, '_outcome', None)
        result = getattr(outcome, 'result', None)
        failed = result and any(test is self for test, _ in result.errors + result.failures)
        if failed:
            path = Path(__file__).resolve().parent.parent / f'selenium_failure_{self._testMethodName}.png'
            self.browser.save_screenshot(str(path))
            print(f'  Screenshot of the failure: {path}')
        super().tearDown()

    def setUp(self):
        # Pre-requisite: a valid user account
        self.user = CustomUser.objects.create_user(
            email=VALID_EMAIL, password=VALID_PASSWORD, first_name='Andrii',
            middle_name='', last_name='Melnyk', role=0, is_active=True)
        self.browser.delete_all_cookies()

    # ---------- helpers ----------
    def step(self, number, text):
        print(f'  Step {number}: {text}')

    def screenshot(self, name):
        if SCREENSHOTS_DIR:
            SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            self.browser.save_screenshot(str(SCREENSHOTS_DIR / f'{name}.png'))

    def pause(self):
        if PAUSE:
            time.sleep(PAUSE)

    def find(self, element_id):
        return self.wait.until(EC.visibility_of_element_located((By.ID, element_id)))

    def type_into(self, element_id, value):
        field = self.find(element_id)
        field.clear()
        for char in value:              # type like a person, so it is visible in the video
            field.send_keys(char)
            if PAUSE:
                time.sleep(0.03)

    def open_homepage(self):
        self.browser.get(self.live_server_url + '/')
        self.wait.until(EC.title_contains('Home'))

    def click_login_link(self):
        self.find('login-link').click()
        self.wait.until(EC.url_contains('/auth/login/'))

    def submit_credentials(self, email, password):
        self.type_into('id_email', email)
        self.type_into('id_password', password)
        self.pause()
        self.find('login-button').click()

    def assert_logged_in(self):
        current_user = self.find('current-user')
        self.assertIn('Andrii Melnyk', current_user.text)
        self.assertTrue(self.browser.find_elements(By.ID, 'logout-button'))
        self.assertFalse(self.browser.find_elements(By.ID, 'login-link'))
        self.assertIn('/books/', self.browser.current_url)
        self.assertIn('Hello, Andrii!', self.find('messages').text)

    def assert_logged_out(self):
        self.find('login-link')
        self.assertFalse(self.browser.find_elements(By.ID, 'logout-button'))
        self.assertFalse(self.browser.find_elements(By.ID, 'current-user'))

    # ---------- tests ----------
    def test_login_logout_and_invalid_login(self):
        """The full test case: steps 1-10."""
        print()
        self.step(1, 'open the homepage')
        self.open_homepage()
        self.assert_logged_out()
        self.screenshot('01_homepage')
        self.pause()

        self.step(2, 'click "Log in" in the top right corner')
        self.click_login_link()
        self.assertEqual(self.find('id_email').get_attribute('value'), '')
        self.screenshot('02_login_page')
        self.pause()

        self.step(3, f'enter valid credentials: {VALID_EMAIL} / {"*" * len(VALID_PASSWORD)}')
        self.step(4, 'click the "Log in" button')
        self.submit_credentials(VALID_EMAIL, VALID_PASSWORD)

        self.step(5, 'verify that the user is logged in')
        self.wait.until(EC.url_contains('/books/'))
        self.assert_logged_in()
        self.screenshot('03_logged_in')
        self.pause()

        self.step(6, 'click "Log out" in the top right corner')
        logout_button = self.find('logout-button')
        logout_button.click()
        self.wait.until(EC.staleness_of(logout_button))  # the page has been reloaded

        self.step(7, 'verify that the user is logged out')
        self.wait.until(EC.text_to_be_present_in_element((By.ID, 'messages'), 'You have been logged out.'))
        self.assert_logged_out()
        self.screenshot('04_logged_out')
        # a page for logged-in users is not available any more
        self.browser.get(self.live_server_url + '/books/')
        self.wait.until(EC.url_contains('/auth/login/'))
        self.pause()

        self.step(8, f'enter invalid credentials: {INVALID_EMAIL} / {"*" * len(INVALID_PASSWORD)}')
        self.step(9, 'click the "Log in" button')
        self.submit_credentials(INVALID_EMAIL, INVALID_PASSWORD)

        self.step(10, 'verify that the user is not logged in and sees an error message')
        error = self.find('form-errors')
        self.assertEqual(error.text, ERROR_MESSAGE)
        self.assertIn('/auth/login/', self.browser.current_url)
        self.assert_logged_out()
        self.assertEqual(self.find('id_email').get_attribute('value'), INVALID_EMAIL)
        self.assertEqual(self.find('id_password').get_attribute('value'), '')
        self.screenshot('05_invalid_credentials_error')
        self.pause()

    def test_valid_email_with_wrong_password(self):
        """An existing user with a wrong password cannot log in."""
        self.open_homepage()
        self.click_login_link()
        self.submit_credentials(VALID_EMAIL, INVALID_PASSWORD)
        self.assertEqual(self.find('form-errors').text, ERROR_MESSAGE)
        self.assert_logged_out()
        self.pause()

    def test_empty_credentials(self):
        """Empty fields show 'This field is required.' under both fields."""
        self.open_homepage()
        self.click_login_link()
        self.pause()
        self.find('login-button').click()
        errors = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.error-text')))
        self.assertEqual([e.text for e in errors], ['This field is required.'] * 2)
        self.assert_logged_out()
        self.pause()

    def test_inactive_user_cannot_log_in(self):
        """A deactivated account cannot log in even with the correct password."""
        self.user.is_active = False
        self.user.save()
        self.open_homepage()
        self.click_login_link()
        self.submit_credentials(VALID_EMAIL, VALID_PASSWORD)
        self.assertEqual(self.find('form-errors').text, ERROR_MESSAGE)
        self.assert_logged_out()
        self.pause()
