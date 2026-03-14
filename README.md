# JustChatting  💬

A modern, full-featured, real-time chat application built with Django and WebSocket (Django Channels).

## ✨ Features

- **Real-Time Messaging**: Built using Django Channels and WebSockets for sub-second message delivery.
- **Modern UI/UX**: Responsive, mobile-first design inspired by modern messaging apps (WhatsApp/Telegram).
- **Message Status Indicators**: Real-time read receipts (Single tick for sent, double ticks for delivered/read).
- **Message Actions**: 
  - WhatsApp-style 3-dot dropdown menu located seamlessly inside the message bubble.
  - Edit sent messages (shows an *edited* tag).
  - Soft-delete messages (turns into a *✨ This message was deleted* ghost bubble).
- **Single-Session Enforcement**: Built-in security to prevent concurrent logins. If an account is already active on another device, subsequent login attempts are explicitly blocked.
- **Typing Indicators & Online Status**: Real-time updates on who is currently online.
- **Unread Badge Counters**: Keeps track of unread messages per conversation.
- **Advanced Integrations** (Optional/Configurable):
  - **Facial Login**: Biometric authentication using `face_recognition`.
  - **AI Assistant**: Integration with `google.generativeai` for advanced querying.

## 🚀 Tech Stack

- **Backend**: Python, Django 5.x
- **Real-Time Server**: ASGI (Daphne), WebSockets, Django Channels
- **Database**: SQLite (Default) / PostgreSQL ready
- **Frontend**: HTML5, Vanilla CSS3 (Custom Glass-morphism Design), Vanilla JavaScript
- **Broker**: Redis (used for Channels layer)

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10+
- Redis Server (Must be running for WebSockets to work)

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/Bimalv01/justchatting.git
   cd justchatting
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: If using optional features like AI or Facial Login, you may also need to install `face_recognition`, `google-generativeai`, `scikit-learn`, and `nltk`)*

4. **Run Database Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Start the Redis Server**
   Ensure your local Redis server is running (usually port 6379).
   ```bash
   redis-server
   ```

6. **Run the Development Server**
   Since this uses ASGI/Channels, Django will automatically use Daphne when running the server.
   ```bash
   python manage.py runserver
   ```

7. **Access the App**
   Open your browser and navigate to `http://127.0.0.1:8000/`.

## 🔒 Security Enhancements
- **CSRF Protection**: Comprehensive Cross-Site Request Forgery handling. Expired CSRF tokens gracefully redirect the user back to the login page instead of displaying ugly 403 errors.
- **WebSocket Auth**: Unauthorized connections are rejected at the ASGI layer during the handshake.
- **Concurrent Session Blocking**: Uses custom middleware (`SingleSessionMiddleware`) and database-backed session validation to ensure one user equals one session.

## 📄 License
This project is open-source and available under the [MIT License](LICENSE). 
