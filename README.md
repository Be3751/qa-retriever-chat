# Chat App to Generate Sample Answers Based on User's Question and Past Q&A History

## Overview
This project is a chat application that generates sample answers based on the user's question and past Q&A history. It leverages the OpenAI API to generate responses and provides a simple web interface for users to interact with. Additionally, it utilizes hybrid search capabilities powered by Azure Cognitive Search to combine AI-driven semantic search with traditional keyword-based search, ensuring more accurate and relevant results.

This application is based on the following repository: [Azure Search OpenAI Demo](https://github.com/Azure-Samples/azure-search-openai-demo/tree/main).

## How to use 
Run the following command to make provisions for the application:
```bash
cd infra
chmod +x main.sh
./main.sh
```

Run the following command to start the application on your local machine:
```bash
# Install the required modules for the frontend
cd apps/frontend
npm install
# Start the frontend application
npm run dev

cd ../backend
# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate
# Install the required packages for the backend
pip install -r requirements.txt
# Start the backend application
quart run
```

Run the following command to deploy the application:
```bash
# Build the frontend pplication
cd apps/frontend
npm run build

# Zip the backend application
cd ../backend
zip -r app.zip . \
  -x "venv/*" \
  -x "venv/**" \
  -x "*.pyc" \
  -x "__pycache__/*" \
  -x ".env" \
  -x "app.zip"
az webapp deploy \
    --name <your-app-name> \
    --resource-group <your-resource-group> \
    --type zip \
    --src-path app.zip
```
