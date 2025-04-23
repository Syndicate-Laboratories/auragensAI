# MongoDB X.509 Certificate Setup for Heroku

This guide explains how to set up your MongoDB X.509 certificate for deployment on Heroku.

## Background

MongoDB Atlas X.509 authentication requires a certificate file. On Heroku, you cannot directly upload files, so you need to:

1. Convert your certificate to base64 format
2. Set it as an environment variable
3. The application will decode it at runtime and save it to a file

## Instructions

### Option 1: Use the Helper Script

We've provided a helper script to convert your certificate:

```bash
# Make the script executable
chmod +x create_mongodb_cert.py

# Run the script with your certificate
./create_mongodb_cert.py /path/to/your/certificate.pem --heroku --env
```

This will:
- Convert your certificate to base64
- Show the Heroku command to set the environment variable
- Show the entry to add to your .env file for local development

### Option 2: Manual Conversion

If you prefer to do it manually:

```bash
# Convert certificate to base64 (MacOS/Linux)
base64 -i /path/to/your/certificate.pem

# Convert certificate to base64 (Windows PowerShell)
[Convert]::ToBase64String([IO.File]::ReadAllBytes("/path/to/your/certificate.pem"))
```

Set the environment variable on Heroku:

```bash
heroku config:set MONGO_X509_CERT_BASE64="YOUR_BASE64_ENCODED_CERTIFICATE" --app auragens-ai
```

## Testing Locally

For local testing, add this to your `.env` file:

```
MONGO_X509_CERT_BASE64="YOUR_BASE64_ENCODED_CERTIFICATE"
```

## Required Environment Variables

Make sure you have all these environment variables set on Heroku:

1. `MONGO_URI` - Your MongoDB connection string
2. `MONGO_X509_CERT_BASE64` - Base64 encoded X.509 certificate
3. `GROQ_API_KEY` - Your Groq API key
4. `ANTHROPIC_API_KEY` - Your Anthropic API key
5. `AUTH0_CLIENT_ID` - Auth0 client ID
6. `AUTH0_CLIENT_SECRET` - Auth0 client secret
7. `AUTH0_DOMAIN` - Auth0 domain
8. `AUTH0_CALLBACK_URL` - Auth0 callback URL
9. `SECRET_KEY` - Flask secret key

## Troubleshooting

If you're having connection issues:

1. Check the Heroku logs: `heroku logs --app auragens-ai`
2. Verify that the certificate is correctly base64-encoded (no extra newlines or spaces)
3. Ensure your MongoDB URI is correct and includes the X.509 authentication mechanism 