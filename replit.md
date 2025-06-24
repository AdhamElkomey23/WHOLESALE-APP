# Wholesale Management System

## Overview

This is a comprehensive wholesale clothing management system built with Flask. The system manages multiple clothing brands (URBRAND, SURVACCI, and AZIZ) with features for order management, inventory tracking, client management, worker attendance, and expense tracking. It's designed to handle the complex requirements of a wholesale clothing business with different storage systems for different brands.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with support for PostgreSQL and SQLite
- **Authentication**: Flask-Login for user session management
- **Forms**: Flask-WTF with WTForms for form handling and CSRF protection
- **PDF Generation**: ReportLab for invoice generation
- **Server**: Gunicorn WSGI server for production deployment

### Frontend Architecture
- **Template Engine**: Jinja2 (Flask's default)
- **CSS Framework**: Bootstrap 5.3.0
- **Icons**: Font Awesome 6.0
- **Charts**: Chart.js for data visualization
- **Fonts**: Google Fonts (Inter)
- **JavaScript**: Vanilla JavaScript with modern ES6+ features

### Database Schema
- **Users**: Authentication and user management
- **Clients**: Customer information and contact details
- **ProductType**: Product catalog with colors, sizes, and brand groups
- **Orders**: Order management with client relationships
- **OrderItems**: Individual items within orders
- **ColorSizeInventory**: Detailed inventory tracking by color and size
- **Workers**: Employee management
- **WorkerAttendance**: Time tracking and salary calculations
- **Expenses**: Business expense tracking by brand

## Key Components

### 1. Multi-Brand Management
- **URBRAND & SURVACCI**: Shared storage system and inventory
- **AZIZ**: Independent storage and inventory management
- Brand-specific filtering across all modules

### 2. Order Management System
- Complete order lifecycle from creation to fulfillment
- Client integration with automatic client creation
- Multi-product orders with color and size selection
- PDF invoice generation
- Order status tracking and payment management

### 3. Inventory Management
- Color and size-specific inventory tracking
- Separate storage types for different brand groups
- Real-time stock level monitoring
- Inventory movement tracking

### 4. Client Relationship Management
- Comprehensive client database
- Order history tracking
- Contact information management
- Client-specific analytics

### 5. Worker Management & Attendance
- Employee database with salary information
- Daily attendance tracking
- Piece-rate payment calculations
- Department-wise organization
- Attendance reporting and analytics

### 6. Expense Tracking
- Brand-specific expense categorization
- Monthly and yearly expense reports
- Expense type classification
- Profit/loss calculations

### 7. Analytics Dashboard
- Brand-specific performance metrics
- Sales trends and analytics
- Revenue, cost, and profit tracking
- Visual charts and graphs

## Data Flow

### Order Creation Flow
1. User selects/creates client information
2. System validates client data and creates new client if needed
3. User selects products with specific colors and sizes
4. System calculates totals and creates order record
5. Inventory levels are automatically updated
6. PDF invoice is generated and available for download

### Inventory Management Flow
1. Products are created with available colors and sizes
2. Initial inventory is set for each color/size combination
3. Orders automatically deduct from inventory
4. Stock movements are tracked for audit purposes
5. Low stock alerts are generated when thresholds are reached

### Expense Tracking Flow
1. Expenses are categorized by brand and type
2. Monthly totals are calculated automatically
3. Profit/loss calculations include both revenue and expenses
4. Reports are generated for financial analysis

## External Dependencies

### Frontend Dependencies
- Bootstrap 5.3.0 (CSS framework)
- Font Awesome 6.0 (Icon library)
- Chart.js (Data visualization)
- Google Fonts (Typography)

### Backend Dependencies
- Flask 3.1.1 (Web framework)
- Flask-SQLAlchemy 3.1.1 (Database ORM)
- Flask-Login 0.6.3 (Authentication)
- Flask-WTF 1.2.2 (Form handling)
- WTForms 3.2.1 (Form validation)
- ReportLab 4.4.1 (PDF generation)
- Gunicorn 23.0.0 (WSGI server)
- psycopg2-binary 2.9.10 (PostgreSQL adapter)
- email-validator 2.2.0 (Email validation)

### System Dependencies
- Python 3.11+
- PostgreSQL (production)
- SQLite (development)
- Node.js 20 (for frontend tooling)

## Deployment Strategy

### Development Environment
- Uses SQLite database for local development
- Flask development server with hot reload
- Debug mode enabled for detailed error reporting

### Production Environment
- PostgreSQL database for data persistence
- Gunicorn WSGI server for handling HTTP requests
- Automatic scaling deployment target
- Environment-based configuration management
- SSL/TLS termination at proxy level

### Configuration Management
- Environment variables for sensitive configuration
- Database URL configuration for different environments
- Session secret management
- Connection pooling and health checks

### Database Management
- SQLAlchemy migrations for schema changes
- Connection pooling with automatic reconnection
- Query optimization for performance
- Backup and recovery procedures

## Changelog
- June 24, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.