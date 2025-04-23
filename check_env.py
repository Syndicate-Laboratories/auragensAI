#!/usr/bin/env python
"""
Environment Variable Check Script for Auragens AI

This script checks if all required environment variables are set.
It can be run locally or on Heroku before starting the main application.
"""

import os
import sys

# Required environment variables
REQUIRED_VARS = [
    # MongoDB variables
    "MONGO_URI",
    "MONGO_X509_CERT_BASE64",
    
    # API keys
    "GROQ_API_KEY",
    "ANTHROPIC_API_KEY",
    
    # Auth0 configuration
    "AUTH0_CLIENT_ID",
    "AUTH0_CLIENT_SECRET",
    "AUTH0_DOMAIN",
    "AUTH0_CALLBACK_URL",
    
    # Flask configuration
    "SECRET_KEY"
]

# Optional variables
OPTIONAL_VARS = [
    "MONGO_X509_CERT_PATH",  # Optional if using BASE64
    "PORT"  # Heroku sets this automatically
]

def check_environment_variables():
    """Check if required environment variables are set"""
    missing_vars = []
    masked_values = {}
    
    for var in REQUIRED_VARS:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Mask sensitive values
            if var.endswith("_KEY") or var.endswith("SECRET") or var == "MONGO_URI":
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            else:
                masked = value
            masked_values[var] = masked
    
    # Print results
    print("\n=== Environment Variable Check ===")
    
    if missing_vars:
        print(f"\n❌ Missing {len(missing_vars)} required variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your environment or Heroku config.")
    else:
        print("\n✅ All required environment variables are set!")
    
    # Print current values (masked)
    print("\nCurrent Environment Variable Values:")
    for var, value in masked_values.items():
        print(f"  - {var}: {value}")
    
    # Check optional variables
    print("\nOptional Variables:")
    for var in OPTIONAL_VARS:
        value = os.getenv(var)
        status = "✅ Set" if value else "⚠️ Not set"
        print(f"  - {var}: {status}")
    
    return len(missing_vars) == 0

if __name__ == "__main__":
    print(f"Running on: {os.environ.get('DYNO', 'Local environment')}")
    print(f"Current directory: {os.getcwd()}")
    
    success = check_environment_variables()
    
    # Exit with appropriate code
    if not success:
        print("\n❌ Environment check failed. Please set the missing variables.")
        sys.exit(1)
    else:
        print("\n✅ Environment check passed. All required variables are set.")
        sys.exit(0) 