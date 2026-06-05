# Cost Synchronization & Real-Time Updates

## Overview

Your RFID payment system now has **database-backed cost management** with **real-time synchronization across all connected users**. When one person updates the meal/snack deduction amount, all other users viewing the dashboard see the change instantly.

## Key Features

### ✅ **Database Persistence**
- The cost per ride (`$25` meal/snack deduction) is now stored in the `SystemConfig` database model
- Values persist even after closing the browser
- Changes are saved to the database and used for all subsequent RFID taps

### ✅ **Real-Time Synchronization** 
- The dashboard polls the server every **5 seconds** for cost changes
- When any user saves a new cost via the form, all connected users see the update within 5 seconds
- No page reload required
- Works across multiple tabs and browsers

### ✅ **AJAX-based Updates**
- Replaced the traditional form submission (which would redirect) with AJAX
- Users see immediate feedback: "Saving..." → "✓ Saved"
- No page reload or loss of current data

## How It Works

### Technology Stack
- **Backend**: Django REST endpoints (`/api/cost/`)
- **Database**: `SystemConfig` model stores `cost_per_ride`
- **Frontend**: JavaScript polling with AJAX updates
- **Polling Interval**: 5 seconds (configurable)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  User 1 saves cost: $30                                       │
│  → POST /api/cost/ {"cost": 30}                              │
│  → Saved to SystemConfig.cost_per_ride in database          │
└─────────────────────────────────────────────────────────────┘
        ↓
        (Database Updated)
        ↓
┌──────────────────────────────────────────────────────────────┐
│  User 2's browser polls GET /api/cost/ every 5 seconds       │
│  → Receives {"cost": 30}                                      │
│  → Updates display: "$30" instead of "$25"                   │
│  → paymentAmount variable updated for RFID taps              │
└──────────────────────────────────────────────────────────────┘
```

## API Endpoints

### GET `/api/cost/`
Returns the current cost per ride from the database.

**Response:**
```json
{
  "cost": 25.00
}
```

### POST `/api/cost/`
Updates the cost per ride. Accepts JSON or form-encoded data.

**Request Body (JSON):**
```json
{
  "cost": 30.00
}
```

**Response:**
```json
{
  "status": "ok",
  "cost": 30.00
}
```

## User Interface

The cost management UI is located at the top of the dashboard:

```
Each RFID tap deducts $25.00 (meal/snack)
[Input: 25.00] [Save Button] [Status Message]
```

### How to Update Cost:
1. Enter the new amount in the input field (e.g., `$30.00`)
2. Click the **Save** button
3. See feedback: "Saving..." → "✓ Saved"
4. The value updates in real-time across all connected users

## Configuration

### To Change Polling Interval
Edit [myproject/config/templates/config/dashboard.html](myproject/config/templates/config/dashboard.html) around line **812**:

```javascript
costPollInterval = setInterval(loadCostFromDatabase, 5000); // 5 seconds
```

Change `5000` (milliseconds) to your desired interval:
- `3000` = 3 seconds (more responsive)
- `10000` = 10 seconds (less server load)

### To Disable Polling
Comment out line **813** in the `startCostPolling()` function to only load cost once on page load.

## Code Changes

### 1. Backend - Views (`config/views.py`)
**Added:** `api_cost()` view
- Handles both GET and POST requests
- GET: Returns current cost from database
- POST: Updates cost with validation
- Returns JSON for AJAX

### 2. URLs (`config/urls.py`)
**Added:** `path('api/cost/', views.api_cost, name='api_cost')`

### 3. Frontend - Template (`config/templates/config/dashboard.html`)
**Replaced:** Form submission with AJAX form
- Removed: `<form method="post" action="...">` 
- Added: JavaScript event handlers
- Added: Real-time polling mechanism
- Added: Status feedback UI

**Added JavaScript Functions:**
- `loadCostFromDatabase()` - Fetches cost from server
- `updateCostDisplay()` - Updates UI elements
- `saveCostToDatabase()` - Saves cost via AJAX POST
- `startCostPolling()` - Starts 5-second polling interval

## Testing

### Test 1: Local Update (Single Browser)
1. Open dashboard in browser
2. Change cost value (e.g., `25.00` → `30.00`)
3. Click **Save**
4. Should see "✓ Saved" message
5. Close browser and reopen dashboard
6. **Expected:** Cost is still `$30.00` (persisted in database)

### Test 2: Real-Time Sync (Multiple Browsers)
1. Open dashboard in **Browser A** and **Browser B**
2. In Browser A: Change cost to `$35.00` and click Save
3. Watch Browser B
4. **Expected:** Within 5 seconds, Browser B shows `$35.00` without any manual refresh

### Test 3: RFID Tap with New Cost
1. Update cost to a new value (e.g., `$15.00`)
2. Trigger an RFID tap (via simulation or ESP32)
3. **Expected:** The transaction uses the new cost (`$15.00`), not the old value

## Database Schema

The cost is stored in the `SystemConfig` model:

```python
class SystemConfig(models.Model):
    cost_per_ride = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('1.00'))
```

### Data Example:
```
SystemConfig ID=1, cost_per_ride=25.00
```

If no SystemConfig exists, the `get_solo()` method creates one with the default value.

## Future Enhancement: WebSocket

The current implementation uses **polling** which is suitable for most cases. If you want true real-time updates (sub-second response), consider using **Django Channels** for WebSocket support:

### Setup WebSocket (Optional)

1. Install Django Channels:
```bash
pip install channels channels-redis
```

2. Update `requirements.txt`:
```
channels==4.0.0
channels-redis==4.1.0
```

3. Create a WebSocket consumer in `config/consumers.py`:
```python
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class CostUpdateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("cost_updates", self.channel_name)
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("cost_updates", self.channel_name)
    
    async def cost_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'cost_update',
            'cost': event['cost']
        }))
```

4. Update settings to use Channels:
```python
ASGI_APPLICATION = 'myproject.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [('127.0.0.1', 6379)]},
    }
}
```

5. Update the JavaScript to use WebSocket instead of polling.

## Troubleshooting

### Cost doesn't persist after page reload
- **Cause**: Database not configured properly
- **Fix**: Check `db.sqlite3` exists or database URL is set

### Updates don't sync between browsers
- **Cause**: Polling might be disabled or interval too long
- **Fix**: Check browser console for errors, verify polling interval is active

### "Network error" message when saving
- **Cause**: CSRF token not sent or server error
- **Fix**: Check browser console for error details, verify endpoint exists

### Changes show up for some users but not others
- **Cause**: Polling intervals are staggered
- **Expected**: Changes appear within 5 seconds (default polling interval)

## Files Modified

1. ✅ `myproject/config/views.py` - Added `api_cost()` view
2. ✅ `myproject/config/urls.py` - Added `/api/cost/` route
3. ✅ `myproject/config/templates/config/dashboard.html` - Updated UI and JavaScript

## Support

For questions or issues:
1. Check the browser console (F12 → Console) for JavaScript errors
2. Check Django logs for server errors
3. Verify CSRF token is present in POST requests
4. Test the API directly: `curl http://localhost:8000/api/cost/`
