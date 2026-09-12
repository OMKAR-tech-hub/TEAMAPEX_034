# Farmer Trust Passport API

Portable Agricultural Economic Identity standard enabling farmers to leverage verified production and community participation for transparent credit access while retaining complete data ownership and control.

## Product Vision

Establish Farmer Trust Passport as the portable Agricultural Economic Identity standard enabling farmers to leverage verified production and community participation for transparent credit access while retaining complete data ownership and control.

## Target Audience

- **Primary Users**: Smallholder farmers and FPOs (Farmer Producer Organizations) seeking transparent credit access
- **Secondary Users**: Rural banks, NBFCs (Non-Banking Financial Companies), and cooperatives requiring verified borrower assessment and reduced information costs

## Core Features

- **Farmer Profile Management**: Create, read, update, and delete farmer profiles with agricultural data
- **Production Records**: Track and verify agricultural production history
- **Credit Applications**: Manage loan applications with transparent status tracking
- **Verification System**: Verify farmer identity, production records, and FPO membership

## Technology Stack

- **Backend Framework**: FastAPI (Python)
- **Database**: SQLAlchemy ORM (SQLite for development, PostgreSQL/MySQL for production)
- **Data Validation**: Pydantic
- **Architecture**: Modular Monolith with clear separation of concerns

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. **Clone the repository** (or navigate to the project directory)

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - On Linux/Mac:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

5. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` file and update the configuration values, especially:
   - `SECRET_KEY`: Use a strong random string for production
   - `DATABASE_URL`: Configure your database connection

## Running the Application

### Development Mode

Run the application with auto-reload enabled:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

### Production Mode

For production deployment:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the application is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Farmers
- `POST /api/v1/farmers/` - Create a new farmer profile
- `GET /api/v1/farmers/` - List all farmers (with pagination)
- `GET /api/v1/farmers/{farmer_id}` - Get a specific farmer
- `PUT /api/v1/farmers/{farmer_id}` - Update a farmer profile
- `DELETE /api/v1/farmers/{farmer_id}` - Delete a farmer profile

### Credit Applications
- `POST /api/v1/credit/` - Create a new credit application
- `GET /api/v1/credit/` - List credit applications (with filters)
- `GET /api/v1/credit/{application_id}` - Get a specific application
- `PUT /api/v1/credit/{application_id}` - Update application status
- `DELETE /api/v1/credit/{application_id}` - Delete an application

### Verifications
- `POST /api/v1/verification/` - Create a new verification request
- `GET /api/v1/verification/` - List verifications (with filters)
- `GET /api/v1/verification/{verification_id}` - Get a specific verification
- `PUT /api/v1/verification/{verification_id}` - Update verification status
- `DELETE /api/v1/verification/{verification_id}` - Delete a verification

## Database

The application uses SQLAlchemy ORM with support for multiple databases:

- **Development**: SQLite (default, no setup required)
- **Production**: PostgreSQL or MySQL (recommended)

### Database Models

- **Farmer**: Core farmer profile with agricultural data
- **ProductionRecord**: Historical production data
- **CreditApplication**: Loan application tracking
- **Verification**: Identity and data verification records

### Database Initialization

The database tables are automatically created on application startup. For SQLite, the database file will be created in the project root directory.

## Configuration

Key configuration options in `.env`:

- `DATABASE_URL`: Database connection string
- `SECRET_KEY`: Secret key for security features
- `ALLOWED_ORIGINS`: CORS allowed origins (comma-separated)
- `DEFAULT_PAGE_SIZE`: Default pagination size (default: 20)
- `MAX_PAGE_SIZE`: Maximum pagination size (default: 100)

## Architecture

The application follows a **Modular Monolith** architecture:

```
backend/
├── main.py              # Application entry point
├── config.py            # Configuration management
├── database.py          # Database setup and session management
├── models.py            # SQLAlchemy database models
├── schemas.py           # Pydantic schemas for validation
└── routers/             # API route handlers
    ├── farmers.py       # Farmer management endpoints
    ├── credit.py        # Credit application endpoints
    └── verification.py  # Verification endpoints
```

### Key Design Principles

- **Separation of Concerns**: Clear boundaries between routes, models, and schemas
- **Data Validation**: Pydantic schemas for request/response validation
- **Error Handling**: Comprehensive error handling with meaningful messages
- **Logging**: Structured logging for debugging and monitoring
- **Security**: Input validation, SQL injection prevention via ORM

## Development

### Code Structure

- **Models** (`models.py`): Database table definitions using SQLAlchemy
- **Schemas** (`schemas.py`): Request/response validation using Pydantic
- **Routers** (`routers/`): API endpoint implementations
- **Config** (`config.py`): Centralized configuration management

### Adding New Features

1. Define database model in `models.py`
2. Create Pydantic schemas in `schemas.py`
3. Implement API routes in `routers/`
4. Register router in `main.py`

## Security Considerations

- All passwords and secrets should be stored in environment variables
- Use strong random strings for `SECRET_KEY` in production
- Enable HTTPS in production deployments
- Implement rate limiting for production use
- Regular security updates for dependencies

## Deployment

For production deployment:

1. Use PostgreSQL or MySQL instead of SQLite
2. Set `DEBUG=False` in environment variables
3. Use a strong random `SECRET_KEY`
4. Configure proper CORS origins
5. Use a production ASGI server (uvicorn with workers)
6. Set up proper logging and monitoring
7. Implement backup strategies for the database

## Support

For issues, questions, or contributions, please refer to the project documentation or contact the development team.

## License

[Specify your license here]
