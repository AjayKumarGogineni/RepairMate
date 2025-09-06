import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import base64
import tempfile
import os
from typing import List, Dict, Any
import time

# Configure the page
st.set_page_config(
    page_title="RepairMate - AI Repair Assistant",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load configuration from secrets
def load_config():
    """Load configuration from Streamlit secrets"""
    try:
        config = {
            'api_key': st.secrets.get("gemini", {}).get("api_key", ""),
            'title': st.secrets.get("app", {}).get("title", "RepairMate - AI Repair Assistant"),
            'max_file_size': st.secrets.get("app", {}).get("max_file_size", 200),
            'supported_image_formats': st.secrets.get("app", {}).get("supported_image_formats", ["png", "jpg", "jpeg", "gif", "webp"]),
            'supported_video_formats': st.secrets.get("app", {}).get("supported_video_formats", ["mp4", "avi", "mov", "mkv"]),
            'theme': st.secrets.get("ui", {}).get("theme", "light"),
            'sidebar_expanded': st.secrets.get("ui", {}).get("sidebar_expanded", True)
        }
        return config
    except Exception as e:
        st.error(f"❌ Error loading configuration: {str(e)}")
        return {
            'api_key': "",
            'title': "RepairMate - AI Repair Assistant",
            'max_file_size': 200,
            'supported_image_formats': ["png", "jpg", "jpeg", "gif"],
            'supported_video_formats': ["mp4", "avi", "mov"],
            'theme': "light",
            'sidebar_expanded': True
        }

# Load app configuration
config = load_config()

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    
    .user-message {
        background-color: #f0f2f6;
        border-left-color: #ff6b6b;
    }
    
    .assistant-message {
        background-color: #e8f5e8;
        border-left-color: #51cf66;
    }
    
    .step-counter {
        background: #667eea;
        color: white;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-right: 10px;
    }
    
    .config-status {
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .config-error {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    
    .chat-container {
        height: 400px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #ddd;
        border-radius: 10px;
        background-color: #f9f9f9;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'uploaded_media' not in st.session_state:
    st.session_state.uploaded_media = None
if 'media_type' not in st.session_state:
    st.session_state.media_type = None
if 'conversation_started' not in st.session_state:
    st.session_state.conversation_started = False
if 'assistant' not in st.session_state:
    st.session_state.assistant = None
if 'user_input' not in st.session_state:
    st.session_state.user_input = ""

class RepairMateAssistant:
    def __init__(self, api_key: str):
        try:
            genai.configure(api_key=api_key)
            self.system_instruction = """You are an expert repair assistant called RepairMate AI. Your role is to help users diagnose and fix issues with their devices, appliances, or objects based on images/videos they share and their descriptions.

Guidelines for your responses:
1. Always be helpful, clear, and safety-conscious
2. Provide step-by-step instructions with numbered lists
3. Ask follow-up questions to better understand the problem
4. Warn about safety hazards and when to seek professional help
5. Suggest specific tools and materials needed
6. Be encouraging and supportive throughout the repair process
7. If you can't identify the issue clearly, ask for more specific information or different angles
8. Provide alternative solutions when possible
9. Include difficulty level (Easy/Medium/Hard) for each repair step

Start by analyzing any media provided and asking clarifying questions about the problem. Get relevant information such as device type, model number if relevant, recent repairs, and symptoms. Then guide the user through diagnosing and fixing the issue step-by-step."""
            
            self.model = genai.GenerativeModel(
                "gemini-2.0-flash-lite",
                system_instruction=self.system_instruction
            )
            self.chat = None
            self.api_configured = True
        except Exception as e:
            self.api_configured = False
            st.error(f"❌ Error configuring Gemini API: {str(e)}")
        
    def start_chat(self):
        """Initialize a new chat session"""
        if not self.api_configured:
            return None
            
        try:
            # Start chat with empty history - system instruction is already in the model
            self.chat = self.model.start_chat(history=[])
            return self.chat
        except Exception as e:
            st.error(f"❌ Error starting chat: {str(e)}")
            return None
    
    def send_message(self, message: str, media_data=None):
        """Send a message to Gemini with optional media"""
        if not self.api_configured:
            return "❌ API not configured properly. Please check your API key."
            
        try:
            # Initialize chat if not already started
            if self.chat is None:
                self.start_chat()
                if not self.chat:
                    return "❌ Failed to start chat session."
            
            # Prepare message content
            content = []
            if media_data:
                content.append(media_data)
            content.append(message)
            
            # Send message
            if len(content) > 1:
                response = self.chat.send_message(content)
            else:
                response = self.chat.send_message(message)
            
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            if "400" in error_msg or "role" in error_msg.lower():
                # Try to restart the chat session
                try:
                    self.chat = None
                    self.start_chat()
                    if self.chat:
                        if media_data:
                            response = self.chat.send_message([media_data, message])
                        else:
                            response = self.chat.send_message(message)
                        return response.text
                except:
                    pass
            return f"❌ Error: {error_msg}. Please try again or check your API key."

def process_uploaded_file(uploaded_file, config):
    """Process uploaded image or video file"""
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    
    if file_size_mb > config['max_file_size']:
        st.error(f"❌ File size ({file_size_mb:.1f}MB) exceeds limit of {config['max_file_size']}MB")
        return None, None
    
    if uploaded_file.type.startswith('image/'):
        try:
            image = Image.open(uploaded_file)
            return image, 'image'
        except Exception as e:
            st.error(f"❌ Error processing image: {str(e)}")
            return None, None
            
    elif uploaded_file.type.startswith('video/'):
        try:
            # For videos, we'll save temporarily and create a video object
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            tfile.write(uploaded_file.read())
            tfile.close()
            
            # Create a video file object for Gemini
            video_file = genai.upload_file(path=tfile.name)
            
            # Wait for video processing
            while video_file.state.name == "PROCESSING":
                time.sleep(1)
                video_file = genai.get_file(video_file.name)
            
            # Clean up temp file
            os.unlink(tfile.name)
            
            return video_file, 'video'
        except Exception as e:
            st.error(f"❌ Error processing video: {str(e)}")
            return None, None
    else:
        return None, None

# Main UI
st.markdown(f"""
<div class="main-header">
    <h1>🔧 {config['title']}</h1>
    <p>Upload an image or video of your broken item and get expert repair guidance!</p>
</div>
""", unsafe_allow_html=True)

# Check if API key is configured
api_configured = bool(config['api_key'])

if not api_configured:
    st.markdown("""
    <div class="config-status config-error">
        ❌ <strong>API Configuration:</strong> Gemini API key not found in secrets.toml
    </div>
    """, unsafe_allow_html=True)

# Initialize assistant if not already done
if api_configured and st.session_state.assistant is None:
    st.session_state.assistant = RepairMateAssistant(config['api_key'])

# Sidebar
with st.sidebar:
    # st.header("⚙️ Configuration")
    
    # # API Status
    # if api_configured:
    #     st.success("✅ API Key: Configured via secrets")
    # else:
    #     st.error("❌ API Key: Not configured")
    #     st.info("💡 Add your Gemini API key to `.streamlit/secrets.toml`")
    
    # # Manual API key override (for development)
    # with st.expander("🔧 Developer Override"):
    #     manual_api_key = st.text_input(
    #         "Manual API Key",
    #         type="password",
    #         help="Override secrets.toml API key for development"
    #     )
        
    #     if manual_api_key:
    #         st.session_state.assistant = RepairMateAssistant(manual_api_key)
    #         st.success("✅ Manual API Key configured!")
    #         api_configured = True
    
    # st.markdown("---")
    
    # Upload Media Section in Sidebar
    st.header("📤 Upload Media")
    
    # Create list of supported formats
    all_formats = config['supported_image_formats'] + config['supported_video_formats']
    
    uploaded_file = st.file_uploader(
        "Choose an image or video file",
        type=all_formats,
        help=f"Upload a clear image or video showing the issue (max {config['max_file_size']}MB)"
    )
    
    if uploaded_file:
        media_data, media_type = process_uploaded_file(uploaded_file, config)
        
        if media_data and media_type:
            st.session_state.uploaded_media = media_data
            st.session_state.media_type = media_type
            
            if media_type == 'image':
                st.image(media_data, caption="Uploaded Image", use_container_width=True)
            elif media_type == 'video':
                st.video(uploaded_file)
            
            st.success(f"✅ {media_type.title()} uploaded!")
            
            # Display file info
            file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
            st.info(f"📊 Size: {file_size:.1f}MB")
    
    st.markdown("---")
    
    if st.button("🔄 Start New Session"):
        st.session_state.chat_history = []
        st.session_state.uploaded_media = None
        st.session_state.media_type = None
        st.session_state.conversation_started = False
        st.session_state.user_input = ""
        if st.session_state.assistant:
            st.session_state.assistant.chat = None
        st.rerun()

# Main Chat Area
st.header("💬 Repair Assistant Chat")

# Display chat history in a scrollable container
with st.container():
    chat_container = st.container()

    with chat_container:
        if st.session_state.chat_history:
            for i, message in enumerate(st.session_state.chat_history):
                if message["role"] == "user":
                    with st.chat_message("user", avatar="🙋‍♂️"):
                        st.markdown(f"**You:**\n\n{message['content']}")
                else:
                    with st.chat_message("assistant", avatar="🔧"):
                        st.markdown(f"**RepairMate AI:**\n\n{message['content']}")
    
    # with chat_container:
    #     if st.session_state.chat_history:
    #         for i, message in enumerate(st.session_state.chat_history):
    #             if message['role'] == 'user':
    #                 st.markdown(f"""
    #                 <div class="chat-message user-message">
    #                     <strong>🙋‍♂️ You:</strong><br>
    #                     {message['content']}
    #                 </div>
    #                 """, unsafe_allow_html=True)
    #             else:
    #                 st.markdown(f"""
    #                 <div class="chat-message assistant-message">
    #                     <strong>🔧 RepairMate AI:</strong><br>
    #                     {message['content']}
    #                 </div>
    #                 """, unsafe_allow_html=True)
        else:
            st.info("👋 Welcome! Upload an image/video of your broken item in the sidebar and describe the issue below to get started.")

# Input section
st.subheader("✍️ Describe Your Issue")

# Text area with session state
user_input = st.text_area(
    "What's wrong with your item?",
    value=st.session_state.user_input,
    placeholder="Describe the problem in detail. For example: 'My phone screen is cracked and not responding to touch' or 'My laptop won't turn on after I spilled water on it'",
    height=100,
    key="user_input_area"
)

# Update session state with current value
st.session_state.user_input = user_input

# Quick examples (only show when no conversation has started)
if not st.session_state.chat_history:
    st.subheader("💡 Quick Examples")
    
    example_issues = [
        "My phone screen is cracked",
        "Laptop won't charge",
        "Car won't start",
        "Washing machine leaking",
        "TV has no sound",
        "Router keeps disconnecting"
    ]
    
    col1, col2, col3 = st.columns(3)
    
    for i, example in enumerate(example_issues):
        col_index = i % 3
        if col_index == 0:
            with col1:
                if st.button(f"💡 {example}", key=f"example_{i}", use_container_width=True):
                    st.session_state.user_input = example
                    st.rerun()
        elif col_index == 1:
            with col2:
                if st.button(f"💡 {example}", key=f"example_{i}", use_container_width=True):
                    st.session_state.user_input = example
                    st.rerun()
        else:
            with col3:
                if st.button(f"💡 {example}", key=f"example_{i}", use_container_width=True):
                    st.session_state.user_input = example
                    st.rerun()

# Send button
send_button = st.button("🚀 Send Message", type="primary", use_container_width=True)

# Process user input
if send_button and user_input and api_configured:
    if not st.session_state.assistant:
        st.error("❌ Assistant not initialized. Please check your API configuration!")
    else:
        # Add user message to chat history
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_input
        })
        
        # Prepare the message for Gemini
        message_content = user_input
        if not st.session_state.conversation_started and st.session_state.uploaded_media:
            message_content = f"I have uploaded a {st.session_state.media_type} showing an issue. Here's my description of the problem: {user_input}. Please analyze the {st.session_state.media_type} and help me fix this issue step by step. Please provide detailed instructions and mention any tools I might need."
            media_to_send = st.session_state.uploaded_media
            st.session_state.conversation_started = True
        else:
            media_to_send = None
        
        # Get AI response
        with st.spinner("🤔 RepairMate AI is analyzing..."):
            response = st.session_state.assistant.send_message(
                message_content, 
                media_to_send
            )
        
        # Add AI response to chat history
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': response
        })
        
        # Clear input and rerun
        st.session_state.user_input = ''
        st.rerun()

elif send_button and not api_configured:
    st.error("❌ Please configure your Gemini API key in secrets.toml!")
elif send_button and not user_input:
    st.error("❌ Please describe your issue!")

# Setup instructions (only show if API not configured)
if not api_configured:
    st.info("""
    🔑 **Setup Instructions:**
    1. Create `.streamlit/secrets.toml` in your project directory
    2. Add your Gemini API key: `[gemini] api_key = "your_key_here"`
    3. Get your free API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
    4. Restart the app after adding the key
    """)