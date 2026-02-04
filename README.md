🌍 Smart Travel Planner
Smart Travel Planner is a full-stack web application that helps users plan trips, manage itineraries, and securely upload travel documents. The application is built with Flask, MySQL, and AWS S3, following best practices for authentication, data isolation, and cloud-based file storage.

🚀 Features
    -User authentication (Register / Login / Logout)
    -Secure password hashing
    -Create, edit, and delete trips
    -Add and manage daily itineraries
    -Upload and delete travel files (stored in AWS S3)
    -User-specific data isolation (users only see their own trips)
    -Flash messages for better user experience

🛠️ Tech Stack

Backend
    -Python
    -Flask
    -Flask-SQLAlchemy
    -Werkzeug (password hashing)

Database
    -MySQL (AWS RDS)
    -PyMySQL

Cloud Services
    -AWS S3 (file storage)
    -AWS EC2 (application hosting)
    -AWS RDS (database)

Frontend
    -HTML
    -Jinja2 Templates
    -CSS


📂 Project Structure
├── app.py              # Main Flask application
├── models.py           # Database models
├── templates/          # Jinja2 HTML templates
├── static/             # CSS and static assets
├── requirements.txt    # Python dependencies
├── .gitignore
└── README.md

🔐 Authentication & Security
    -Passwords are hashed using Werkzeug
    -User sessions are managed with Flask sessions
    -Protected routes prevent unauthorized access
    -Environment variables are used for secrets and credentials


📁 File Upload Workflow
    -User uploads a file using a form (multipart/form-data)
    -Flask receives the file and validates it
    -File is uploaded to AWS S3 using Boto3
    -File metadata is stored in the database
    -Files can be safely deleted from both S3 and the database
    -This approach avoids storing large files on the server and improves scalability.


🗄️ Database Models
    -User – stores account information
    -Trip – stores trip details linked to a user
    -Itinerary – stores daily plans for a trip
    -File – stores metadata for uploaded documents
    -Relationships are enforced using foreign keys to ensure data integrity.


▶️ Running the Application Locally
    -git clone https://github.com/tanjilamumu/Travel-Planner-Capstone-Project.git
    -cd smart-travel-planner
    -python -m venv venv
    -venv\Scripts\activate
    -pip install -r requirements.txt
    -python app.py

Then open 
    -http://127.0.0.1:5000

☁️ Deployment
    -Application hosted on AWS EC2
    -Database hosted on AWS RDS (MySQL)
    -Files stored in AWS S3
    -Environment variables used for production configuration


🚧 Future Enhancements
    -REST API with JWT authentication
    -Trip sharing and collaboration
    -File preview and download permissions
    -UI/UX improvements
    -Automated testing


👩‍💻 Author
    Tanjila Khatun Mumu
    Software Developer
    Capstone project demonstrating full-stack development, cloud integration, and scalable application design.
    
    
