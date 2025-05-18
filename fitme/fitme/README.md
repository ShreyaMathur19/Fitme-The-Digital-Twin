# FitMe - Fitness Application

A Flask-based web application for fitness tracking and management.

## Setup Instructions

1. Install MySQL on your system if not already installed.

2. Create a MySQL database:
```sql
CREATE DATABASE fitme_db;
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Configure the database connection:
   - Open `app.py`
   - Update the `SQLALCHEMY_DATABASE_URI` with your MySQL credentials:
   ```python
   app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://username:password@localhost/fitme_db'
   ```
   - Update the `SECRET_KEY` with a secure random string

5. Run the application:
```bash
python app.py
```

6. Access the application:
   - Open your web browser
   - Navigate to `http://localhost:5000`
   - Register a new account or login with existing credentials

## Features

- User authentication (login/register)
- Dashboard
- Chatbot interface
- Calendar functionality
- Secure password storage

## Project Structure

```
fitme/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── templates/         # HTML templates
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── chatbot.html
│   └── calendar.html
└── static/           # Static files (CSS, JS, images)
``` 