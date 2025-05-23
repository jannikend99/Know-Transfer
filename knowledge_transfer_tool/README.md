# Knowledge Transfer Tool - Prototype Setup

This guide provides instructions to set up and run the Knowledge Transfer Tool prototype.

## Prerequisites

*   **Python** (version 3.8 or higher recommended)
*   **Node.js** (version 16 or higher recommended) and **npm**
*   Access to a shell or terminal

## Setup Instructions

1.  **Clone the Repository (if applicable)**
    If you've received this as a set of files, ensure they are all within a main project directory (e.g., `knowledge_transfer_tool`).

2.  **Create the `.env` File:**
    In the root directory of the project (`knowledge_transfer_tool/`), create a file named `.env` and add the following content. Replace `your_openai_api_key` with your actual OpenAI API key if you plan to test AI features later (it's not strictly needed for the initial frontend display).

    ```env
    DATABASE_URL=sqlite:///./knowledge_transfer.db
    UPLOAD_DIRECTORY=./uploads
    VECTOR_STORE_PATH=./vector_store
    OPENAI_API_KEY=your_openai_api_key
    ```

3.  **Set Up Backend:**
    *   Navigate to the backend directory:
        ```bash
        cd backend
        ```
    *   **Create a Virtual Environment (recommended):**
        ```bash
        python -m venv venv
        ```
    *   **Activate the Virtual Environment:**
        *   On macOS/Linux:
            ```bash
            source venv/bin/activate
            ```
        *   On Windows:
            ```bash
            .\venv\Scripts\activate
            ```
    *   **Install Backend Dependencies:**
        ```bash
        pip install -r requirements.txt
        ```
    *   Navigate back to the project root:
        ```bash
        cd ..
        ```

4.  **Set Up Frontend:**
    *   Navigate to the frontend directory:
        ```bash
        cd frontend
        ```
    *   **Install Frontend Dependencies:**
        ```bash
        npm install
        ```
    *   Navigate back to the project root:
        ```bash
        cd ..
        ```

5.  **Make Build Script Executable (if not already):**
    The `run.py` script attempts to do this, but it's good to ensure manually if needed.
    *   On macOS/Linux:
        ```bash
        chmod +x frontend/build.sh
        ```
    *   On Windows, shell scripts might require WSL or Git Bash to run correctly. If `build.sh` doesn't run via `run.py`, you might need to execute its steps manually or adapt it to a `.bat` script. The `build.sh` script essentially runs `npm run build` in the `frontend` directory and then copies the contents of `frontend/build/` to `backend/static/`, and also copies CSS files from `frontend/src/styles/` to `backend/static/styles/`.

## Running the Application

1.  **Ensure you are in the project's root directory (`knowledge_transfer_tool/`).**
2.  **If you created a backend virtual environment, make sure it's activated.**
3.  **Run the `run.py` script:**
    ```bash
    python run.py
    ```
    This script will:
    *   Attempt to build the frontend (by executing `frontend/build.sh`).
    *   Start the FastAPI backend server.

4.  **Access the Application:**
    Open your web browser and go to: `http://localhost:8000`

You should see the basic header and a welcome message for the Home Page.

## Stopping the Application

*   Press `Ctrl+C` in the terminal where `run.py` is running.
*   If you used a virtual environment, you can deactivate it by typing `deactivate` in the terminal.

## Next Steps in Development
Refer to the `todo.txt` file for the ongoing development tasks. 