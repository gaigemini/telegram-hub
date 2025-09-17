Telegram API Hub - Usage Guide
==============================

🚀 Setup Instructions
---------------------

### 1\. Environment Setup

1.  **Clone or download the project files**
    
2.  pip install -r requirements.txt
    
3.  **Create environment file:**
    
    *   Copy .env.example to .env
        
    *   Fill in your Telegram API credentials and database URL
        
4.  **Get Telegram API credentials:**
    
    *   Go to https://my.telegram.org/apps
        
    *   Create a new application
        
    *   Copy the API\_ID and API\_HASH
        
5.  **Setup Database:**
    
    *   For production: Use PostgreSQL
        
    *   For development: You can use SQLite by setting DATABASE\_URL=sqlite:///./telegram\_hub.db
        

### 2\. Running the Service

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   # Using the startup script (recommended)  python run.py  # Or directly with uvicorn  uvicorn main:app --host 0.0.0.0 --port 8000 --reload   `

The service will be available at: http://localhost:8000

📚 API Endpoints
----------------

### Health Check Endpoints

#### Health Status

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   GET /health   `

**Response:**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   {      "status": "healthy",      "active_sessions": 2  }   `

### Authentication Endpoints

#### 1\. Start Login Process

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   POST /login/start  Content-Type: application/json  {      "session_id": "user123",      "phone_number": "+1234567890"  }   `

**Response:**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   {      "status": "success",      "message": "Verification code sent to your phone",      "phone_code_hash": "hash_string_here"  }   `

#### 2\. Submit Verification Code

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   POST /login/code  Content-Type: application/json  {      "session_id": "user123",      "phone_code": "12345",      "phone_code_hash": "hash_from_previous_step"  }   `

**Response (Success):**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   {      "status": "success",      "message": "Login successful",      "user": {          "id": 123456789,          "first_name": "John",          "last_name": "Doe",          "username": "johndoe",          "phone": "+1234567890"      }  }   `

**Response (2FA Required):**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   {      "status": "2fa_required",      "message": "Two-factor authentication is enabled. Please provide your password"  }   `

#### 3\. Submit 2FA Password

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   POST /login/password  Content-Type: application/json  {      "session_id": "user123",      "password": "your_2fa_password"  }   `

#### 4\. Logout

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   POST /logout  Content-Type: application/json  {      "session_id": "user123"  }   `

**Response:**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   {      "status": "success",      "message": "Logged out successfully"  }   `

### Session Management Endpoints

#### 1\. List All Sessions

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   GET /sessions   `

**Response:**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   {      "status": "success",      "total_sessions": 2,      "sessions": [          {              "session_id": "user123",              "is_connected": true,              "is_authenticated": true,              "user_info": {                  "id": 123456789,                  "first_name": "John",                  "last_name": "Doe",                  "username": "johndoe",                  "phone": "+1234567890"              },              "in_login_cache": false          },          {              "session_id": "user456",              "is_connected": false,              "is_authenticated": false,              "user_info": null,              "in_login_cache": true          }      ]  }   `

#### 2\. Get Specific Session Status

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   GET /session/{session_id}/status   `

**Response:**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   {      "session_id": "user123",      "is_authenticated": true,      "is_active": true,      "is_connected": true,      "user_info": {          "id": 123456789,          "first_name": "John",          "last_name": "Doe",          "username": "johndoe",          "phone": "+1234567890"      },      "in_login_cache": false  }   `

#### 3\. Destroy Session (Complete Cleanup)

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   DELETE /session/{session_id}   `

**Response:**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   {      "status": "success",      "message": "Session user123 destroyed completely"  }   `

#### 4\. Reconnect Session

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   POST /session/{session_id}/reconnect   `

**Response:**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   {      "status": "success",      "message": "Session reconnected successfully"  }   `

### Messaging Endpoints

#### Send Message

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   POST /message/send  Content-Type: application/json  {      "session_id": "user123",      "chat_id": "@username",      "message": "Hello, World!"  }   `

**Response:**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   {      "status": "success",      "message": "Message sent successfully"  }   `

🔧 Usage Examples
-----------------

### Python Example

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   import requests  BASE_URL = "http://localhost:8000"  # 1. Start login  response = requests.post(f"{BASE_URL}/login/start", json={      "session_id": "my_session",      "phone_number": "+1234567890"  })  data = response.json()  phone_code_hash = data["phone_code_hash"]  # 2. Submit code (you'll need to get this from your phone)  code = input("Enter verification code: ")  response = requests.post(f"{BASE_URL}/login/code", json={      "session_id": "my_session",      "phone_code": code,      "phone_code_hash": phone_code_hash  })  # 3. Send message  requests.post(f"{BASE_URL}/message/send", json={      "session_id": "my_session",      "chat_id": "@someone",      "message": "Hello from API!"  })  # 4. List sessions  response = requests.get(f"{BASE_URL}/sessions")  print(response.json())  # 5. Logout  requests.post(f"{BASE_URL}/logout", json={      "session_id": "my_session"  })   `

### cURL Examples

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   # Health check  curl -X GET "http://localhost:8000/health"  # Start login  curl -X POST "http://localhost:8000/login/start" \    -H "Content-Type: application/json" \    -d '{"session_id": "test123", "phone_number": "+1234567890"}'  # List all sessions  curl -X GET "http://localhost:8000/sessions"  # Get session status  curl -X GET "http://localhost:8000/session/test123/status"  # Send message  curl -X POST "http://localhost:8000/message/send" \    -H "Content-Type: application/json" \    -d '{"session_id": "test123", "chat_id": "@username", "message": "Hello!"}'  # Destroy session  curl -X DELETE "http://localhost:8000/session/test123"   `

### Administrative Endpoints

#### 1\. Manual Session Restoration

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   POST /admin/restore-sessions   `

**Response:**

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   {      "status": "success",      "message": "Restored 3 sessions from database",      "restored_count": 3  }   `

🔄 Session Persistence
----------------------

**Key Feature**: Sessions persist across application restarts!

When you restart the API Hub:

1.  ✅ All authenticated sessions are automatically restored from the database
    
2.  ✅ Users remain logged in and can continue receiving messages
    
3.  ✅ No need to re-authenticate unless the session expires on Telegram's side
    

### How it works:

*   Session data (auth keys, user info) is stored in PostgreSQL/SQLite
    
*   On startup, the service automatically loads all valid sessions
    
*   Each restored session reconnects to Telegram and verifies authentication
    
*   Invalid or expired sessions are automatically cleaned up
    

### Monitoring Session Restoration:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   # Check server logs during startup to see restoration status  # You'll see messages like:  # 🔄 Restoring sessions from database...  # ✅ Session user123 restored successfully - User: John  # ✅ Session restoration complete: 2 sessions restored   `

Use the included test script:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   python test_api.py   `

📝 Notes
--------

*   **Session IDs**: Use unique identifiers for each user/client
    
*   **Phone Numbers**: Must include country code (e.g., +1234567890)
    
*   **Chat IDs**: Can be usernames (@username), phone numbers, or numeric IDs
    
*   **Message Detection**: The service automatically logs incoming messages for all authenticated sessions
    
*   **Database**: Session data persists between restarts
    
*   **Connection Management**: The service handles reconnections automatically