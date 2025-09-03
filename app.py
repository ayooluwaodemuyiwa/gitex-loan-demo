import streamlit as st
import boto3
import uuid
import re
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
import io
import time

# -----------------------------
# Page config + minimal theme
# -----------------------------
st.set_page_config(page_title="Credit Decisioning Demo", page_icon="", layout="wide")
st.markdown("""
<style>
:root {
  --bg:#fafbfc; --panel:#ffffff; --ink:#111827; --sub:#6b7280; --border:#e5e7eb;
}
html, body, [class*="css"] { font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
body { background: var(--bg); }
.header {
  background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
  color: #fff; padding: 28px 24px; border-radius: 0 0 12px 12px; margin: -16px -16px 24px -16px;
}
.header h1 { margin:0; font-weight:700; letter-spacing:-0.02em; }
.header p { margin:6px 0 0 0; color:#d1d5db; }

.panel { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
.label { font-weight:600; color: var(--ink); margin-bottom:8px; }
.help { color: var(--sub); font-size: 13px; margin-top:6px; }
.hr { height:1px; background:var(--border); margin: 20px 0; }
.kpi { background:#f8fafc; border:1px solid var(--border); border-radius:10px; padding:14px; text-align:center; }
.kpi .k { font-size:12px; color:var(--sub); margin-bottom:4px; }
.kpi .v { font-size:16px; font-weight:700; color:var(--ink); }

.badge { display:inline-block; padding:6px 10px; border-radius:999px; font-size:12px; font-weight:700; border:1px solid var(--border); }
.badge.approved { background:#ecfdf5; border-color:#bbf7d0; color:#065f46; }
.badge.rejected { background:#fef2f2; border-color:#fecaca; color:#7f1d1d; }
.badge.pending  { background:#fffbeb; border-color:#fde68a; color:#92400e; }

/* Hide Streamlit chrome we don't need */
#MainMenu {visibility: hidden;} .stDeployButton{display:none;} footer{visibility:hidden;} .stApp > header{display:none;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Session state
# -----------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "loan_data" not in st.session_state:
    st.session_state.loan_data = None

# -----------------------------
# Header
# -----------------------------
st.markdown("""
<div class="header">
  <h1>Credit Decisioning Demo</h1>
  <p>Side-by-side intake. Single decisive action. Professional results.</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# Config / secrets
# -----------------------------
try:
    agent_id = st.secrets.get("AGENT_ID", "")
    agent_alias_id = st.secrets.get("AGENT_ALIAS_ID", "TSTALIASID")
    aws_access_key = st.secrets.get("AWS_ACCESS_KEY_ID", "")
    aws_secret_key = st.secrets.get("AWS_SECRET_ACCESS_KEY", "")
    aws_region = st.secrets.get("AWS_REGION", "eu-west-2")
    if not agent_id:
        st.error("Configuration missing: set AGENT_ID in Streamlit secrets.")
        st.stop()
except Exception:
    st.error("Configuration missing: set AWS credentials and AGENT_ID in Streamlit secrets.")
    st.stop()

@st.cache_resource
def get_bedrock_client():
    try:
        return boto3.client(
            "bedrock-agent-runtime",
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
    except Exception as e:
        st.error(f"AWS connection failed: {e}")
        return None

# -----------------------------
# Agent call
# -----------------------------
def call_bedrock_agent(message, file_name=None):
    bedrock = get_bedrock_client()
    if not bedrock:
        return "Unable to connect to the decisioning system. Please try again."

    if file_name:
        prompt = f"""Process this loan application file: {file_name}.

Return:
- Applicant name (if available)
- Loan amount requested
- Recommendation (APPROVED or REJECTED)
- Interest rate (if approved)
- Key decision factors
- Any conditions or required documents

Keep it precise and neutral."""
    else:
        prompt = f"""Loan Request:

{message}

Return:
- Recommendation (APPROVED or REJECTED)
- Suggested loan amount and terms
- Interest rate recommendation
- Key decision factors
- Any additional requirements

Keep it precise and neutral."""

    try:
        response = bedrock.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            enableTrace=False,
            sessionId=st.session_state.session_id,
            inputText=prompt
        )
        completion = ""
        for event in response.get("completion", []):
            if "chunk" in event:
                completion += event["chunk"]["bytes"].decode()
        return completion.strip() or "No response received from the decisioning system."
    except Exception as e:
        return f"Processing error: {e}"

# -----------------------------
# Parsing / PDFs (reusing your logic)
# -----------------------------
def parse_loan_data(response_text):
    try:
        name_patterns = [r'applicant[:\s]+([A-Za-z\s]+)', r'name[:\s]+([A-Za-z\s]+)',
                         r'borrower[:\s]+([A-Za-z\s]+)', r'client[:\s]+([A-Za-z\s]+)']
        applicant_name = "Loan Applicant"
        for p in name_patterns:
            m = re.search(p, response_text, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if not any(w in cand.lower() for w in ["report","analysis","decision","loan","bank"]):
                    applicant_name = cand
                    break

        amount_patterns = [r'\$[\s]*([\d,]+)', r'amount[:\s]+\$?([\d,]+)']
        loan_amount = 0
        for p in amount_patterns:
            m = re.search(p, response_text, re.IGNORECASE)
            if m:
                try:
                    loan_amount = int(m.group(1).replace(",", ""))
                    break
                except:
                    pass

        decision = "PENDING"
        if re.search(r'\bapproved?\b', response_text, re.IGNORECASE):
            decision = "APPROVED"
        elif re.search(r'\b(rejected?|declined?|deny|denied)\b', response_text, re.IGNORECASE):
            decision = "REJECTED"

        rate_match = re.search(r'(\d+\.?\d*)\s*%', response_text)
        interest_rate = float(rate_match.group(1)) if rate_match else 0.0

        return {
            "applicant_name": applicant_name,
            "loan_amount": loan_amount,
            "decision": decision,
            "interest_rate": interest_rate,
            "full_response": response_text,
            "timestamp": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        }
    except Exception:
        return {
            "applicant_name": "Loan Applicant",
            "loan_amount": 0, "decision": "PENDING", "interest_rate": 0.0,
            "full_response": response_text,
            "timestamp": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        }

def generate_loan_report(loan_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    title = ParagraphStyle('Title', parent=styles['Title'], fontSize=22,
                           textColor=HexColor('#111827'), spaceAfter=24, alignment=1,
                           fontName='Helvetica-Bold')
    header = ParagraphStyle('Header', parent=styles['Heading2'], fontSize=14,
                            textColor=HexColor('#111827'), spaceAfter=12,
                            fontName='Helvetica-Bold')

    story.append(Paragraph("Credit Decisioning Demo", title))
    story.append(Paragraph("Loan Analysis Report", title))
    story.append(Spacer(1, 20))

    summary_data = [
        ['Report Generated:', loan_data['timestamp']],
        ['Applicant Name:', loan_data['applicant_name']],
        ['Requested Amount:', f"${loan_data['loan_amount']:,}" if loan_data['loan_amount'] > 0 else "Not specified"],
        ['Decision:', loan_data['decision']],
        ['Processing System:', 'Automated Decisioning Platform']
    ]
    if loan_data['decision'] == 'APPROVED' and loan_data['interest_rate'] > 0:
        summary_data.append(['Approved Interest Rate:', f"{loan_data['interest_rate']}% per annum"])

    t = Table(summary_data, colWidths=[2.5*inch, 3.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0,0), (0,-1), HexColor('#111827')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [white, HexColor('#f8f9fa')])
    ]))
    story.append(t); story.append(Spacer(1, 24))

    story.append(Paragraph("Analysis & Rationale", header))
    for para in (loan_data['full_response'] or "").split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), styles['Normal']))
            story.append(Spacer(1, 10))

    doc.build(story); buffer.seek(0)
    return buffer.getvalue()

def generate_decision_letter(loan_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    header = ParagraphStyle('Header', parent=styles['Normal'], fontSize=14,
                            textColor=HexColor('#111827'), alignment=1, fontName='Helvetica-Bold')
    story.append(Paragraph("Credit Decisioning Demo", header))
    story.append(Paragraph("Decisioning Unit", styles['Normal']))
    story.append(Spacer(1, 24))
    story.append(Paragraph(f"Date: {loan_data['timestamp']}", styles['Normal']))
    story.append(Spacer(1, 16))
    story.append(Paragraph(f"Dear {loan_data['applicant_name']},", styles['Normal']))
    story.append(Spacer(1, 12))

    if loan_data['decision'] == 'APPROVED':
        subject = "Loan Application — Approved"
        story.append(Paragraph(subject, ParagraphStyle('S', parent=styles['Normal'], fontName='Helvetica-Bold')))
        story.append(Spacer(1, 10))
        content = "Your loan application has been approved."
        if loan_data['loan_amount'] > 0:
            content += f" Approved amount: ${loan_data['loan_amount']:,}."
        if loan_data['interest_rate'] > 0:
            content += f" Interest rate: {loan_data['interest_rate']}% per annum."
        content += """

Next steps:
• A loan officer will contact you within 48 hours.
• Prepare required documentation for final verification.
• Disbursement follows completion of all paperwork."""
    else:
        subject = "Loan Application — Status Update"
        story.append(Paragraph(subject, ParagraphStyle('S', parent=styles['Normal'], fontName='Helvetica-Bold')))
        story.append(Spacer(1, 10))
        content = """Thank you for your application. Based on the current assessment, we are unable to approve the loan at this time.

You may consider:
• Reviewing and strengthening your financial position.
• Reapplying in 6–12 months.
• Speaking with an advisor for guidance."""

    story.append(Paragraph(content, styles['Normal']))
    story.append(Spacer(1, 24))
    story.append(Paragraph("Sincerely,", styles['Normal']))
    story.append(Spacer(1, 18))
    story.append(Paragraph("Decisioning Unit", ParagraphStyle('Sig', parent=styles['Normal'], fontName='Helvetica-Bold')))
    doc.build(story); buffer.seek(0)
    return buffer.getvalue()

# -----------------------------
# Intake (side-by-side)
# -----------------------------
st.markdown('<div class="panel">', unsafe_allow_html=True)
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="label">Upload completed application (PDF)</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Select PDF", type=["pdf"], label_visibility="collapsed")
    st.markdown('<div class="help">If provided, the PDF will be analyzed and used as the primary input.</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="label">Or describe the loan request</div>', unsafe_allow_html=True)
    user_message = st.text_area(
        label="Describe",
        label_visibility="collapsed",
        placeholder="Example: Requesting USD 25,000 for equipment. Operating 3 years, monthly revenue USD 8,000, good credit, collateral available.",
        height=120
    )
    st.markdown('<div class="help">Use concise, factual details. If a PDF is uploaded, this text is ignored.</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Submit
# -----------------------------
st.markdown('<div class="panel">', unsafe_allow_html=True)

both_provided = (uploaded_file is not None) and user_message.strip()
neither_provided = (uploaded_file is None) and (not user_message.strip())

if both_provided:
    st.warning("Please provide one input method: upload a PDF or describe the request, not both.")
if neither_provided:
    st.info("Provide a PDF or a brief description to continue.")

can_submit = not both_provided and not neither_provided
submit = st.button("Run Analysis", type="primary", use_container_width=True, disabled=not can_submit)

if submit:
    with st.spinner("Running analysis"):
        time.sleep(0.6)  # brief UX pause
        if uploaded_file is not None:
            response = call_bedrock_agent("", uploaded_file.name)
        else:
            response = call_bedrock_agent(user_message)
    st.session_state.last_response = response
    st.session_state.loan_data = parse_loan_data(response)
    st.experimental_rerun()

st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Result
# -----------------------------
if st.session_state.last_response and st.session_state.loan_data:
    ld = st.session_state.loan_data
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    # Status
    if ld["decision"] == "APPROVED":
        st.markdown('<span class="badge approved">Approved</span>', unsafe_allow_html=True)
    elif ld["decision"] == "REJECTED":
        st.markdown('<span class="badge rejected">Not Approved</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge pending">Pending / Review</span>', unsafe_allow_html=True)

    st.write("")
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(f'<div class="kpi"><div class="k">Applicant</div><div class="v">{ld["applicant_name"]}</div></div>', unsafe_allow_html=True)
    with k2:
        amount_display = f"${ld['loan_amount']:,}" if ld["loan_amount"] > 0 else "Not specified"
        st.markdown(f'<div class="kpi"><div class="k">Requested Amount</div><div class="v">{amount_display}</div></div>', unsafe_allow_html=True)
    with k3:
        rate_display = f"{ld['interest_rate']}% APR" if ld['interest_rate'] > 0 else "TBD"
        st.markdown(f'<div class="kpi"><div class="k">Interest Rate</div><div class="v">{rate_display}</div></div>', unsafe_allow_html=True)

    st.write("")
    st.markdown("**Detailed Analysis**")
    st.code(st.session_state.last_response)

    st.write("")
    cdl, cdl2 = st.columns(2)
    with cdl:
        try:
            report_pdf = generate_loan_report(st.session_state.loan_data)
            st.download_button(
                label="Download Detailed Report (PDF)",
                data=report_pdf,
                file_name=f"Loan_Report_{ld['applicant_name'].replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Report generation error: {e}")

    with cdl2:
        try:
            letter_pdf = generate_decision_letter(st.session_state.loan_data)
            st.download_button(
                label="Download Decision Letter (PDF)",
                data=letter_pdf,
                file_name=f"Decision_Letter_{ld['applicant_name'].replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Letter generation error: {e}")

    st.write("")
    colb1, colb2 = st.columns([1,1])
    with colb1:
        if st.button("Start New Analysis", use_container_width=True):
            st.session_state.last_response = None
            st.session_state.loan_data = None
            st.experimental_rerun()
    with colb2:
        st.caption(f"Generated {ld['timestamp']} • Session {st.session_state.session_id[-8:]}")

    st.markdown('</div>', unsafe_allow_html=True)
