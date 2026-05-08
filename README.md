# Django Realtime Chat

A full-featured real-time chat application built with Django, Django Channels, and WebSockets. Supports public rooms, private groups, direct messages, file sharing, and real-time messaging with typing indicators and online status.

---

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Running the Project](#running-the-project)
7. [Usage Guide](#usage-guide)
8. [API Endpoints](#api-endpoints)
9. [WebSocket Events](#websocket-events)
10. [Database Models](#database-models)
11. [Demo Data](#demo-data)
12. [Environment Variables](#environment-variables)
13. [Troubleshooting](#troubleshooting)
14. [License](#license)

---

## Features

### Authentication and User Management
- User registration and login
- Custom user model with avatar, bio, online status, and last seen
- Session-based authentication with Django's authentication system

### Chat Rooms
- **Public Rooms**: Anyone can join and participate
- **Private Groups**: Admin-controlled groups with join requests
- **Direct Messages (DM)**: Private one-on-one conversations between users

### Messaging Features
- Real-time messaging via WebSockets
- Message reply functionality
- Edit and delete own messages
- File and image sharing (drag-and-drop upload)
- Typing indicators
- Online member count per room
- Unread message count tracking

### Room Management
- Create public and private rooms
- Room admin system with full control
- Invite users to private rooms
- Join request system for private rooms
- Leave room functionality
- Room settings (edit name, description, avatar, delete)

### Additional Features
- User profile with group memberships
- Online users list
- Recent rooms sidebar
- Message pagination (load older messages)
- Read receipts

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | Django 6.0 |
| Real-time Communication | Django Channels 4.x |
| WebSocket Server | Daphne |
| Message Broker | Redis |
| Database | SQLite3 (default) |
| Frontend | HTML, CSS, JavaScript |
| Styling | Custom CSS |
| File Storage | Django Media files |

---

## Project Structure

```
Django Realtime Chat/
├── chatproject/          # Django project configuration
│   ├── settings.py       # Project settings
│   ├── urls.py          # Main URL configuration
│   ├── asgi.py          # ASGI configuration for channels
│   └── wsgi.py          # WSGI configuration
├── chat/                 # Chat application
│   ├── models.py        # Database models (Room, Message, JoinRequest, Invitation)
│   ├── views.py         # View functions
│   ├── urls.py          # Chat URL patterns
│   ├── consumers.py     # WebSocket consumer
│   ├── routing.py       # WebSocket URL routing
│   ├── admin.py         # Django admin configuration
│   └── migrations/      # Database migrations
├── accounts/            # User authentication app
│   ├── models.py        # Custom User model
│   ├── views.py         # Authentication views
│   ├── forms.py         # Authentication forms
│   ├── urls.py          # Auth URL patterns
│   └── migrations/      # Database migrations
├── templates/           # HTML templates
│   ├── chat/           # Chat templates
│   └── accounts/       # Auth templates
├── static/             # CSS and JavaScript files
├── media/              # User-uploaded files
├── manage.py          # Django management script
├── requirements.txt   # Python dependencies
├── docker-compose.yml # Docker configuration (optional)
├── .env.example       # Environment variables template
└── README.md          # This file
```

---

## Installation

### Prerequisites

- Python 3.8 or higher
- Redis server (for WebSocket channel layer)
- Node.js (optional, for development)

### Clone the Repository

```bash
git clone <repository-url>
cd "Django Realtime Chat"
```

### Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Install Redis

#### Windows
Download and install Redis from [redis.io](https://redis.io/download) or use Windows Subsystem for Linux (WSL).

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install redis-server
```

#### macOS
```bash
brew install redis
brew services start redis
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

Or copy from `.env.example`:

```bash
copy .env.example .env
```

### Channel Layer Configuration

The project uses Redis as the channel layer. Ensure Redis is running on `127.0.0.1:6379` (default).

In `chatproject/settings.py`:
```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}
```

### Database Configuration

The project uses SQLite3 by default. To use PostgreSQL or MySQL, update `DATABASES` in `settings.py`.

---

## Running the Project

### Step 1: Start Redis

```bash
# Windows (if Redis is installed)
redis-server

# Linux/Mac
redis-server
```

### Step 2: Run Migrations

```bash
python manage.py migrate
```

### Step 3: Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### Step 4: Start Development Server

```bash
python manage.py runserver
```

For WebSocket support, use Daphne:

```bash
daphne -b 127.0.0.1 -p 8000 chatproject.asgi:application
```

Or use the included `start.bat` (Windows):

```bash
start.bat
```

### Step 5: Access the Application

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## Usage Guide

### Registration and Login

1. Visit the homepage
2. Click "Sign Up" to create an account
3. After registration, you'll be redirected to the chat interface
4. Already have an account? Click "Login"

### Joining Public Rooms

1. On the homepage, you'll see a list of public rooms
2. Click on any room to join and start chatting

### Creating a New Room

1. Click "Create Room" button
2. Enter room name and optional description
3. Choose "Public" or "Private"
4. For private rooms, you become the room admin

### Direct Messages (DM)

1. Click on any user in the sidebar
2. A DM room will be created automatically
3. Start chatting privately

### Joining Private Groups

1. Private groups appear in the "Discover" section
2. Click "Request to Join"
3. Wait for the admin to approve your request

### Room Admin Features

As a private room admin, you can:
- View and manage join requests
- Invite users to your room
- Remove members
- Edit room details and avatar
- Delete the room

### Message Features

- **Reply**: Hover over a message and click the reply icon
- **Edit**: Click on your own message and select "Edit"
- **Delete**: Click on your own message and select "Delete"
- **File Upload**: Drag and drop files or use the upload button

---

## API Endpoints

### Authentication
| URL | Method | Description |
|-----|--------|-------------|
| `/accounts/login/` | GET, POST | User login |
| `/accounts/signup/` | GET, POST | User registration |
| `/accounts/logout/` | GET, POST | User logout |

### Chat
| URL | Method | Description |
|-----|--------|-------------|
| `/` | GET | Home/Dashboard |
| `/room/<slug>/` | GET | Chat room |
| `/dm/<username>/` | GET | Direct message room |
| `/create-public-room/` | POST | Create public room |
| `/create-private-room/` | POST | Create private room |
| `/request-join/<slug>/` | POST | Request to join private room |
| `/cancel-join-request/<slug>/` | POST | Cancel join request |
| `/handle-join-request/<id>/<action>/` | POST | Approve/Reject join request |
| `/invite-to-room/<slug>/` | POST | Invite user to room |
| `/handle-invitation/<id>/<action>/` | POST | Accept/Decline invitation |
| `/remove-member/<slug>/` | POST | Remove member from room |
| `/leave-group/<slug>/` | POST | Leave private group |
| `/upload-file/<slug>/` | POST | Upload file to room |
| `/user-profile/<username>/` | GET | Get user profile |
| `/room-settings/<slug>/` | GET, POST | Room settings |
| `/load-older-messages/<slug>/` | GET | Pagination for messages |

---

## WebSocket Events

### Connection
```
ws://127.0.0.1:8000/ws/chat/<room_slug>/
```

### Client → Server Events

| Event | Payload | Description |
|-------|---------|-------------|
| message | `{"message": "text", "reply_to_id": null}` | Send text message |
| typing | `{"type": "typing"}` | User is typing |
| stop_typing | `{"type": "stop_typing"}` | User stopped typing |
| mark_as_read | `{"type": "mark_as_read", "message_id": 123}` | Mark message as read |
| file_message | `{"type": "file_message", "file_url": "...", "file_type": "image", "file_name": "..."}` | Send file |
| delete_message | `{"type": "delete_message", "message_id": 123}` | Delete message |
| edit_message | `{"type": "edit_message", "message_id": 123, "content": "new text"}` | Edit message |

### Server → Client Events

| Event | Payload | Description |
|-------|---------|-------------|
| chat_message | `{type, message, username, timestamp, message_id, file_url, file_type, reply_to}` | New message |
| typing | `{type: "typing", username}` | User typing |
| stop_typing | `{type: "stop_typing", username}` | User stopped typing |
| user_join | `{type: "user_join", username}` | User joined room |
| online_count | `{type: "online_count", count}` | Online members count |
| message_read | `{type: "message_read", message_id, username}` | Message read |
| message_deleted | `{type: "message_deleted", message_id}` | Message deleted |
| message_edited | `{type: "message_edited", message_id, content}` | Message edited |

---

## Database Models

### User (accounts.User)
| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| username | CharField | Unique username |
| email | EmailField | User email |
| password | CharField | Hashed password |
| avatar | ImageField | User avatar (optional) |
| bio | TextField | User bio (optional) |
| is_online | BooleanField | Online status |
| last_seen | DateTimeField | Last active timestamp |

### Room (chat.Room)
| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| name | CharField | Room name |
| slug | SlugField | URL-friendly identifier |
| description | TextField | Room description |
| members | ManyToManyField | Room members |
| admin | ForeignKey | Room admin |
| is_private | BooleanField | Public/Private flag |
| avatar | ImageField | Room avatar (optional) |
| created_at | DateTimeField | Creation timestamp |
| updated_at | DateTimeField | Last update timestamp |

### Message (chat.Message)
| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| room | ForeignKey | Related room |
| author | ForeignKey | Message author |
| content | TextField | Message text |
| timestamp | DateTimeField | Creation timestamp |
| is_read | BooleanField | Read status |
| is_edited | BooleanField | Edited flag |
| reply_to | ForeignKey | Reply target (optional) |
| file | FileField | Attached file (optional) |
| file_type | CharField | File type (image/file) |

### JoinRequest (chat.JoinRequest)
| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| room | ForeignKey | Target room |
| user | ForeignKey | Requesting user |
| status | CharField | pending/approved/rejected |
| created_at | DateTimeField | Request timestamp |

### Invitation (chat.Invitation)
| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| room | ForeignKey | Target room |
| invited_by | ForeignKey | Inviter |
| invited_user | ForeignKey | Invitee |
| status | CharField | pending/accepted/declined |
| created_at | DateTimeField | Invitation timestamp |

---

## Demo Data

To create demo data with sample rooms and messages:

```bash
python manage.py create_demo_data
```

This command creates:
- Sample public and private rooms
- Demo messages in rooms
- Test users (if any)

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | django-insecure-fallback-key |
| `DEBUG` | Debug mode | True |
| `ALLOWED_HOSTS` | Allowed hosts (comma-separated) | localhost,127.0.0.1 |

---

## Troubleshooting

### WebSocket Connection Issues
- Ensure Redis is running: `redis-cli ping` should return PONG
- Check ALLOWED_HOSTS includes your domain
- Verify CHANNEL_LAYERS configuration in settings.py

### File Upload Issues
- Ensure MEDIA_ROOT directory exists and is writable
- Check file size limits in settings (default: 2.5MB)
- Verify Pillow is installed for image handling

### Database Issues
- Run migrations: `python manage.py migrate`
- Check database file permissions
- For SQLite, ensure db.sqlite3 exists

### Authentication Issues
- Check LOGIN_URL and LOGIN_REDIRECT_URL settings
- Ensure AUTH_USER_MODEL points to accounts.User
- Verify session middleware is configured

---

## License

This project is open-source and available under the MIT License.

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## Acknowledgments

- Django Framework
- Django Channels
- Channels Redis
- Daphne