# Language Toggle Feature Documentation

## Overview
The language toggle feature allows users to switch between English (EN) and Spanish (ES) throughout the application. This feature ensures that laboratory personnel who are more comfortable with Spanish can easily use the application.

## Features

### Toggle UI
- A toggle switch in the application header displays "EN/ES" labels
- EN (English) is the default language
- Clicking the toggle switches to ES (Spanish)
- The current language selection is visually indicated 
- The language preference is persistent across all pages and sessions

### Support for Multiple Languages
- Complete English and Spanish translations for all application text
- Translations include:
  - Menu items and navigation
  - Form labels and button text
  - Instructions and guidance text
  - Error messages and alerts
  - Page titles and section headers

### Technical Implementation

#### Frontend Components
- Language toggle switch in application header
- JavaScript-based translation system 
- Persistent language preference using browser localStorage
- Dynamic text replacement without page reload

#### How It Works
1. **Translation Dictionary**: The system uses a comprehensive dictionary that maps text keys to translations in both languages.

2. **Dynamic Text Replacement**: When the language is changed, all text on the page is instantly updated without requiring a page reload.

3. **Persistence**: The language preference is stored in localStorage, so it remains consistent as users navigate through the application.

4. **Data Attributes**: HTML elements use the `data-i18n` attribute to specify which translation key to use, making the code maintainable.

## Usage Instructions

### For Users
1. Locate the language toggle switch in the top-right corner of the application header.
2. The switch shows "EN" (English) and "ES" (Spanish).
3. English is the default language. The "EN" label appears highlighted when English is active.
4. Click or slide the toggle to switch to Spanish. The "ES" label will become highlighted.
5. All application text will immediately change to the selected language.
6. Your language preference will be remembered across sessions until you change it again.

### For Developers

#### Adding New Text
1. Add new text elements with the `data-i18n` attribute:
```html
<span data-i18n="some_key">Default English text</span>
```

2. Add corresponding translations to the dictionary in `static/js/i18n.js`:
```javascript
en: {
    // ... existing translations
    some_key: "English text"
},
es: {
    // ... existing translations
    some_key: "Spanish text"
}
```

#### Translating Dynamic Content
For JavaScript-generated content, use the translation helper:
```javascript
const translatedText = window.i18n.getTranslation('some_key');
```

#### Adding New Languages
To add support for additional languages:
1. Add a new language section to the translations dictionary
2. Update the language toggle UI to include the new language option
3. Modify the toggle behavior in `i18n.js` to support the additional language

## Testing
- Test the language toggle on all pages to ensure complete translation
- Verify that language preference persists between pages and after browser refresh
- Confirm that dynamically generated content (like error messages) is properly translated
- Test on different browsers and devices to ensure consistent functionality

## Security Considerations
- Translations are performed client-side, reducing server load
- No personal data is sent to the server when changing languages
- Language preference is stored only in the user's browser

## Accessibility
- The language toggle is keyboard accessible
- Visual indication shows which language is currently active
- Toggle has sufficient color contrast for visibility
- Toggle is positioned consistently across all pages for predictability 