import streamlit as st
from streamlit import sidebar
import pdfkit
from openai import OpenAI
import api_handler
from api_handler import send_query_get_response
from chat_gen import generate_html
import io
from file_upload import upload_files_to_assistant, attach_files_to_assistant, check_and_upload_files
import subprocess
import os
from PIL import Image

logo=Image.open('logo.png')

# Title and Description
st.title('EduMentor : An AI-Enhanced Tutoring System')

# RAG function description
rag_description = """
EduMentor leverages the cutting-edge RAG (Retrieval-Augmented Generation) function to provide in-depth, contextually rich answers to complex educational queries. This AI-driven approach combines extensive knowledge retrieval with dynamic response generation, offering students a deeper, more nuanced understanding of subjects and fostering a more interactive, exploratory learning environment.
"""

# OpenAI API Key Input
api_key = st.text_input(label='Enter your OpenAI API Key', type='password')

if api_key:
    # If API key is entered, initialize the OpenAI client and proceed with app functionality
    client = OpenAI(api_key=api_key)
    assistant_id = 'asst_konaahsahZ0UhK82guGBvn6m'

    # RAG Description
    st.markdown(rag_description, unsafe_allow_html=True)

    # File Handling Section
    files_info = check_and_upload_files(client, assistant_id)
    
    st.markdown(f'Number of files uploaded in the assistant: :blue[{len(files_info)}]')
    st.divider()

    # Sidebar for Additional Features
    st.sidebar.header('EduMentor: AI-Tutor')
    st.sidebar.image(logo)
    st.sidebar.caption('Made by D')
    # Adding a button in the sidebar to delete all files from the assistant
    if st.sidebar.button('Delete All Files from Assistant'):
        # Retrieve all file IDs associated with the assistant
        assistant_files = client.beta.assistants.files.list(assistant_id=assistant_id)
        for file in assistant_files:
            file_id = file['id']
            client.beta.assistants.files.delete(assistant_id=assistant_id, file_id=file_id)
            st.sidebar.success(f'Deleted file: {file_id}')

    if st.sidebar.button('Generate Chat History'):
        html_data = generate_html(st.session_state.messages)
        st.sidebar.download_button(label="Download Chat History as HTML",
                                        data=html_data,
                                        file_name="chat_history.html",
                                        mime="text/html")


    # Main Chat Interface
    st.subheader('Chat History with Tutor')
    st.caption('You can choose to download the chat history in either PDF or HTML format using the options in the sidebar on the left.')
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("Welcome and ask a question to the AI tutor"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar='👨🏻‍🏫'):
            message_placeholder = st.empty()
            response = send_query_get_response(client,prompt,assistant_id)
            message_placeholder.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

else:
    # Prompt for API key if not entered
    st.warning("Please enter your OpenAI API Key to use EduMentor.")
