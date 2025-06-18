# Knowledge Transfer Tool

A comprehensive knowledge transfer application that combines document processing, AI-powered chat, and process visualization to facilitate knowledge sharing and documentation.

## Features

- **Document Processing**: Upload and process PDF, DOCX, PPTX, and Excel files
- **AI-Powered Chat**: Interactive chat interface with document context
- **Process Visualization**: Generate Mermaid diagrams and process checklists
- **Voice Input**: Voice-to-text functionality for hands-free interaction (requires HTTPS)
- **Process Management**: Create, manage, and track knowledge transfer processes

## Architecture

- **Frontend**: React.js with Tailwind CSS and shadcn/ui components
- **Backend**: FastAPI with SQLAlchemy ORM
- **Database**: SQLite (development) / PostgreSQL (production)
- **AI Integration**: OpenAI GPT models via LangChain
- **Vector Storage**: ChromaDB for document embeddings

## Prerequisites

- **Python 3.8+** (Python 3.9+ recommended)
- **Node.js 16+** and **npm** (Node.js 18+ recommended)
- **OpenAI API Key** (required for AI features)
- **Git** (for cloning the repository)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Know-Transfer
```

### 2. Environment Configuration

Create a `.env` file in the `knowledge_transfer_tool/` directory:

```bash
cd knowledge_transfer_tool
```

Create `.env` file with the following content:

```env
# Database Configuration
DATABASE_URL=sqlite:///./knowledge_transfer.db

# File Upload Configuration
UPLOAD_DIRECTORY=./uploads
VECTOR_STORE_PATH=./vector_store

# OpenAI Configuration (Required)
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Custom Settings
MAX_FILE_SIZE_MB=50
SUPPORTED_FILE_TYPES=pdf,docx,pptx,xlsx
```

**⚠️ Important**: Replace `your_openai_api_key_here` with your actual OpenAI API key. Get one at [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

### 3. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# .\venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Return to project root
cd ..
```

### 4. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Make build script executable (macOS/Linux only)
chmod +x build.sh

# Return to project root
cd ..
```

### 5. Run the Application

From the project root directory (`Know-Transfer/`):

```bash
# Ensure backend virtual environment is activated
# Then run the application

# For basic functionality (HTTP):
python run.py

# For voice input functionality (HTTPS required):
python run.py --https
```

**Available options:**
- `--https`: Enable HTTPS with self-signed certificate (required for voice input)
- `--port <number>`: Specify port (default: 8080)
- `--host <address>`: Specify host (default: 0.0.0.0)

The application will:
1. Build the React frontend
2. Copy static files to the backend
3. Start the FastAPI server on the specified port

### 6. Access the Application

**For basic functionality:**
- **http://localhost:8080**

**For voice input (HTTPS):**
- **https://localhost:8080**
- ⚠️ **Note**: You'll see a browser security warning for the self-signed certificate
- Click "Advanced" → "Proceed to localhost (unsafe)" to continue

## Audio Recording Setup

Voice input requires HTTPS due to browser security restrictions. We provide two options:

### Option 1: Auto-generate certificates (Recommended)
```bash
# Run with HTTPS - certificates will be auto-generated
python run.py --https
```

### Option 2: Generate certificates manually
```bash
# Generate certificates first
python generate_cert.py

# Then run with HTTPS
python run.py --https
```

**Requirements:**
- OpenSSL must be installed on your system
- **macOS**: `brew install openssl`
- **Ubuntu/Debian**: `sudo apt install openssl`
- **Windows**: Download from [OpenSSL website](https://slproweb.com/products/Win32OpenSSL.html)

## Development Workflow

### Backend Development

```bash
cd knowledge_transfer_tool/backend

# Activate virtual environment
source venv/bin/activate  # or .\venv\Scripts\activate on Windows

# Run backend only (for API development)
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### Frontend Development

```bash
cd knowledge_transfer_tool/frontend

# Start development server
npm start
```

The React development server runs on `http://localhost:3000` and proxies API calls to the backend.

### Building for Production

```bash
# From frontend directory
./build.sh

# Or manually:
npm run build
```

## Project Structure

```
Know-Transfer/
├── run.py                          # Main application launcher
├── knowledge_transfer_tool/
│   ├── backend/                    # FastAPI backend
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── database.py             # Database configuration
│   │   ├── models/                 # SQLAlchemy models
│   │   ├── routers/                # API route handlers
│   │   ├── schemas/                # Pydantic schemas
│   │   ├── services/               # Business logic services
│   │   ├── static/                 # Built frontend files (auto-generated)
│   │   └── requirements.txt        # Python dependencies
│   └── frontend/                   # React frontend
│       ├── src/
│       │   ├── components/         # React components
│       │   ├── styles/             # CSS stylesheets
│       │   └── lib/                # Utility functions
│       ├── public/                 # Static assets
│       ├── package.json            # Node.js dependencies
│       └── build.sh                # Frontend build script
└── README.md                       # This file
```

## API Documentation

Once the application is running, visit:
- **Interactive API Docs**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## Key Dependencies

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: Python SQL toolkit and ORM
- **LangChain**: Framework for developing LLM applications
- **ChromaDB**: Vector database for embeddings
- **OpenAI**: AI model integration
- **Uvicorn**: ASGI server for FastAPI

### Frontend
- **React**: JavaScript library for building user interfaces
- **Tailwind CSS**: Utility-first CSS framework
- **shadcn/ui**: High-quality React components
- **Mermaid**: Diagramming and charting library
- **React Router**: Client-side routing

## Troubleshooting

### Common Issues

#### 1. Port Already in Use
If port 8080 is already in use, you can change it in `run.py`:
```python
# Change the port number in run.py
["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8081"]
```

#### 2. OpenAI API Key Issues
- Ensure your API key is valid and has sufficient credits
- Check that the `.env` file is in the correct location (`knowledge_transfer_tool/.env`)
- Verify no extra spaces or quotes around the API key

#### 3. Build Script Permission Denied (macOS/Linux)
```bash
chmod +x knowledge_transfer_tool/frontend/build.sh
```

#### 4. Python Virtual Environment Issues
```bash
# Ensure you're in the correct directory
cd knowledge_transfer_tool/backend

# Create fresh virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 5. Node.js Module Issues
```bash
# Clear npm cache and reinstall
cd knowledge_transfer_tool/frontend
rm -rf node_modules package-lock.json
npm install
```

### Windows-Specific Notes

- Use `.\venv\Scripts\activate` instead of `source venv/bin/activate`
- The build script (`build.sh`) requires WSL, Git Bash, or similar Unix-like environment
- Alternatively, run the build commands manually:
  ```cmd
  cd knowledge_transfer_tool\frontend
  npm run build
  xcopy /E /I build ..\backend\static
  ```