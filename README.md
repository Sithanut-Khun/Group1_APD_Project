# Group 1 APD Project - Pose Estimation System

This project is a full-stack application featuring a FastAPI backend with YOLOv8 pose estimation integration and a vanilla JavaScript frontend. It includes database management using PostgreSQL.

## 📂 Project Structure

```text
GROUP1_APD_PROJECT/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── models/
│   │   │   └── yolov8n-pose.pt      # YOLO Model Weights
│   │   ├── routers/
│   │   │   ├── history.py
│   │   │   └── pose.py
│   │   ├── __init__.py
│   │   ├── crud.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py                # SQLAlchemy Models
│   │   └── schemas.py               # Pydantic Schemas
│   ├── ml_research/                 # Notebooks & Training scripts
│   ├── uploads/                     # Storage for processed images
│   ├── .dockerignore
│   ├── Dockerfile
│   └── requirements.txt
├── docs/
├── frontend/
│   ├── assets/
│   ├── css/
│   ├── js/
│   │   ├── config.js
│   │   ├── main.js
│   │   └── metrics.js
│   └── frontend_index.html
├── nginx/
├── .env                             # Environment Variables (Create this)
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## ⚙️ Configuration
Create a .env file in the root directory of the project. This file handles your database connection and application settings.

```bash
# .env file content

# Database Configuration
DB_HOST=localhost       # Use 'db' if running with Docker, 'localhost' if running manually
DB_PORT=5432
DB_USER=your_db_username
DB_PASSWORD=your_pass
DB_NAME=your_db_name
```

--- 

Note regarding DB_HOST:

- Docker: Set DB_HOST=db (matches the service name in docker-compose).

- Manual Run: Set DB_HOST=localhost.

---

## 🚀 Method 1: Running with Docker (Recommended)
This method spins up the Backend, Database, and Frontend (via Nginx) automatically.

1. Ensure Docker Desktop is running.

2. Modify .env for Docker: Change DB_HOST=localhost to DB_HOST=db.

3. Build and Run: Open your terminal in the root folder and run:

```bash
docker-compose up --build
```

4. Access the Application:

- Frontend: http://localhost:80 (or the port defined in docker-compose)

- Backend API Docs: http://localhost:8000/docs

---

## 🛠 Method 2: Running Services Separately (Manual)
Use this method for local development and debugging.

### 1. Database Setup
Ensure you have PostgreSQL installed locally.

Open pgAdmin or your terminal.

Create a database with the name specified in your .env (e.g., Test_db).

### 2. Backend Setup

1. Navigate to the backend folder:

```bash
cd backend
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run Server

```bash
uvicorn app.main:app --reload

```
The backend is now running at http://127.0.0.1:8000.


### 3. Frontend Setup
Since the frontend is HTML/JS, you cannot simply double-click the HTML file due to CORS policies. You must serve it.

Option A: VS Code Live Server (Easiest)

1. Open frontend/frontend_index.html in VS Code.

2. Right-click and select "Open with Live Server".