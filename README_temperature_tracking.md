# Laboratory Temperature Tracking Feature

## Overview
The Laboratory Temperature Tracking feature is a calendar-based system for laboratory personnel to log and monitor temperature readings for critical equipment. It enables compliance tracking for:

- Refrigerator temperature (2°C - 8°C)
- Freezer temperature (-30°C to -15°C)
- Liquid Nitrogen percentage level (above 60% capacity)
- Room temperature (20°C - 25°C)
- Humidity level (30% - 60%)

The system provides visual indicators when readings are out of acceptable range and prompts for corrective actions.

## Features

### Calendar Interface
- Monthly calendar view displaying all days
- Color-coded status indicators (green for compliant, red for non-compliant)
- Visual status dots for each parameter being tracked
- Highlighting of the current day

### Temperature Entry Form
- Form appears when clicking on a calendar day
- Input fields for all required measurements
- Reference ranges displayed next to each field
- Automatic validation against reference ranges
- Corrective action required when values are out of range

### Compliance Tracking
- Monthly compliance overview with percentage stats
- Parameter-specific compliance metrics
- Yearly summary view with month-by-month breakdown
- Data visualization of compliance trends

### Data Export
- Export temperature data as CSV file
- Context-aware export (monthly or yearly data)
- Complete record including compliance status and corrective actions
- Automatic filename generation based on date range
- Compatible with Excel, Google Sheets, and other spreadsheet programs

## Technical Implementation

### Frontend
- HTML: `templates/temperature_tracking.html`
- CSS: `static/css/temp_tracking.css`
- JavaScript: `static/js/temp_tracking.js`

### Backend
- Routes in `app.py`:
  - GET/POST `/temperature-data`: Retrieve or save temperature readings
  - GET `/temperature-compliance`: Get compliance data for date range
  - GET `/temperature-compliance-yearly`: Get yearly compliance summary
  - GET `/export-temperature-data`: Export data as CSV file
- MongoDB collection: `temperature_records` with index on date field

### Data Model
```json
{
  "date": "YYYY-MM-DD",
  "refrigerator_temp": 4.5,
  "freezer_temp": -20.2,
  "ln2_level": 75,
  "room_temp": 22.5,
  "humidity": 45,
  "corrective_action": "Text explanation when required",
  "is_compliant": true,
  "compliance": {
    "refrigerator": true,
    "freezer": true,
    "ln2": true,
    "room": true,
    "humidity": true
  },
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp"
}
```

## User Workflow
1. Navigate to Temperature Tracking from the main menu
2. Select a day in the calendar to enter or update readings
3. Enter temperature and humidity values
4. If values are out of range, the form will automatically request corrective action details
5. Submit the form to save the data
6. View monthly compliance statistics at the bottom of the page
7. Toggle to Yearly Summary to view long-term compliance data
8. Export data to CSV for reporting or further analysis by clicking the Export CSV button

## Accessibility Features
- Responsive design works on desktop and mobile devices
- Color-coding is supplemented with symbols for color-blind users
- Clear error indicators for out-of-range values
- Well-structured layout with intuitive navigation

## Future Enhancements
- Email notifications for non-compliant readings
- PDF report generation for audits
- User permissions to restrict editing of past entries
- Integration with external monitoring systems
- Additional data visualization options 