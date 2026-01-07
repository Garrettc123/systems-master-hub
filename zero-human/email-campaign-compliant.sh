#!/bin/bash

# ZERO-HUMAN EMAIL CAMPAIGN - GDPR/CAN-SPAM COMPLIANT
# Generates compliant partnership outreach templates
# Ready for manual sending or integration with email service
# Usage: bash email-campaign-compliant.sh

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ ZERO-HUMAN EMAIL CAMPAIGN - COMPLIANT MODE ║"
echo "║ GDPR + CAN-SPAM compliant partnership outreach ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Configuration
SENDER_NAME="Garrett Carroll"
SENDER_EMAIL="gwc2780@gmail.com"
COMPANY="Zero-Human Systems"
DEMO_URL="https://github.com/Garrettc123"
CAMPAIGN_DATE=$(date +"%Y-%m-%d")

echo "📋 CAMPAIGN CONFIGURATION"
echo "═════════════════════════════════════════════════════════════════"
echo "Sender: $SENDER_NAME <$SENDER_EMAIL>"
echo "Company: $COMPANY"
echo "Date: $CAMPAIGN_DATE"
echo "Status: COMPLIANCE CHECK REQUIRED BEFORE SENDING"
echo ""

# Create compliance checklist
echo "🔍 COMPLIANCE REQUIREMENTS CHECKLIST"
echo "═════════════════════════════════════════════════════════════════"
echo ""
echo "Before sending ANY emails, verify ALL of these:"
echo ""
echo "☐ EMAIL AUTHENTICATION:"
echo "  □ SPF record configured (ask domain provider)"
echo "  □ DKIM signature enabled (Gmail Settings → Forwarding)"
echo "  □ DMARC policy set (optional but recommended)"
echo "  □ Test with mail-tester.com before live send"
echo ""
echo "☐ LEGAL COMPLIANCE:"
echo "  □ CAN-SPAM Act (US): Requires unsubscribe link"
echo "  □ GDPR (EU): Requires explicit opt-in consent"
echo "  □ CASL (Canada): Cannot send without prior relationship"
echo "  □ CCPA (California): Must provide opt-out option"
echo ""
echo "☐ RECIPIENT VALIDATION:"
echo "  □ Email addresses verified (valid format)"
echo "  □ No purchased/rented email lists"
echo "  □ Warm introductions preferred where possible"
echo "  □ Not more than 100 emails/day from new domain"
echo ""
echo "☐ CONTENT REQUIREMENTS:"
echo "  □ Clear sender identification"
echo "  □ Legitimate business purpose stated"
echo "  □ Unsubscribe mechanism included"
echo "  □ Physical mailing address included"
echo "  □ No deceptive subject lines"
echo ""

echo "📧 GENERATING COMPLIANT EMAIL TEMPLATE"
echo "═════════════════════════════════════════════════════════════════"
echo ""

# Create template email
TEMPLATE_FILE="email_partnership_template_$(date +%s).txt"

cat > "$TEMPLATE_FILE" << 'EOF'
SUBJECT: Partnership Opportunity - Enterprise AI Governance Platform

TO: [RECIPIENT_EMAIL]
Cc: 
Bcc: 

---

Dear [RECIPIENT_NAME],

I'm Garrett Carroll, founder of Zero-Human Systems, building autonomous enterprise AI governance infrastructure.

I believe your organization would benefit from our technology for [SPECIFIC_USE_CASE]. We're currently working with enterprise customers on:

• Enterprise AI Governance Platform
• Constitutional Approval Engines for regulated industries  
• Autonomous infrastructure management

Our market research shows a $50B+ addressable opportunity in this space, with customers typically seeing 3-8x ROI in the first year.

I'd love to schedule a 15-minute call to discuss how we might collaborate. Are you available for a brief conversation sometime next week?

Best regards,
Garrett Carroll
Founder, Zero-Human Systems

---

REQUIRED COMPLIANCE FOOTER:

This email was sent to [RECIPIENT_EMAIL] based on [WARM_INTRODUCTION / YOUR_PUBLIC_INFORMATION / INDUSTRY_PUBLICATION].

If you would prefer not to receive similar communications:
  • Reply "STOP" to this email, or
  • Click here to unsubscribe: [UNSUBSCRIBE_LINK]

Zero-Human Systems
[YOUR_BUSINESS_ADDRESS]
[PHONE_NUMBER]

Privacy Policy: [LINK_TO_PRIVACY_POLICY]
Terms of Service: [LINK_TO_TERMS]

EOF

echo "✅ Template created: $TEMPLATE_FILE"
echo ""

echo "📋 VERIFIED RECIPIENT LIST (WITH NOTES)"
echo "═════════════════════════════════════════════════════════════════"
echo ""
echo "⚠️  IMPORTANT: These are TEMPLATES only. You must:"
echo "  1. Find real, verified email addresses (LinkedIn, company sites)"
echo "  2. Get warm introductions where possible"
echo "  3. Customize each email for recipient"
echo "  4. Verify unsubscribe mechanism is working"
echo ""

echo "TIER 1: Warm Introduction Recommended"
echo "─────────────────────────────────────────────────────────────────"
echo "(Wait for LinkedIn/personal connection first)"
echo ""

echo "TIER 2: Research-Based Outreach"
echo "─────────────────────────────────────────────────────────────────"
echo "(Public information + warm opening)"
echo ""

echo "TIER 3: Requires Compliance Review"
echo "─────────────────────────────────────────────────────────────────"
echo "(Legal team approval needed before sending)"
echo ""

echo "═════════════════════════════════════════════════════════════════"
echo "✅ EMAIL CAMPAIGN GENERATION COMPLETE"
echo "═════════════════════════════════════════════════════════════════"
echo ""

echo "📝 GENERATED FILES:"
echo "   • $TEMPLATE_FILE (email template)"
echo ""

echo "🎯 NEXT STEPS:"
echo "   1. ⬇️  Download template: cat $TEMPLATE_FILE"
echo "   2. 🔍 Research verified email addresses (LinkedIn)"
echo "   3. ✅ Get warm introductions where possible"
echo "   4. 📧 Set up unsubscribe link (e.g., via email service)"
echo "   5. ⚖️  Have legal review before sending"
echo "   6. 📤 Send Wave 1 (5 people) first as test"
echo "   7. 📊 Monitor delivery & response rates"
echo "   8. 🚀 Expand to Wave 2 & 3 after validation"
echo ""

echo "💡 BEST PRACTICES:"
echo "   • Send during business hours (9 AM - 4 PM recipient timezone)"
echo "   • Personalize subject line for each recipient"
echo "   • Keep initial email short (3-4 sentences)"
echo "   • Include clear CTA (call to action)"
echo "   • Follow up after 3 days if no response"
echo "   • Stop after 2 follow-ups (respect opt-out)"
echo ""

echo "🔐 SECURITY REMINDERS:"
echo "   • Never include credentials in emails"
echo "   • Use BCC for group sends (not CC)"
echo "   • Test unsubscribe before sending"
echo "   • Monitor for bounce rates"
echo "   • Keep email list fresh (remove bounces)"
echo ""
