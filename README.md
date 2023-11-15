# EduMentor: An AI-Enhanced Tutoring System

**Description:**
EduMentor utilizes advanced RAG (Retrieval-Augmented Generation) to provide comprehensive answers to complex educational queries. This AI-driven approach combines extensive knowledge retrieval with dynamic response generation, enhancing students' understanding and promoting interactive learning.

**Usage:**
1. Enter your OpenAI API Key.
2. Upload relevant files.
3. Explore the chat history and ask questions.
4. Download chat history in PDF or HTML format.

**Project Structure:**
- `api_handler.py`: Handles API interactions.
- `app.py`: Streamlit app for EduMentor.
- `chat_gen.py`: Generates chat history.
- `file_upload.py`: Manages file uploads.
- `pdfs/`: Directory for uploaded PDF files.
- `requirements.txt`: List of dependencies.

**Dependencies:**
- streamlit
- openai
- fpdf2
- jinja2
- markdown2
- pdfkit
- wkhtmltopdf (for PDF conversion)

To run the app, provide your OpenAI API Key, upload files, and interact with EduMentor. You can download chat history in your preferred format (PDF or HTML) via the sidebar.

Enjoy using EduMentor for enriched educational experiences!