/**
 * Internationalization (i18n) module for the Auragens application
 * Supports English and Spanish translations
 */

// Language dictionary
const translations = {
    // English translations (default)
    en: {
        // Common UI elements
        home: "Home",
        upload_document: "Upload Document",
        temperature_tracking: "Temperature Tracking",
        new_chat: "New Chat",
        clear_chat: "Clear Chat",
        export_chat: "Export Chat",
        logout: "Logout",
        save: "Save",
        cancel: "Cancel",
        submit: "Submit",
        export_csv: "Export CSV",
        
        // Temperature tracking page
        lab_temperature_tracking: "Laboratory Temperature Tracking",
        monthly_view: "Monthly View",
        yearly_summary: "Yearly Summary",
        reference_ranges: "Reference Ranges",
        refrigerator: "Refrigerator",
        freezer: "Freezer",
        ln2: "LN2",
        ln2_level: "Liquid Nitrogen Level",
        room: "Room",
        room_temp: "Room Temperature",
        humidity: "Humidity",
        monthly_compliance: "Monthly Compliance",
        yearly_compliance_summary: "Yearly Compliance Summary",
        monthly_breakdown: "Monthly Breakdown",
        compliance_percentage: "Compliance %",
        no_data_available: "No data available for this month",
        overall_compliance: "Overall Compliance",
        
        // Temperature form
        temperature_recording: "Temperature Recording",
        refrigerator_temp: "Refrigerator Temperature (°C)",
        freezer_temp: "Freezer Temperature (°C)",
        ln2_level_pct: "Liquid Nitrogen Level (%)",
        room_temp_c: "Room Temperature (°C)",
        humidity_pct: "Humidity (%)",
        corrective_action: "Corrective Action Taken",
        range: "Range",
        target: "Target",
        above: "Above",
        
        // Compliance messages
        compliant: "Compliant",
        non_compliant: "Non-Compliant",
        corrective_action_required: "Corrective action is required for out-of-range values",
        error_saving: "Error saving data",
        success_saving: "Data saved successfully",
        
        // CSV export
        exporting_data: "Exporting data...",
        export_error: "An error occurred while exporting the data. Please try again."
    },
    
    // Spanish translations
    es: {
        // Common UI elements
        home: "Inicio",
        upload_document: "Subir Documento",
        temperature_tracking: "Registro de Temperatura",
        new_chat: "Nuevo Chat",
        clear_chat: "Borrar Chat",
        export_chat: "Exportar Chat",
        logout: "Cerrar Sesión",
        save: "Guardar",
        cancel: "Cancelar",
        submit: "Enviar",
        export_csv: "Exportar CSV",
        
        // Temperature tracking page
        lab_temperature_tracking: "Registro de Temperatura de Laboratorio",
        monthly_view: "Vista Mensual",
        yearly_summary: "Resumen Anual",
        reference_ranges: "Rangos de Referencia",
        refrigerator: "Refrigerador",
        freezer: "Congelador",
        ln2: "LN2",
        ln2_level: "Nivel de Nitrógeno Líquido",
        room: "Sala",
        room_temp: "Temperatura Ambiente",
        humidity: "Humedad",
        monthly_compliance: "Cumplimiento Mensual",
        yearly_compliance_summary: "Resumen de Cumplimiento Anual",
        monthly_breakdown: "Desglose Mensual",
        compliance_percentage: "% de Cumplimiento",
        no_data_available: "No hay datos disponibles para este mes",
        overall_compliance: "Cumplimiento General",
        
        // Temperature form
        temperature_recording: "Registro de Temperatura",
        refrigerator_temp: "Temperatura del Refrigerador (°C)",
        freezer_temp: "Temperatura del Congelador (°C)",
        ln2_level_pct: "Nivel de Nitrógeno Líquido (%)",
        room_temp_c: "Temperatura Ambiente (°C)",
        humidity_pct: "Humedad (%)",
        corrective_action: "Acción Correctiva Tomada",
        range: "Rango",
        target: "Objetivo",
        above: "Por encima de",
        
        // Compliance messages
        compliant: "Conforme",
        non_compliant: "No Conforme",
        corrective_action_required: "Se requiere acción correctiva para valores fuera de rango",
        error_saving: "Error al guardar datos",
        success_saving: "Datos guardados exitosamente",
        
        // CSV export
        exporting_data: "Exportando datos...",
        export_error: "Ocurrió un error al exportar los datos. Por favor intente de nuevo."
    }
};

// Current language - Default to English
let currentLanguage = 'en';

// Initialize language from localStorage if available
document.addEventListener('DOMContentLoaded', function() {
    // Check for saved language preference
    const savedLanguage = localStorage.getItem('language');
    if (savedLanguage) {
        currentLanguage = savedLanguage;
        updateLanguageToggle(currentLanguage === 'es');
    }
    
    // Apply translations initially
    applyTranslations();
    
    // Set up language toggle event listener
    const languageSwitch = document.getElementById('language-switch');
    if (languageSwitch) {
        languageSwitch.addEventListener('change', function() {
            if (this.checked) {
                // Switch to Spanish
                currentLanguage = 'es';
            } else {
                // Switch to English
                currentLanguage = 'en';
            }
            
            // Save preference
            localStorage.setItem('language', currentLanguage);
            
            // Apply translations
            applyTranslations();
            
            // Update toggle visual state
            updateLanguageToggle(currentLanguage === 'es');
        });
    }
    
    // Update toggle visual state initially
    updateLanguageToggle(currentLanguage === 'es');
});

/**
 * Update language toggle visual state
 * @param {boolean} isSpanish - Whether the current language is Spanish
 */
function updateLanguageToggle(isSpanish) {
    const languageSwitch = document.getElementById('language-switch');
    if (languageSwitch) {
        languageSwitch.checked = isSpanish;
    }
    
    // Update label styling
    const enLabel = document.querySelector('.lang-label[data-lang="en"]');
    const esLabel = document.querySelector('.lang-label[data-lang="es"]');
    
    if (enLabel && esLabel) {
        if (isSpanish) {
            enLabel.classList.remove('active');
            esLabel.classList.add('active');
        } else {
            enLabel.classList.add('active');
            esLabel.classList.remove('active');
        }
    }
}

/**
 * Apply translations to the page based on currentLanguage
 */
function applyTranslations() {
    // Get current language dictionary
    const dictionary = translations[currentLanguage];
    
    // Apply to all elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(function(element) {
        const key = element.getAttribute('data-i18n');
        if (dictionary[key]) {
            element.textContent = dictionary[key];
        }
    });
    
    // Apply to placeholders with data-i18n-placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function(element) {
        const key = element.getAttribute('data-i18n-placeholder');
        if (dictionary[key]) {
            element.placeholder = dictionary[key];
        }
    });
    
    // Apply to buttons
    translateMenuItem('home', 'Home');
    translateMenuItem('upload_document', 'Upload Document');
    translateMenuItem('temperature_tracking', 'Temperature Tracking');
    translateMenuItem('new_chat', 'New Chat');
    translateMenuItem('clear_chat', 'Clear Chat');
    translateMenuItem('export_chat', 'Export Chat');
    translateMenuItem('logout', 'Logout');
    
    // Apply to specific sections based on current page
    translateTemperatureTrackingPage();
}

/**
 * Translate a menu item by its class or id
 * @param {string} key - Translation key
 * @param {string} fallbackText - Default text to look for
 */
function translateMenuItem(key, fallbackText) {
    // Try by specific menu item class
    document.querySelectorAll(`.menu-item.${key}`).forEach(function(element) {
        element.textContent = translations[currentLanguage][key] || fallbackText;
    });
    
    // Try by text content
    document.querySelectorAll('.menu-item').forEach(function(element) {
        if (element.textContent.trim() === fallbackText) {
            element.textContent = translations[currentLanguage][key] || fallbackText;
        }
    });
    
    // Try by id
    const elementById = document.getElementById(key);
    if (elementById) {
        elementById.textContent = translations[currentLanguage][key] || fallbackText;
    }
}

/**
 * Translate temperature tracking specific elements
 */
function translateTemperatureTrackingPage() {
    // Check if we're on the temperature tracking page
    const trackingContainer = document.querySelector('.tracking-container');
    if (!trackingContainer) return;
    
    const dict = translations[currentLanguage];
    
    // Translate buttons
    const monthlyViewBtn = document.getElementById('monthly-view-btn');
    const yearlyViewBtn = document.getElementById('yearly-view-btn');
    const exportCsvBtn = document.getElementById('export-csv-btn');
    
    if (monthlyViewBtn) monthlyViewBtn.textContent = dict.monthly_view;
    if (yearlyViewBtn) yearlyViewBtn.textContent = dict.yearly_summary;
    if (exportCsvBtn) {
        exportCsvBtn.innerHTML = `<i class="fas fa-file-csv"></i> ${dict.export_csv}`;
    }
    
    // Translate reference ranges section
    const refRangesTitle = document.querySelector('.reference-ranges h3');
    if (refRangesTitle) refRangesTitle.textContent = dict.reference_ranges;
    
    document.querySelectorAll('.reference-ranges li span').forEach(function(span) {
        const className = Array.from(span.classList)[0];
        if (dict[className]) {
            span.textContent = dict[className] + ':';
        }
    });
    
    // Translate compliance summary
    const complianceSummaryTitle = document.querySelector('.compliance-summary h3');
    if (complianceSummaryTitle) complianceSummaryTitle.textContent = dict.monthly_compliance;
    
    // Translate yearly view titles
    const yearlySummaryTitle = document.querySelector('.yearly-summary h3');
    if (yearlySummaryTitle) yearlySummaryTitle.textContent = dict.yearly_compliance_summary;
    
    const monthlyBreakdownTitle = document.querySelector('.monthly-breakdown h3');
    if (monthlyBreakdownTitle) monthlyBreakdownTitle.textContent = dict.monthly_breakdown;
    
    // Translate form labels
    document.querySelectorAll('.form-group label').forEach(function(label) {
        const forAttr = label.getAttribute('for');
        
        switch(forAttr) {
            case 'refrigerator-temp':
                label.textContent = dict.refrigerator_temp;
                break;
            case 'freezer-temp':
                label.textContent = dict.freezer_temp;
                break;
            case 'ln2-level':
                label.textContent = dict.ln2_level_pct;
                break;
            case 'room-temp':
                label.textContent = dict.room_temp_c;
                break;
            case 'humidity':
                label.textContent = dict.humidity_pct;
                break;
            case 'corrective-action':
                label.textContent = dict.corrective_action;
                break;
        }
    });
    
    // Translate range indicators
    document.querySelectorAll('.range-indicator').forEach(function(element) {
        if (element.textContent.includes('Range:')) {
            element.textContent = element.textContent.replace('Range:', dict.range + ':');
        }
        if (element.textContent.includes('Target:')) {
            element.textContent = element.textContent.replace('Target:', dict.target + ':');
        }
        if (element.textContent.includes('Above')) {
            element.textContent = element.textContent.replace('Above', dict.above);
        }
    });
    
    // Translate buttons
    const submitBtn = document.querySelector('.submit-btn');
    const cancelBtn = document.querySelector('.cancel-btn');
    
    if (submitBtn) submitBtn.textContent = dict.save;
    if (cancelBtn) cancelBtn.textContent = dict.cancel;
}

// Export functions for use in other modules
window.i18n = {
    getTranslation: function(key) {
        return translations[currentLanguage][key] || key;
    },
    getCurrentLanguage: function() {
        return currentLanguage;
    },
    applyTranslations: applyTranslations
}; 