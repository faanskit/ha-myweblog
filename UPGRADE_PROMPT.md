# Home Assistant Integration Update Prompt

**Objective:** Update the Home Assistant integration `ha-myweblog` to be compatible with `pyMyweblog` v0.6.0, which implemented the new version, 3.0.0, of Mobile API for myWebLog.

⚠️ **CRITICAL FIRST STEP:** The agent must verify which pyMyweblog APIs are actually used in the ha-myweblog codebase before proceeding (see [APIs Used by Home Assistant Integration](#apis-used-by-home-assistant-integration) section).

This document outlines the API migration from v2.0.3 to v3.0.0 and focuses specifically on the APIs used by the Home Assistant integration.

---

## APIs Used by Home Assistant Integration

**IMPORTANT: Before proceeding, the AI agent MUST verify which APIs are actually used.**

The `ha-myweblog` integration is believed to currently use:
1. ✅ **getObjects()** - to retrieve list of aircraft
2. ✅ **getBookings()** - to retrieve booking information
3. ✅ **obtainAppToken()** - to authenticate and get the app token

### AGENT VERIFICATION TASK (REQUIRED)

**Before making any updates, the AI agent must:**

1. **Search the ha-myweblog codebase** for all imports and calls to `MyWebLogClient`
2. **Identify every method call** on the client instance
3. **Confirm the complete list** of APIs being used
4. **Report findings** with the exact file names and line numbers where each API is called
5. **Compare** against the list above and note any discrepancies

**Report template for agent:**
```
# API Usage Verification Report

## APIs Found in ha-myweblog Codebase:
- [ ] getObjects() - Used in: [file(s) and line numbers]
- [ ] getBookings() - Used in: [file(s) and line numbers]
- [ ] obtainAppToken() - Used in: [file(s) and line numbers]
- [ ] [Other APIs if found] - Used in: [file(s) and line numbers]

## Verification Status:
- [ ] Confirmed: Only getObjects(), getBookings(), obtainAppToken() are used
- [ ] Different: Other APIs are also used (list them above)
- [ ] Need clarification: [describe any issues]

## Conclusion:
[Summary of findings]
```

**Do NOT proceed with update steps until this verification is complete and documented.**

---

## Good News: Minimal Changes Required!

**The Home Assistant integration requires minimal or NO updates** because the APIs it uses have NO breaking changes:

| API | Status | Changes Required |
|-----|--------|-----------------|
| getObjects() | ✅ No breaking changes | None |
| getBookings() | ✅ No breaking changes | None |
| obtainAppToken() | ✅ No breaking changes | None |

---

## Summary of Changes

The `pyMyweblog` library has been updated from using API v2.0.3 to v3.0.0. This document focuses on the APIs relevant to the Home Assistant integration.

---

## API Version Update

- **Old Version:** 2.0.3
- **New Version:** 3.0.0

The client now uses `3.0.0` as the API version. All mock responses and tests must validate against this version.

---

## APIs Used by HA Integration - Detailed Analysis

### 1. getObjects()
**Status:** ✅ **NO CHANGES REQUIRED**

#### Signature (Unchanged)
```python
async def getObjects(self, includeObjectThumbnail: bool = False) -> Dict[str, Any]:
```

#### Response Structure (Unchanged)
```json
{
  "Object": [
    {
      "ID": int,
      "regnr": str,
      "club_id": int,
      "clubname": str,
      "model": str,
      "objectThumbnail": str  // jpg, 150x100 px (optional)
    }
  ]
}
```

#### Integration Impact
- ✅ No code changes needed
- ✅ No parameter changes
- ✅ No response field changes
- The HA integration can continue using this method exactly as before

---

### 2. getBookings()
**Status:** ✅ **NO CHANGES REQUIRED**

#### Signature (Unchanged)
```python
async def getBookings(
    self, 
    airplaneId: str, 
    mybookings: bool = False, 
    includeSun: bool = False
) -> Dict[str, Any]:
```

#### Response Structure (Unchanged)
```json
{
  "Booking": [
    {
      "ID": int,
      "ac_id": int,
      "regnr": str,
      "bStart": timestamp,
      "bEnd": timestamp,
      "fullname": str,
      "fritext": str,
      "platserkvar": int,
      "bobject_cat": int,
      "club_id": int,
      "user_id": int,
      "typ": str,
      "primary_booking": bool,
      "elevuserid": int,
      "completeMobile": str,
      "email": str
    }
  ],
  "sunData": {  // Optional, if includeSun=True
    "refAirport": {...},
    "dates": {...}
  }
}
```

#### Integration Impact
- ✅ No code changes needed
- ✅ No parameter changes
- ✅ No response field changes
- The HA integration can continue using this method exactly as before

---

### 3. obtainAppToken()
**Status:** ✅ **NO CHANGES REQUIRED**

#### Signature (Unchanged)
```python
async def obtainAppToken(self, app_secret: str) -> None:
```

#### Functionality (Unchanged)
- Obtains the app token from Netlify using the app secret
- Sets `client.app_token` internally
- No breaking changes to the method

#### Integration Impact
- ✅ No code changes needed
- ✅ Behavior is identical
- The HA integration can continue using this method exactly as before

---

## Other APIs (Not Used by HA Integration)

The following APIs have breaking changes but are **NOT used** by the HA integration:

- `getTransactions()` - Added parameters and response field changes
- `getFlightLog()` - Added parameters and new fields
- `getFlightLogReversed()` - Added parameters and new fields
- `createBooking()` - Type changes, datetime format changes, parameter renames, response format changes
- `cutBooking()` - Response format changes
- `deleteBooking()` - Response format changes

These changes are documented in the [Full API Reference](#full-api-reference) section below for completeness.

---

## Migration Steps for HA Integration

### Phase 1: Compatibility Check ✅ (COMPLETE)
- Verify that HA integration only uses getObjects(), getBookings(), and obtainAppToken()
- Confirm that none of these APIs have breaking changes
- **Conclusion:** No breaking changes detected for HA integration

### Phase 2: Testing
- Run existing HA tests against the updated pyMyweblog v0.6.0
- Verify getObjects() still returns aircraft list
- Verify getBookings() still returns booking information
- Verify obtainAppToken() still authenticates correctly

### Phase 3: Deployment
- Update pyMyweblog dependency to v0.6.0 or newer
- Deploy updated HA integration
- No code changes required in HA integration itself

---

## Full API Reference

For completeness, here is documentation of all API changes (including those not used by HA integration):

**Status:** ⚠️ BREAKING CHANGES

#### Old Signature (v2.0.3)
```python
async def getTransactions(self) -> Dict[str, Any]:
    # No parameters
```

#### New Signature (v3.0.0)
```python
async def getTransactions(
    self,
    limit: int = 20,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> Dict[str, Any]:
```

#### Changes Required in HA Integration:
1. **Add parameter support:**
   - `limit` (default: 20) - number of transactions to retrieve
   - `from_date` (optional) - filter transactions from this date
   - `to_date` (optional) - filter transactions up to this date

2. **Response field name changes:**
   - `'date'` → `'datum'` (transaction date in yyyy-mm-dd format)
   - `'amount'` → `'belopp'` (transaction amount as decimal)
   - `'description'` → removed/changed to `'comment'`
   - `'balance_after'` → removed
   - ✅ NEW: `'created'` (timestamp yyyy-mm-dd hh:mm:ss when created)
   - ✅ NEW: `'bookedby_fullname'` (who booked the transaction)
   - ✅ NEW: `'BalanceAtToDate'` (balance at the end of the period)
   - ✅ NEW: `'UsedCountLimit'` (count limit usage)

#### Example Migration:
```python
# Old code
result = await client.getTransactions()
for tx in result.get('Transaction', []):
    amount = tx['amount']
    date = tx['date']

# New code
result = await client.getTransactions(limit=30)
for tx in result.get('Transaction', []):
    amount = tx['belopp']
    date = tx['datum']
    created = tx['created']
    bookedby = tx['bookedby_fullname']
```

---

### 5. getFlightLog()

**Status:** ⚠️ BREAKING CHANGES

#### Old Signature (v2.0.3)
```python
async def getFlightLog(self) -> Dict[str, Any]:
    # No parameters
```

#### New Signature (v3.0.0)
```python
async def getFlightLog(
    self,
    limit: int = 20,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    myflights: bool = False,
    ac_id: Optional[int] = None,
) -> Dict[str, Any]:
```

#### Changes Required in HA Integration:
1. **Add parameter support:**
   - `limit` (default: 20) - number of flight records to retrieve
   - `from_date` (optional) - filter flights from this date
   - `to_date` (optional) - filter flights up to this date
   - `myflights` (default: False) - only own flights if True
   - `ac_id` (optional) - filter by aircraft ID

2. **New response fields (added in v3.0.0):**
   - ✅ `'fullname'` (pilot name)
   - ✅ `'tach_start'` (tachometer start time hh:mm)
   - ✅ `'tach_end'` (tachometer end time hh:mm)
   - ✅ `'tach_total'` (total tachometer time as decimal)
   - ✅ `'flights'` (number of flights as int)
   - ✅ `'distance'` (distance as decimal)
   - ✅ `'rowID'` (row identifier as int)

3. **Type changes:**
   - `'ac_id'` is now `int` (was `str`)

#### Example Migration:
```python
# Old code
result = await client.getFlightLog()
for flight in result.get('FlightLog', []):
    ac_id = flight['ac_id']  # was string

# New code
result = await client.getFlightLog(limit=20, myflights=False)
for flight in result.get('FlightLog', []):
    ac_id = flight['ac_id']  # now int
    pilot = flight['fullname']  # NEW
    tach_time = flight['tach_total']  # NEW
    distance = flight['distance']  # NEW
```

---

### 6. getFlightLogReversed()

**Status:** ⚠️ BREAKING CHANGES (same as getFlightLog)

#### Old Signature (v2.0.3)
```python
async def getFlightLogReversed(self) -> Dict[str, Any]:
    # No parameters, used hardcoded values internally
```

#### New Signature (v3.0.0)
```python
async def getFlightLogReversed(
    self,
    limit: int = 20,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    myflights: bool = False,
    ac_id: Optional[int] = None,
) -> Dict[str, Any]:
```

#### Changes:
- **Removed:** Hardcoded date filtering (was: from_date="2025-05-31", to_date="2025-05-31", myflights=1)
- **Added:** Same parameters as getFlightLog()
- **Added:** Same new response fields as getFlightLog()
- Response is identical to getFlightLog but in reversed order (newer first)

#### Example Migration:
```python
# Old code
result = await client.getFlightLogReversed()  # No parameters

# New code
result = await client.getFlightLogReversed(limit=20)  # Add parameters
```

---

### 7. createBooking()

**Status:** ⚠️ BREAKING CHANGES (CRITICAL)

#### Old Signature (v2.0.3)
```python
async def createBooking(
    self,
    ac_id: str,
    bStart: str,  # Format: "YYYY-MM-DD HH:MM:SS"
    bEnd: str,    # Format: "YYYY-MM-DD HH:MM:SS"
    fullname: Optional[str] = None,
    comment: Optional[str] = None,
) -> Dict[str, Any]:
```

#### New Signature (v3.0.0)
```python
async def createBooking(
    self,
    ac_id: int,
    bStart: str,  # Format: "YYYY-MM-DDTHH:MM+HH:MM" (ISO 8601 with timezone)
    bEnd: str,    # Format: "YYYY-MM-DDTHH:MM+HH:MM" (ISO 8601 with timezone)
    fritext: Optional[str] = None,
    expectedAirborne: Optional[float] = None,
    platserkvar: Optional[int] = None,
) -> Dict[str, Any]:
```

#### Changes Required in HA Integration:
1. **Type change for ac_id:**
   - `ac_id: str` → `ac_id: int`

2. **DateTime format change:**
   - Old: `"2025-05-01 10:00:00"` (system time)
   - New: `"2025-05-01T10:00+02:00"` (ISO 8601 with timezone offset)

3. **Parameter name changes:**
   - `fullname` → `fritext` (booking text/comment)
   - `comment` → `fritext` (booking text/comment)

4. **New parameters:**
   - `expectedAirborne` (optional, float) - expected airborne time in hours
   - `platserkvar` (optional, int) - seat reservation

5. **Response field changes:**
   - Old: `{'Result': 'OK', 'BookingID': 1234}`
   - New: `{'infoMessageTitle': 'string', 'infoMessage': 'string', 'errorMessage': 'string (if error)'}`

#### Example Migration:
```python
# Old code
from datetime import datetime
bStart = datetime(2025, 5, 1, 10, 0).strftime("%Y-%m-%d %H:%M:%S")
bEnd = datetime(2025, 5, 1, 12, 0).strftime("%Y-%m-%d %H:%M:%S")
result = await client.createBooking(
    ac_id="1118",
    bStart=bStart,
    bEnd=bEnd,
    fullname="John Doe",
    comment="Business flight"
)
if result.get("Result") == "OK":
    booking_id = result.get("BookingID")

# New code
from datetime import datetime
import pytz
tz = pytz.timezone('Europe/Stockholm')
dt_start = tz.localize(datetime(2025, 5, 1, 10, 0))
dt_end = tz.localize(datetime(2025, 5, 1, 12, 0))
bStart = dt_start.strftime("%Y-%m-%dT%H:%M%z")
bStart = bStart[:-2] + ":" + bStart[-2:]  # Add colon to timezone
bEnd = dt_end.strftime("%Y-%m-%dT%H:%M%z")
bEnd = bEnd[:-2] + ":" + bEnd[-2:]

result = await client.createBooking(
    ac_id=1118,  # Now int
    bStart=bStart,  # ISO 8601 format
    bEnd=bEnd,      # ISO 8601 format
    fritext="Business flight",  # Renamed parameter
    expectedAirborne=2.0,  # NEW
    platserkvar=1  # NEW
)
if result.get("infoMessageTitle"):
    # Booking successful
    info_msg = result.get("infoMessage")
elif result.get("errorMessage"):
    # Booking failed
    error = result.get("errorMessage")
```

---

### 8. cutBooking()

**Status:** ⚠️ RESPONSE FORMAT CHANGE

#### Signature
```python
async def cutBooking(self, booking_id: str) -> Dict[str, Any]:
```

#### Changes:
- Method signature unchanged
- **Response format changed:**
  - Old: `{'Result': 'OK', 'bookingID': 1234}`
  - New: `{'infoMessageTitle': 'string', 'infoMessage': 'string', 'errorMessage': 'string (if error)'}`

#### Example Migration:
```python
# Old code
result = await client.cutBooking("1234")
if result.get("Result") == "OK":
    booking_id = result.get("bookingID")

# New code
result = await client.cutBooking("1234")
if result.get("infoMessageTitle"):
    info = result.get("infoMessage")
elif result.get("errorMessage"):
    error = result.get("errorMessage")
```

---

### 9. deleteBooking()

**Status:** ⚠️ RESPONSE FORMAT CHANGE

#### Signature
```python
async def deleteBooking(self, booking_id: str) -> Dict[str, Any]:
```

#### Changes:
- Method signature unchanged
- **Response format changed:**
  - Old: `{'Result': 'OK', 'bookingID': 1234}`
  - New: `{'infoMessageTitle': 'string', 'infoMessage': 'string', 'errorMessage': 'string (if error)'}`

#### Example Migration:
```python
# Old code
result = await client.deleteBooking("1234")
if result.get("Result") == "OK":
    booking_id = result.get("bookingID")

# New code
result = await client.deleteBooking("1234")
if result.get("infoMessageTitle"):
    info = result.get("infoMessage")
elif result.get("errorMessage"):
    error = result.get("errorMessage")
```

---

## Files to Update in ha-myweblog

### HA Integration Code
- **Status:** ❌ NO CODE CHANGES NEEDED
- The integration does not use any APIs with breaking changes
- Continue using getObjects(), getBookings(), and obtainAppToken() exactly as before

### Dependencies / Requirements
- **Update:** `requirements.txt` or `setup.py`
- Change: `pyMyweblog>=0.5.x` → `pyMyweblog>=0.6.0`
- This is the ONLY change needed for the HA integration

### Testing
- Run existing test suite - all tests should still pass
- No new tests required for HA integration (no behavior changes)
- The underlying API is compatible

---

## Testing Checklist for HA Integration

- [ ] Verify getObjects() returns aircraft list (unchanged format)
- [ ] Verify getBookings() returns booking data (unchanged format)
- [ ] Verify obtainAppToken() authenticates successfully
- [ ] Run existing HA integration tests
- [ ] Verify no regression in functionality
- [ ] Update pyMyweblog dependency version in documentation

---

## Resources

- **Updated pyMyweblog library:** Located in `pyMyweblog/client.py`
- **Test cases:** Located in `tests/test_client.py` - these demonstrate the correct usage patterns
- **Updated scripts:** `scripts/myweblog.py` and `scripts/booking_cli.py` show integration examples
- **API Specification:** https://api.myweblog.se/index.php?page=mobile (v3.0.0)

---

## Additional Notes

- All datetime handling must include timezone information in the new format
- The `fritext` parameter is designed to store booking-related text (formerly split between `fullname` and `comment`)
- Response validation now requires matching both `qType` and `APIVersion` (3.0.0)
- Ensure backward compatibility is not required - this is a full migration to v3.0.0

