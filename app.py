import streamlit as st
import boto3
import json
import uuid
import re
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
import io

# Configure page
st.set_page_config(
    page_title="DESCASIO - AWS AI Bedrock Agent Demo",
    page_icon="⚡",
    layout="wide"
)

# Chat-like styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #f0f2f6;
    }
    
    .chat-header {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d3436 100%);
        padding: 1.5rem 2rem;
        margin: -1rem -1rem 1rem -1rem;
        border-radius: 0 0 16px 16px;
        color: white;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.15);
    }
    
    .chat-header h1 {
        color: white;
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
    }
    
    .chat-header .subtitle {
        color: #b0b0b0;
        margin: 0.3rem 0 0 0;
        font-size: 0.9rem;
    }
    
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 0 1rem;
    }
    
    .message {
        margin: 1rem 0;
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
    }
    
    .message.bot {
        justify-content: flex-start;
    }
    
    .message.user {
        justify-content: flex-end;
    }
    
    .message-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        flex-shrink: 0;
    }
    
    .bot .message-avatar {
        background: #1a1a1a;
        color: white;
    }
    
    .user .message-avatar {
        background: #2196f3;
        color: white;
        order: 2;
    }
    
    .message-content {
        max-width: 70%;
        padding: 1rem 1.25rem;
        border-radius: 18px;
        font-size: 0.95rem;
        line-height: 1.4;
    }
    
    .bot .message-content {
        background: white;
        color: #1a1a1a;
        border: 1px solid #e0e0e0;
        border-bottom-left-radius: 6px;
    }
    
    .user .message-content {
        background: #2196f3;
        color: white;
        border-bottom-right-radius: 6px;
    }
    
    .typing-indicator {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin: 1rem 0;
    }
    
    .typing-dots {
        background: white;
        border: 1px solid #e0e0e0;
        padding: 1rem 1.25rem;
        border-radius: 18px;
        border-bottom-left-radius: 6px;
    }
    
    .typing-dots span {
        height: 8px;
        width: 8px;
        background: #999;
        border-radius: 50%;
        display: inline-block;
        margin-right: 4px;
        animation: typing 1.4s infinite;
    }
    
    .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
    .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
    
    @keyframes typing {
        0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
        30% { transform: translateY(-10px); opacity: 1; }
    }
    
    .input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        border-top: 1px solid #e0e0e0;
        padding: 1rem;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    }
    
    .input-wrapper {
        max-width: 800px;
        margin: 0 auto;
        display: flex;
        gap: 0.75rem;
        align-items: flex-end;
    }
    
    .chat-input {
        flex: 1;
        background: #f5f5f5;
        border: 2px solid #e0e0e0;
        border-radius: 20px;
        padding: 0.75rem 1rem;
        font-size: 0.95rem;
        resize: none;
        min-height: 20px;
        max-height: 120px;
        outline: none;
        transition: all 0.2s ease;
    }
    
    .chat-input:focus {
        border-color: #2196f3;
        background: white;
    }
    
    .send-button {
        background: #2196f3;
        color: white;
        border: none;
        border-radius: 50%;
        width: 44px;
        height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 1.1rem;
    }
    
    .send-button:hover {
        background: #1976d2;
        transform: scale(1.05);
    }
    
    .send-button:disabled {
        background: #ccc;
        cursor: not-allowed;
        transform: none;
    }
    
    .file-upload {
        background: #f5f5f5;
        color: #666;
        border: 2px dashed #ddd;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .file-upload:hover {
        border-color: #2196f3;
        background: #f0f8ff;
    }
    
    .decision-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #28a745;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .decision-card.rejected {
        border-left-color: #dc3545;
    }
    
    .decision-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #28a745;
    }
    
    .decision-title.rejected {
        color: #dc3545;
    }
    
    .download-buttons {
        display: flex;
        gap: 0.75rem;
        margin-top: 1rem;
    }
    
    .download-btn {
        flex: 1;
        background: #2196f3;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .download-btn:hover {
        background: #1976d2;
    }
    
    .chat-content {
        padding-bottom: 100px;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display: none;}
    footer {visibility: hidden;}
    .stApp > header {display: none;}
    
    .stFileUploader > div {
        border: none !important;
        background: none !important;
    }
    
    .stFileUploader label {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = [
        {
            'role': 'bot',
            'content': "Hello! I'm your AI loan officer. I can help you apply for a business loan. You can either upload your completed application or tell me about your financing needs. What would you like to do?",
            'timestamp': datetime.now()
        }
    ]
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'awaiting_file' not in st.session_state:
    st.session_state.awaiting_file = False

# Header
st.markdown('''
<div class="chat-header">
    <h1>GITEX Demo Bank - AI Loan Officer</h1>
    <p class="subtitle">Powered by AWS Bedrock AI</p>
</div>
''', unsafe_allow_html=True)

# Get configuration
try:
    agent_id = st.secrets.get("AGENT_ID", "")
    agent_alias_id = st.secrets.get("AGENT_ALIAS_ID", "TSTALIASID")
    aws_access_key = st.secrets.get("AWS_ACCESS_KEY_ID", "")
    aws_secret_key = st.secrets.get("AWS_SECRET_ACCESS_KEY", "")
    aws_region = st.secrets.get("AWS_REGION", "eu-west-2")
    
    if not agent_id:
        st.error("Configuration Required: Please add your AGENT_ID to Streamlit secrets")
        st.stop()
        
except Exception:
    st.error("Configuration Required: Please add your AWS credentials")
    st.stop()

# AWS client
@st.cache_resource
def get_bedrock_client():
    try:
        return boto3.client(
            'bedrock-agent-runtime',
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
    except Exception as e:
        st.error(f"AWS Connection Failed: {str(e)}")
        return None

# Chat container
st.markdown('<div class="chat-container"><div class="chat-content">', unsafe_allow_html=True)

# Display chat messages
for i, message in enumerate(st.session_state.chat_messages):
    role_class = "bot" if message['role'] == 'bot' else "user"
    avatar = "🤖" if message['role'] == 'bot' else "👤"
    
    st.markdown(f'''
    <div class="message {role_class}">
        <div class="message-avatar">{avatar}</div>
        <div class="message-content">{message['content']}</div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Show decision card if this is a loan decision
    if message['role'] == 'bot' and 'APPROVED' in message['content'] or 'REJECTED' in message['content']:
        loan_data = parse_loan_data(message['content']) if 'parse_loan_data' in globals() else None
        if loan_data:
            decision_class = "rejected" if loan_data['decision'] == 'REJECTED' else ""
            title_class = "rejected" if loan_data['decision'] == 'REJECTED' else ""
            
            st.markdown(f'''
            <div class="decision-card {decision_class}">
                <div class="decision-title {title_class}">
                    {'❌ Application Not Approved' if loan_data['decision'] == 'REJECTED' else '✅ Loan Approved!'}
                </div>
                <div><strong>Applicant:</strong> {loan_data['applicant_name']}</div>
                <div><strong>Amount:</strong> ${loan_data['loan_amount']:,} {f'at {loan_data["interest_rate"]}% APR' if loan_data['interest_rate'] > 0 else ''}</div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 Download Report", key=f"report_{i}", use_container_width=True):
                    report_pdf = generate_loan_report(loan_data)
                    st.download_button(
                        label="📊 Download Report",
                        data=report_pdf,
                        file_name=f"Loan_Report.pdf",
                        mime="application/pdf",
                        key=f"dl_report_{i}"
                    )
            with col2:
                if st.button("📝 Download Letter", key=f"letter_{i}", use_container_width=True):
                    letter_pdf = generate_decision_letter(loan_data)
                    st.download_button(
                        label="📝 Download Letter",
                        data=letter_pdf,
                        file_name=f"Decision_Letter.pdf",
                        mime="application/pdf",
                        key=f"dl_letter_{i}"
                    )

# Show typing indicator when processing
if st.session_state.processing:
    st.markdown('''
    <div class="typing-indicator">
        <div class="message-avatar" style="background: #1a1a1a; color: white;">🤖</div>
        <div class="typing-dots">
            <span></span><span></span><span></span>
        </div>
    </div>
    ''', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)

# File upload area (when needed)
if st.session_state.awaiting_file:
    st.markdown('<div style="max-width: 800px; margin: 0 auto; padding: 0 1rem;">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload your loan application (PDF)",
        type=['pdf'],
        key="file_uploader"
    )
    
    if uploaded_file:
        st.session_state.awaiting_file = False
        st.session_state.processing = True
        
        # Add user message
        st.session_state.chat_messages.append({
            'role': 'user',
            'content': f"📄 Uploaded: {uploaded_file.name}",
            'timestamp': datetime.now()
        })
        
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Input area
if not st.session_state.processing and not st.session_state.awaiting_file:
    # Create input form
    with st.form(key="chat_form", clear_on_submit=True):
        st.markdown('''
        <div class="input-container">
            <div class="input-wrapper">
        ''', unsafe_allow_html=True)
        
        user_input = st.text_area(
            "",
            placeholder="Tell me about your loan needs, or type 'upload' to send a document...",
            height=50,
            key="user_input",
            label_visibility="collapsed"
        )
        
        submitted = st.form_submit_button("Send", use_container_width=False)
        
        st.markdown('''
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        if submitted and user_input.strip():
            # Handle file upload request
            if "upload" in user_input.lower() and ("file" in user_input.lower() or "document" in user_input.lower()):
                st.session_state.chat_messages.append({
                    'role': 'user',
                    'content': user_input,
                    'timestamp': datetime.now()
                })
                st.session_state.chat_messages.append({
                    'role': 'bot',
                    'content': "Perfect! Please upload your loan application document below and I'll analyze it for you.",
                    'timestamp': datetime.now()
                })
                st.session_state.awaiting_file = True
                st.rerun()
            else:
                # Regular message
                st.session_state.chat_messages.append({
                    'role': 'user',
                    'content': user_input,
                    'timestamp': datetime.now()
                })
                st.session_state.processing = True
                st.rerun()

# Process messages
if st.session_state.processing:
    def call_bedrock_agent(message, file_name=None):
        bedrock = get_bedrock_client()
        if not bedrock:
            return "I'm having trouble connecting to our loan processing system. Please try again."
        
        try:
            if file_name:
                prompt = f"Please analyze this loan application: {file_name}. Provide a comprehensive decision with reasons."
            else:
                prompt = f"As a loan officer, please analyze this request: {message}. Provide a decision (APPROVED/REJECTED) with clear reasoning and terms if approved."
            
            response = bedrock.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                enableTrace=False,
                sessionId=st.session_state.session_id,
                inputText=prompt
            )
            
            completion = ""
            for event in response.get("completion", []):
                if 'chunk' in event:
                    chunk = event["chunk"]
                    completion += chunk["bytes"].decode()
            
            return completion or "I apologize, but I didn't receive a proper response. Could you try again?"
            
        except Exception as e:
            return f"I encountered an error processing your request: {str(e)}"
    
    # Get the last user message
    last_message = st.session_state.chat_messages[-1]
    
    if last_message['role'] == 'user':
        # Check if it's a file upload
        if last_message['content'].startswith('📄 Uploaded:'):
            file_name = last_message['content'].replace('📄 Uploaded: ', '')
            response = call_bedrock_agent("", file_name)
        else:
            response = call_bedrock_agent(last_message['content'])
        
        # Add bot response
        st.session_state.chat_messages.append({
            'role': 'bot',
            'content': response,
            'timestamp': datetime.now()
        })
        
        st.session_state.processing = False
        st.rerun()

# Helper functions
def parse_loan_data(response_text):
    try:
        # Extract key information from response
        applicant_name = "Loan Applicant"
        name_patterns = [r'applicant[:\s]+([A-Za-z\s]+)', r'name[:\s]+([A-Za-z\s]+)']
        for pattern in name_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                name_candidate = match.group(1).strip()
                if len(name_candidate.split()) <= 3:  # Reasonable name length
                    applicant_name = name_candidate
                    break
        
        # Extract amount
        loan_amount = 0
        amount_match = re.search(r'\$[\s]*([\d,]+)', response_text)
        if amount_match:
            try:
                loan_amount = int(amount_match.group(1).replace(',', ''))
            except:
                pass
        
        # Extract decision
        decision = "PENDING"
        if re.search(r'\b(approved?|approve)\b', response_text, re.IGNORECASE):
            decision = "APPROVED"
        elif re.search(r'\b(rejected?|declined?|deny|denied)\b', response_text, re.IGNORECASE):
            decision = "REJECTED"
        
        # Extract rate
        rate_match = re.search(r'(\d+\.?\d*)\s*%', response_text)
        interest_rate = float(rate_match.group(1)) if rate_match else 0
        
        return {
            'applicant_name': applicant_name,
            'loan_amount': loan_amount,
            'decision': decision,
            'interest_rate': interest_rate,
            'full_response': response_text,
            'timestamp': datetime.now().strftime('%B %d, %Y at %I:%M %p')
        }
    except:
        return {
            'applicant_name': "Loan Applicant",
            'loan_amount': 0,
            'decision': "PENDING",
            'interest_rate': 0,
            'full_response': response_text,
            'timestamp': datetime.now().strftime('%B %d, %Y at %I:%M %p')
        }

def generate_loan_report(loan_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    story.append(Paragraph("GITEX DEMO BANK - LOAN ANALYSIS", styles['Title']))
    story.append(Spacer(1, 30))
    
    summary_data = [
        ['Applicant:', loan_data['applicant_name']],
        ['Decision:', loan_data['decision']],
        ['Date:', loan_data['timestamp']]
    ]
    
    if loan_data['loan_amount'] > 0:
        summary_data.append(['Amount:', f"${loan_data['loan_amount']:,}"])
    if loan_data['interest_rate'] > 0:
        summary_data.append(['Rate:', f"{loan_data['interest_rate']}%"])
    
    table = Table(summary_data)
    table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, black)]))
    story.append(table)
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("Analysis:", styles['Heading2']))
    story.append(Paragraph(loan_data['full_response'], styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def generate_decision_letter(loan_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    story.append(Paragraph("GITEX DEMO BANK", styles['Title']))
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Dear {loan_data['applicant_name']},", styles['Normal']))
    story.append(Spacer(1, 20))
    
    if loan_data['decision'] == 'APPROVED':
        content = "Congratulations! Your loan application has been approved."
    else:
        content = "Thank you for your application. We are unable to approve your loan at this time."
    
    story.append(Paragraph(content, styles['Normal']))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Sincerely,", styles['Normal']))
    story.append(Paragraph("GITEX Demo Bank", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
