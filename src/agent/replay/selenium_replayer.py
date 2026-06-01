"""
Selenium-based replayer for recorded web automation sessions.

Replays recorded events from JSON records using Selenium WebDriver.
Supports multiple browsers (Chrome, Firefox, Edge) and graceful error handling.
"""

import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException,
    WebDriverException
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.firefox import GeckoDriverManager
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
except ImportError:  # pragma: no cover
    ChromeDriverManager = None
    GeckoDriverManager = None
    EdgeChromiumDriverManager = None

logger = logging.getLogger(__name__)

@dataclass
class ReplayConfig:
    """Configuration for Selenium replay."""
    browser: str = "chrome"  # chrome, firefox, edge
    headless: bool = False
    wait_timeout: int = 10  # seconds
    wait_between_actions: float = 0.5  # seconds
    screenshots_dir: Optional[Path] = None
    verbose: bool = True
    retry_count: int = 3


class SeleniumReplayer:
    """
    Replays recorded web automation sessions using Selenium.
    
    Supported operations:
    - goto_tool: Navigate to URL
    - click_tool: Click elements (by index, selector, or coordinates)
    - type_tool: Type text
    - scroll_tool: Scroll page
    - wait_tool: Wait for conditions
    - extract_tool: Extract data
    - done_tool: Mark task as done
    """
    
    def __init__(self, config: ReplayConfig):
        self.config = config
        self.driver: Optional[webdriver.Chrome] = None
        self.actions: Optional[ActionChains] = None
        self.session_screenshots = []
        self._initialize_driver()
    
    def _initialize_driver(self):
        """Initialize Selenium WebDriver based on config."""
        browser = self.config.browser.lower()

        if browser == "chrome":
            options = ChromeOptions()
            if self.config.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            self.driver = self._create_driver_with_fallback(
                webdriver.Chrome, ChromeService, ChromeDriverManager, options=options
            )
        elif browser == "firefox":
            options = webdriver.FirefoxOptions()
            if self.config.headless:
                options.add_argument("--headless")
            self.driver = self._create_driver_with_fallback(
                webdriver.Firefox, FirefoxService, GeckoDriverManager, options=options
            )
        elif browser == "edge":
            options = webdriver.EdgeOptions()
            if self.config.headless:
                options.add_argument("--headless")
            self.driver = self._create_driver_with_fallback(
                webdriver.Edge, EdgeService, EdgeChromiumDriverManager, options=options
            )
        else:
            raise ValueError(f"Unsupported browser: {self.config.browser}")
        
        self.actions = ActionChains(self.driver)
        self.driver.set_page_load_timeout(self.config.wait_timeout)
        self.driver.implicitly_wait(1)  # Short implicit wait

    def _create_driver_with_fallback(self, driver_cls, service_cls, manager_cls, **kwargs):
        try:
            return driver_cls(**kwargs)
        except WebDriverException as root_error:
            if manager_cls is None:
                raise

            browser = self.config.browser.lower()
            local_driver = self._find_local_driver_path(browser)
            if self.config.verbose:
                logger.warning(f"Automatic driver discovery failed: {root_error}")

            if local_driver:
                if self.config.verbose:
                    logger.info(f"Found local {browser} driver at: {local_driver}")
                return driver_cls(service=service_cls(local_driver), **kwargs)

            if self.config.verbose:
                logger.info("Falling back to webdriver-manager to install browser driver.")

            try:
                manager = manager_cls()
                driver_service = service_cls(manager.install())
                return driver_cls(service=driver_service, **kwargs)
            except Exception as install_error:
                if self.config.verbose:
                    logger.warning(f"webdriver-manager installation failed: {install_error}")
                raise RuntimeError(
                    f"Could not start {browser} webdriver. "
                    "Install the browser driver manually or enable internet access. "
                    "If you have the driver locally, set EDGEWEBDRIVER=/path/to/msedgedriver "
                    "or WEBDRIVER_PATH=/path/to/msedgedriver. "
                    f"Original error: {root_error}; {install_error}"
                ) from install_error

    def _find_local_driver_path(self, browser: str) -> Optional[str]:
        env_vars = {
            "chrome": ["CHROMEDRIVER_PATH", "WEBDRIVER_PATH"],
            "firefox": ["GECKODRIVER_PATH", "WEBDRIVER_PATH"],
            "edge": ["EDGEWEBDRIVER", "WEBDRIVER_PATH"],
        }
        driver_names = {
            "chrome": "chromedriver",
            "firefox": "geckodriver",
            "edge": "msedgedriver",
        }

        for env_var in env_vars.get(browser, []):
            path = os.getenv(env_var)
            if path and Path(path).exists():
                return path

        driver_name = driver_names.get(browser)
        if driver_name:
            path = shutil.which(driver_name)
            if path:
                return path

            common_dirs = [
                Path('/opt/homebrew/bin'),
                Path('/usr/local/bin'),
                Path('/usr/bin'),
                Path('/bin'),
                Path('/usr/sbin'),
                Path('/sbin'),
            ]
            for directory in common_dirs:
                candidate = directory / driver_name
                if candidate.exists() and candidate.is_file():
                    return str(candidate)

        return None

    def _find_indexed_element(self, index: int) -> Optional[Any]:
        """Find element by index using scoped element groups.

        Index-based replay is brittle. Prefer header/nav groups when possible,
        since top menu clicks typically use a small index value.
        """
        scopes = [
            ("topnav", "//ul[contains(@class,'p-0') and .//a[contains(text(),'ホーム')]]/li/a | //ul[contains(@class,'p-0') and .//a[contains(text(),'ホーム')]]/li/button | //ul[contains(@class,'p-0') and .//a[contains(text(),'ホーム')]]/li//*[@role='button']"),
            ("header", "//header//button | //header//a | //header//input[@type='button'] | //header//input[@type='submit'] | //header//*[@role='button']"),
            ("nav", "//nav//button | //nav//a | //nav//input[@type='button'] | //nav//input[@type='submit'] | //nav//*[@role='button']"),
            ("document", "//button | //a | //input[@type='button'] | //input[@type='submit'] | //*[@role='button']"),
        ]

        for name, xpath in scopes:
            elements = [
                el for el in self.driver.find_elements(By.XPATH, xpath)
                if el.is_displayed()
            ]
            if self.config.verbose:
                logger.info(f"Found {len(elements)} visible elements in {name} scope")
            if len(elements) > index:
                return elements[index]

        return None
    
    def _take_screenshot(self, name: str):
        """Take screenshot for debugging."""
        if self.config.screenshots_dir is None:
            return
        
        self.config.screenshots_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = self.config.screenshots_dir / f"{name}.png"
        self.driver.save_screenshot(str(screenshot_path))
        self.session_screenshots.append(str(screenshot_path))
        if self.config.verbose:
            logger.info(f"Screenshot saved: {screenshot_path}")
    
    def _wait_for_element(self, selector: str, by: By = By.CSS_SELECTOR, timeout: Optional[int] = None) -> Any:
        """Wait for element to be present."""
        timeout = timeout or self.config.wait_timeout
        try:
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, selector)))
            return element
        except TimeoutException:
            logger.error(f"Timeout waiting for element: {selector}")
            raise
    
    def _find_element_by_text(self, text: str, tag: str = "*") -> Any:
        """Find element by text content."""
        xpath = f"//{tag}[contains(text(), '{text}')]"
        return self.driver.find_element(By.XPATH, xpath)
    
    def _click_element(self, element: Any, retry: int = 0):
        """Click element with retry logic."""
        try:
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.3)
            
            # Try regular click first
            element.click()
            if self.config.verbose:
                logger.info(f"Clicked element: {element.tag_name}")
        except StaleElementReferenceException:
            if retry < self.config.retry_count:
                logger.warning(f"Stale element, retrying... ({retry + 1}/{self.config.retry_count})")
                time.sleep(0.5)
                # Element reference changed, need to re-find it
                raise
            else:
                raise
        except WebDriverException as e:
            error_text = str(e).lower()
            if retry < self.config.retry_count and ("not clickable" in error_text or "not interactable" in error_text):
                # Element cannot be clicked directly, try JavaScript click
                logger.info(f"Using JavaScript click (attempt {retry + 1})")
                self.driver.execute_script("arguments[0].click();", element)
            else:
                raise
    
    def replay_goto(self, params: dict) -> dict:
        """Replay goto_tool: navigate to URL."""
        url = params.get("url")
        if not url:
            return {"success": False, "error": "URL not specified"}
        
        try:
            if self.config.verbose:
                logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            self._take_screenshot(f"after_goto_{len(self.session_screenshots)}")
            time.sleep(self.config.wait_between_actions)
            return {"success": True, "message": f"Navigated to {url}"}
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            return {"success": False, "error": str(e)}
    
    def replay_click(self, params: dict) -> dict:
        """Replay click_tool: click on element."""
        try:
            # Try different locator strategies in order of preference
            if "selector" in params:
                # CSS selector provided
                selector = params["selector"]
                if self.config.verbose:
                    logger.info(f"Clicking by selector: {selector}")
                element = self._wait_for_element(selector)
            elif "xpath" in params:
                # XPath provided
                xpath = params["xpath"]
                if self.config.verbose:
                    logger.info(f"Clicking by XPath: {xpath}")
                element = self._wait_for_element(xpath, By.XPATH)
            elif "text" in params:
                # Find by text
                text = params["text"]
                tag = params.get("tag", "*")
                if self.config.verbose:
                    logger.info(f"Clicking element with text: {text}")
                element = self._find_element_by_text(text, tag)
            elif "index" in params:
                # Interactive element index (from original recording)
                index = params["index"]
                if self.config.verbose:
                    logger.info(f"Clicking element at index: {index}")
                element = self._find_indexed_element(index)
                if element is None:
                    return {"success": False, "error": f"Element index {index} out of range"}
            elif "coordinates" in params:
                # Click by coordinates
                coords = params["coordinates"]
                if self.config.verbose:
                    logger.info(f"Clicking at coordinates: {coords}")
                self.actions.move_by_offset(coords["x"], coords["y"]).click().perform()
                self._take_screenshot(f"after_click_{len(self.session_screenshots)}")
                time.sleep(self.config.wait_between_actions)
                return {"success": True, "message": f"Clicked at {coords}"}
            else:
                return {"success": False, "error": "No locator strategy specified"}
            
            for attempt in range(self.config.retry_count):
                try:
                    self._click_element(element, attempt)
                    break
                except StaleElementReferenceException:
                    if attempt < self.config.retry_count - 1:
                        # Re-find element
                        if "selector" in params:
                            element = self._wait_for_element(params["selector"])
                        elif "xpath" in params:
                            element = self._wait_for_element(params["xpath"], By.XPATH)
                        elif "index" in params:
                            element = self._find_indexed_element(params["index"])
                        continue
                    else:
                        raise
            
            self._take_screenshot(f"after_click_{len(self.session_screenshots)}")
            time.sleep(self.config.wait_between_actions)
            return {"success": True, "message": "Element clicked"}
        except Exception as e:
            logger.error(f"Failed to click element: {e}")
            return {"success": False, "error": str(e)}
    
    def replay_type(self, params: dict) -> dict:
        """Replay type_tool: type text into element."""
        try:
            selector = params.get("selector", "input, textarea")
            text = params.get("text", "")
            clear_first = params.get("clear_first", True)
            
            if self.config.verbose:
                logger.info(f"Typing into element: {selector}")
            
            element = self._wait_for_element(selector)
            if clear_first:
                element.clear()
            element.send_keys(text)
            
            self._take_screenshot(f"after_type_{len(self.session_screenshots)}")
            time.sleep(self.config.wait_between_actions)
            return {"success": True, "message": f"Typed: {text}"}
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return {"success": False, "error": str(e)}
    
    def replay_scroll(self, params: dict) -> dict:
        """Replay scroll_tool: scroll page."""
        try:
            direction = params.get("direction", "down")
            amount = params.get("amount", 3)
            
            if self.config.verbose:
                logger.info(f"Scrolling {direction} by {amount}")
            
            if direction == "down":
                self.driver.execute_script(f"window.scrollBy(0, {amount * 100});")
            elif direction == "up":
                self.driver.execute_script(f"window.scrollBy(0, -{amount * 100});")
            elif direction == "top":
                self.driver.execute_script("window.scrollTo(0, 0);")
            elif direction == "bottom":
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            time.sleep(self.config.wait_between_actions)
            self._take_screenshot(f"after_scroll_{len(self.session_screenshots)}")
            return {"success": True, "message": f"Scrolled {direction}"}
        except Exception as e:
            logger.error(f"Failed to scroll: {e}")
            return {"success": False, "error": str(e)}
    
    def replay_wait(self, params: dict) -> dict:
        """Replay wait_tool: wait for condition."""
        try:
            wait_time = params.get("time", 1)
            selector = params.get("selector")
            
            if selector:
                if self.config.verbose:
                    logger.info(f"Waiting for element: {selector}")
                self._wait_for_element(selector, timeout=wait_time)
            else:
                if self.config.verbose:
                    logger.info(f"Waiting {wait_time} seconds")
                time.sleep(wait_time)
            
            return {"success": True, "message": f"Wait completed"}
        except Exception as e:
            logger.error(f"Wait failed: {e}")
            return {"success": False, "error": str(e)}
    
    def replay_event(self, event: dict) -> dict:
        """Replay a single event from the record."""
        event_type = event.get("type")
        data = event.get("data", {})
        tool_name = data.get("tool_name", "").lower()
        tool_params = data.get("tool_params", {})
        
        if self.config.verbose:
            logger.info(f"Replaying {tool_name} with params: {tool_params}")
        
        if tool_name == "goto_tool":
            return self.replay_goto(tool_params)
        elif tool_name == "click_tool":
            return self.replay_click(tool_params)
        elif tool_name == "type_tool":
            return self.replay_type(tool_params)
        elif tool_name == "scroll_tool":
            return self.replay_scroll(tool_params)
        elif tool_name == "wait_tool":
            return self.replay_wait(tool_params)
        elif tool_name == "done_tool":
            if self.config.verbose:
                logger.info("Task completed")
            return {"success": True, "message": "Done"}
        else:
            logger.warning(f"Unknown tool: {tool_name}")
            return {"success": True, "message": f"Skipped {tool_name}"}
    
    def replay_from_file(self, record_path: Path) -> dict:
        """Replay all events from a JSON record file."""
        try:
            with open(record_path, 'r', encoding='utf-8') as f:
                events = json.load(f)
            
            logger.info(f"Loaded {len(events)} events from {record_path}")
            
            results = {
                "total_events": len(events),
                "successful": 0,
                "failed": 0,
                "skipped": 0,
                "details": []
            }
            
            for i, event in enumerate(events):
                event_type = event.get("type")
                
                # Skip non-action events
                if event_type not in ["TOOL_CALL", "TOOL_RESULT"]:
                    results["skipped"] += 1
                    continue
                
                # Only process TOOL_CALL events
                if event_type == "TOOL_CALL":
                    result = self.replay_event(event)
                    if result.get("success"):
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                    results["details"].append({
                        "index": i,
                        "event": event,
                        "result": result
                    })
            
            return results
        except Exception as e:
            logger.error(f"Failed to replay from file: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def close(self):
        """Close the browser and clean up."""
        if self.driver:
            self.driver.quit()
            if self.config.verbose:
                logger.info("Browser closed")


def replay_record(record_path: Path, config: ReplayConfig = None) -> dict:
    """
    Convenience function to replay a record file.
    
    Args:
        record_path: Path to the JSON record file
        config: ReplayConfig object (uses defaults if None)
    
    Returns:
        Dictionary with replay results
    """
    if config is None:
        config = ReplayConfig()
    
    replayer = SeleniumReplayer(config)
    try:
        results = replayer.replay_from_file(record_path)
        return results
    finally:
        replayer.close()


if __name__ == "__main__":
    import sys
    
    # Example usage
    if len(sys.argv) > 1:
        record_file = Path(sys.argv[1])
        config = ReplayConfig(
            browser="chrome",
            headless=False,
            screenshots_dir=Path("./replay_screenshots"),
            verbose=True
        )
        results = replay_record(record_file, config)
        print(json.dumps(results, indent=2, default=str))
