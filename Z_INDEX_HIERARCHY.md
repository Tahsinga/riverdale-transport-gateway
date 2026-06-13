# Z-Index Hierarchy Documentation

## Overview
This document defines the z-index layering system for the Riverdale Academy RFID Portal to prevent modal/popup overlapping issues.

## Z-Index Levels (Ascending Order)

### Base Layers (0-50)
- **z-index: 0** - Default content layer
- **z-index: 5** - Background overlay
- **z-index: 50** - Sticky headers (within modals and main content)
- **z-index: 60** - Sticky headers within modal content

### Navigation Layer (100)
- **z-index: 100** - Sidebar navigation (fixed positioning)
- **z-index: 100** - Mobile bottom navigation

### Modal Layers (1300-3000)
All modals maintain proper stacking order with unique z-index values:

| z-index | Modal ID | Purpose |
|---------|----------|---------|
| 1300 | `modal-students` | Students List Modal |
| 1400 | `modal-payments` | Recent Payments Modal |
| 1500 | `modal-topup` | Top Up Account Modal |
| 1600 | `modal-revenue` | Revenue Report Modal |
| 1700 | `modal-tags` | RFID Tags Modal |
| 1800 | `modal-unregistered-tags` | Unregistered Tags Modal |
| 2400 | `modal-assign-rfid` | Assign RFID Tag Modal |
| 2500 | `modal-edit-student` | Edit Student Modal |
| 3000 | `modal-add-student` | Add Student Modal (Highest Priority) |

## Key Rules

1. **No Duplicate Values**: Each modal has a unique z-index value
2. **Add Student Modal Priority**: Set to 3000 (highest) to ensure it appears above all other modals
3. **Consistent Spacing**: Modals use 100-point increments for future expansion
4. **Sticky Content**: Headers within modals use z-index: 60 to stay visible while scrolling within the modal
5. **Navigation Layer**: Sidebar and navigation elements stay at z-index: 100

## When Adding New Modals

1. Add new z-index values starting at 1900 or higher
2. Ensure values don't conflict with existing modals
3. Document the new modal in this file
4. Use 100-point increments to maintain consistency

## Files Modified

- `myproject/config/templates/config/dashboard.html` - Main dashboard with all modals
- `myproject/config/templates/config/riverdale_login.html` - Login page (z-index: 10 on card)

## Testing

All popups should now appear correctly in front of the page content. Test by:
1. Clicking buttons that open different modals
2. Verify modals don't disappear behind other elements
3. Confirm sticky headers within modals remain visible while scrolling
