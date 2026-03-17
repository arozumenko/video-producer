# Demo Script JSON Format

## Full Schema

```json
{
  "metadata": {
    "title": "Creating Your First Test Case",
    "description": "Walk through creating a test case.",
    "audience": "prospective users",
    "tone": "professional",
    "estimated_duration_seconds": 90,
    "resolution": {"width": 1920, "height": 1080},
    "url": "https://staging.example.com",
    "auth": {
      "type": "cookie",
      "note": "Pre-authenticated session required"
    }
  },
  "scenes": [
    {
      "id": "intro",
      "title": "Opening - Dashboard Overview",
      "steps": [
        {
          "action": "navigate",
          "target": "/dashboard",
          "narration": "Welcome to the app.",
          "pause_before_ms": 0,
          "pause_after_ms": 2000,
          "highlight": null
        }
      ]
    }
  ]
}
```

## Action Reference

| Action | Fields | Description |
|--------|--------|-------------|
| `navigate` | `target` (path or full URL) | Go to a page |
| `click` | `selector` | Click an element |
| `type` | `selector`, `text`, `typing_speed_ms` | Type text with human-like speed |
| `select` | `selector`, `value` | Select dropdown option |
| `scroll` | `selector` (optional), `direction`, `amount` | Scroll page or element |
| `hover` | `selector` | Hover over element (show tooltip/menu) |
| `wait` | `duration_ms` | Just wait (for narration over static screen) |
| `screenshot` | `name` | Save a named screenshot (for thumbnails) |
| `drag` | `from_selector`, `to_selector` | Drag and drop |
| `keyboard` | `key` (e.g. "Enter", "Escape", "Tab") | Press keyboard key |

## Highlight Styles

| Style | Effect |
|-------|--------|
| `pulse` | Subtle pulsing border around element |
| `glow` | Soft glow effect |
| `arrow` | Animated arrow pointing to element |
| `dim-others` | Dim everything except the target element |
| `zoom` | Slight zoom into the element area |

Implementation: inject CSS/JS via `page.evaluate()` before the action, remove after.
