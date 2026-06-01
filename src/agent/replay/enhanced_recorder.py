"""
Enhanced event recorder that captures Selenium-compatible locators.

Saves more detailed information about actions for reliable Selenium replay:
- CSS selectors
- XPath expressions  
- Element coordinates
- Element text content
- Screenshot data
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ElementLocator:
    """Multiple strategies to locate an element for Selenium."""
    css_selector: Optional[str] = None
    xpath: Optional[str] = None
    text: Optional[str] = None
    tag_name: Optional[str] = None
    coordinates: Optional[dict] = None  # {"x": int, "y": int}
    index: Optional[int] = None  # Fallback to original index
    attributes: Optional[dict] = None  # id, class, name, etc.
    
    def to_dict(self):
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class EnhancedActionRecord:
    """Enhanced record of a single action with multiple locator strategies."""
    timestamp: str
    action_type: str  # "goto", "click", "type", "scroll", "wait", etc.
    tool_name: str
    tool_params: dict
    element_locator: Optional[ElementLocator] = None
    dom_snapshot: Optional[str] = None  # Trimmed DOM for context
    page_title: Optional[str] = None
    page_url: Optional[str] = None
    screenshot_path: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    duration_ms: int = 0
    step: int = 0
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        data = {
            "timestamp": self.timestamp,
            "action_type": self.action_type,
            "tool_name": self.tool_name,
            "tool_params": self.tool_params,
            "page_url": self.page_url,
            "page_title": self.page_title,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "step": self.step,
        }
        if self.element_locator:
            data["element_locator"] = self.element_locator.to_dict()
        if self.dom_snapshot:
            data["dom_snapshot"] = self.dom_snapshot
        if self.screenshot_path:
            data["screenshot_path"] = self.screenshot_path
        if self.error_message:
            data["error_message"] = self.error_message
        return data


class EnhancedRecorder:
    """
    Records agent actions with enhanced information for Selenium replay.
    
    This recorder wraps the standard event subscriber and enriches records with:
    - Stable element locators (CSS selectors, XPath)
    - DOM context snapshots
    - Screenshots
    - Timing information
    """
    
    def __init__(self, output_path: Path, browser_service=None, capture_screenshots: bool = False):
        """
        Initialize the enhanced recorder.
        
        Args:
            output_path: Path to save the enhanced record JSON file
            browser_service: Reference to the browser service (for getting DOM, coordinates, etc.)
            capture_screenshots: Whether to capture screenshots for each action
        """
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.browser_service = browser_service
        self.capture_screenshots = capture_screenshots
        self.records: list[EnhancedActionRecord] = []
        self._start_time: Optional[datetime] = None
    
    async def record_action(
        self,
        action_type: str,
        tool_name: str,
        tool_params: dict,
        element_info: Optional[dict] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: int = 0,
        step: int = 0,
    ):
        """
        Record an action with enhanced information.
        
        Args:
            action_type: Type of action (goto, click, type, etc.)
            tool_name: Name of the tool used
            tool_params: Parameters passed to the tool
            element_info: Information about the element (from browser)
            success: Whether the action succeeded
            error_message: Error message if action failed
            duration_ms: How long the action took
            step: Agent step number
        """
        # Get page information
        page_url = None
        page_title = None
        dom_snapshot = None
        screenshot_path = None
        element_locator = None
        
        if self.browser_service:
            try:
                # Get page URL and title
                page_url = await self._get_page_url()
                page_title = await self._get_page_title()
                
                # Capture DOM context if we have element info
                if element_info:
                    element_locator = self._create_locator(element_info)
                    dom_snapshot = await self._get_dom_context(element_info)
                
                # Capture screenshot if enabled
                if self.capture_screenshots:
                    screenshot_path = await self._capture_screenshot(step)
            except Exception as e:
                logger.warning(f"Failed to capture enhanced info: {e}")
        
        # Create the record
        record = EnhancedActionRecord(
            timestamp=datetime.utcnow().isoformat() + "Z",
            action_type=action_type,
            tool_name=tool_name,
            tool_params=tool_params,
            element_locator=element_locator,
            dom_snapshot=dom_snapshot,
            page_title=page_title,
            page_url=page_url,
            screenshot_path=screenshot_path,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
            step=step,
        )
        
        self.records.append(record)
        self._save()
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Recorded action: {action_type} - {tool_name}")
    
    def _create_locator(self, element_info: dict) -> ElementLocator:
        """Create a locator with multiple strategies from element info."""
        return ElementLocator(
            css_selector=element_info.get("selector"),
            xpath=element_info.get("xpath"),
            text=element_info.get("text"),
            tag_name=element_info.get("tag_name"),
            coordinates=element_info.get("coordinates"),
            index=element_info.get("index"),
            attributes=element_info.get("attributes"),
        )
    
    async def _get_page_url(self) -> Optional[str]:
        """Get current page URL."""
        try:
            if hasattr(self.browser_service, '_browser_state') and self.browser_service._browser_state:
                if self.browser_service._browser_state.current_tab:
                    return self.browser_service._browser_state.current_tab.url
        except Exception:
            pass
        return None
    
    async def _get_page_title(self) -> Optional[str]:
        """Get current page title."""
        try:
            if hasattr(self.browser_service, '_browser_state') and self.browser_service._browser_state:
                if self.browser_service._browser_state.current_tab:
                    return self.browser_service._browser_state.current_tab.title
        except Exception:
            pass
        return None
    
    async def _get_dom_context(self, element_info: dict) -> Optional[str]:
        """Get DOM context around the element."""
        # This would require implementing element context extraction
        # For now, return None (can be enhanced later)
        return None
    
    async def _capture_screenshot(self, step: int) -> Optional[str]:
        """Capture screenshot and return path."""
        try:
            screenshot_dir = self.output_path.parent / "screenshots"
            screenshot_dir.mkdir(exist_ok=True)
            screenshot_path = screenshot_dir / f"step_{step}.png"
            
            # This would require calling browser's screenshot method
            # For now, return the path that would be used
            return str(screenshot_path)
        except Exception as e:
            logger.warning(f"Failed to capture screenshot: {e}")
            return None
    
    def _save(self):
        """Save records to JSON file."""
        try:
            data = {
                "version": "2.0",
                "recorded_at": datetime.utcnow().isoformat() + "Z",
                "records": [r.to_dict() for r in self.records]
            }
            self.output_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except Exception as e:
            logger.error(f"Failed to save enhanced records: {e}")


def convert_to_enhanced_format(old_record_path: Path, new_record_path: Path):
    """
    Convert old record format to enhanced format.
    
    This adds empty locator and context fields that can be populated later.
    """
    try:
        with open(old_record_path, 'r', encoding='utf-8') as f:
            events = json.load(f)
        
        enhanced_records = []
        
        for i, event in enumerate(events):
            if event.get("type") != "TOOL_CALL":
                continue
            
            data = event.get("data", {})
            tool_name = data.get("tool_name", "")
            tool_params = data.get("tool_params", {})
            step = data.get("step", 0)
            
            # Map tool name to action type
            action_type = tool_name.replace("_tool", "")
            
            record = {
                "timestamp": event.get("ts", datetime.utcnow().isoformat() + "Z"),
                "action_type": action_type,
                "tool_name": tool_name,
                "tool_params": tool_params,
                "page_url": None,
                "page_title": None,
                "success": True,
                "duration_ms": 0,
                "step": step,
                "element_locator": {},
            }
            enhanced_records.append(record)
        
        output_data = {
            "version": "2.0",
            "converted_from": str(old_record_path),
            "recorded_at": datetime.utcnow().isoformat() + "Z",
            "records": enhanced_records
        }
        
        new_record_path.parent.mkdir(parents=True, exist_ok=True)
        new_record_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        logger.info(f"Converted {len(enhanced_records)} records to enhanced format")
        return new_record_path
    except Exception as e:
        logger.error(f"Failed to convert record: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    # Example: Convert old format to enhanced format
    if len(sys.argv) > 1:
        old_path = Path(sys.argv[1])
        new_path = old_path.parent / f"{old_path.stem}_enhanced.json"
        convert_to_enhanced_format(old_path, new_path)
        print(f"Converted: {new_path}")
