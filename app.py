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
import PyPDF2

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
    
    .chat-content {
        padding-bottom: 100px;
    }
    
    .stTextArea > div > div > textarea {
        border: 2px solid #e0e0e0;
        border-radius: 20px;
        padding: 0.75rem 1rem;
        font-size: 0.95rem;
        background: #f5f5f5;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #2196f3;
        background: white;
    }
    
    .stButton > button {
        background: #2196f3;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background: #1976d2;
        transform: translateY(-1px);
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

# Helper functions
def read_pdf_content(uploaded_file):
    """Extract text content from uploaded PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text_content = ""
        
        for page in pdf_reader.pages:
            text_content += page.extract_text() + "\n"
        
        return text_content.strip()
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def parse_loan_data(response_text):
    try:
        applicant_name = "Loan Applicant"
        name_patterns = [r'applicant[:\s]+([A-Za-z\s]+)', r'name[:\s]+([A-Za-z\s]+)']
        for pattern in name_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                name_candidate = match.group(1).strip()
                if len(name_candidate.split()) <= 3:
                    applicant_name = name_candidate
                    break
        
        loan_amount = 0
        amount_match = re.search(r'\$[\s]*([\d,]+)', response_text)
        if amount_match:
            try:
                loan_amount = int(amount_match.group(1).replace(',', ''))
            except:
                pass
        
        decision = "PENDING"
        if re.search(r'\b(approved?|approve)\b', response_text, re.IGNORECASE):
            decision = "APPROVED"
        elif re.search(r'\b(rejected?|declined?|deny|denied)\b', response_text, re.IGNORECASE):
            decision = "REJECTED"
        
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
    
    # Custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontSize=24,
        textColor=HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=1,
        fontName='Helvetica-Bold'
    )
    
    story.append(Paragraph("GITEX DEMO BANK", title_style))
    story.append(Paragraph("COMPREHENSIVE LOAN ANALYSIS REPORT", title_style))
    story.append(Spacer(1, 30))
    
    # Executive summary table
    summary_data = [
        ['Report Generated:', loan_data['timestamp']],
        ['Applicant Name:', loan_data['applicant_name']],
        ['Requested Amount:', f"${loan_data['loan_amount']:,}" if loan_data['loan_amount'] > 0 else "Not specified"],
        ['Final Decision:', loan_data['decision']],
        ['Processing System:', 'AI-Powered Multi-Agent Platform']
    ]
    
    if loan_data['decision'] == 'APPROVED' and loan_data['interest_rate'] > 0:
        summary_data.append(['Approved Interest Rate:', f"{loan_data['interest_rate']}% per annum"])
    
    summary_table = Table(summary_data, colWidths=[2.5*inch, 3.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0,0), (0,-1), HexColor('#1a1a1a')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 12),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e5e5e5')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [white, HexColor('#f8f9fa')])
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 40))
    
    # Analysis section
    story.append(Paragraph("DETAILED ANALYSIS & DECISION RATIONALE", styles['Heading2']))
    
    response_text = loan_data['full_response']
    paragraphs = response_text.split('\n\n') if '\n\n' in response_text else [response_text]
    
    for para in paragraphs:
        if para.strip():
            story.append(Paragraph(para.strip(), styles['Normal']))
            story.append(Spacer(1, 12))
    
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

def call_bedrock_agent(message, file_content=None, file_name=None):
    bedrock = get_bedrock_client()
    if not bedrock:
        return "I'm having trouble connecting to our loan processing system. Please try again."
    
    try:
        if file_content:
            prompt = f"""Please analyze this loan application document. Here is the complete content:

{file_content}

Based on this loan application, please provide a comprehensive analysis including:
- Applicant information
- Loan amount requested  
- Your recommendation (APPROVED/REJECTED)
- Interest rate (if approved)
- Key decision factors
- Risk assessment
- Any conditions or requirements

Be professional and thorough in your analysis."""
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
    
    # Show download links if this is a loan decision
    if message['role'] == 'bot' and ('APPROVED' in message['content'] or 'REJECTED' in message['content']) and len(message['content']) > 100:
        loan_data = parse_loan_data(message['content'])
        
        # AI follow-up message about documents
        st.markdown(f'''
        <div style="max-width: 70%; margin: 0.5rem 0 1rem 0;">
            <div class="message bot">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    I've generated your professional loan documents. You can download them below:
                    <br><br>
                    📊 <strong>Detailed Analysis Report</strong> - Complete loan assessment with decision rationale
                    <br>
                    📝 <strong>Official Decision Letter</strong> - Formal correspondence on bank letterhead
                    <br><br>
                    Would you like me to regenerate these with any additional details?
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Download section with working buttons  
        st.markdown('''
        <div style="background: #e3f2fd; border: 2px solid #2196f3; border-radius: 12px; 
                    padding: 1.5rem; margin: 1rem 0; text-align: center;">
            <div style="font-size: 1.1rem; font-weight: 600; color: #0d47a1; margin-bottom: 1rem;">
                📄 Your Loan Documents Are Ready
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Download buttons
        col1, col2 = st.columns(2)
        with col1:
            try:
                report_pdf = generate_loan_report(loan_data)
                st.download_button(
                    label="📊 Download Detailed Report",
                    data=report_pdf,
                    file_name=f"GITEX_Loan_Report_{loan_data['applicant_name'].replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key=f"report_{i}",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Report generation error: {str(e)}")
        
        with col2:
            try:
                letter_pdf = generate_decision_letter(loan_data)
                st.download_button(
                    label="📝 Download Decision Letter",
                    data=letter_pdf,
                    file_name=f"GITEX_Decision_Letter_{loan_data['applicant_name'].replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key=f"letter_{i}",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Letter generation error: {str(e)}")

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

# Input area
if not st.session_state.processing:
    st.markdown('''
    <div class="input-container">
        <div class="input-wrapper">
    ''', unsafe_allow_html=True)
    
    # Create form to handle both text and file input
    with st.form(key="chat_form", clear_on_submit=True):
        # Create columns for input, upload, and send
        col1, col2 = st.columns([5, 1])
        
        with col1:
            user_input = st.text_area(
                "",
                placeholder="Tell me about your loan needs...",
                height=50,
                key="user_input",
                label_visibility="collapsed"
            )
        
        with col2:
            # File upload
            uploaded_file = st.file_uploader(
                "📎 Upload PDF",
                type=['pdf'],
                key="file_upload",
                help="Upload loan application PDF"
            )
        
        # Send button
        submitted = st.form_submit_button("Send", type="primary", use_container_width=True)
        
        # Handle form submission
        if submitted:
            if uploaded_file is not None:
                # Handle file upload - read PDF content
                pdf_content = read_pdf_content(uploaded_file)
                st.session_state.chat_messages.append({
                    'role': 'user',
                    'content': f"📄 Uploaded: {uploaded_file.name}",
                    'timestamp': datetime.now()
                })
                st.session_state.processing = True
                st.session_state.current_file_content = pdf_content
                st.session_state.current_file_name = uploaded_file.name
                st.rerun()
            elif user_input.strip():
                # Handle text message
                st.session_state.chat_messages.append({
                    'role': 'user',
                    'content': user_input,
                    'timestamp': datetime.now()
                })
                st.session_state.processing = True
                st.session_state.current_file_content = None
                st.session_state.current_file_name = None
                st.rerun()
    
    st.markdown('''
        </div>
    </div>
    ''', unsafe_allow_html=True)

# Process messages
if st.session_state.processing:
    # Get the last user message
    last_message = st.session_state.chat_messages[-1]
    
    if last_message['role'] == 'user':
        # Check if it's a file upload
        if last_message['content'].startswith('📄 Uploaded:'):
            # Use the PDF content we extracted
            file_content = st.session_state.get('current_file_content', '')
            file_name = st.session_state.get('current_file_name', 'document.pdf')
            response = call_bedrock_agent("", file_content=file_content, file_name=file_name)
        else:
            response = call_bedrock_agent(last_message['content'])
        
        # Add bot response
        st.session_state.chat_messages.append({
            'role': 'bot',
            'content': response,
            'timestamp': datetime.now()
        })
        
        # Clear file data
        if 'current_file_content' in st.session_state:
            del st.session_state.current_file_content
        if 'current_file_name' in st.session_state:
            del st.session_state.current_file_name
        
        st.session_state.processing = False
        st.rerun()
