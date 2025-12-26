# CollectIQ User Guide

Quick guide to get started with the loan collection platform.

## Login

1. Go to `http://your-domain:3000`
2. Login with your credentials
3. Default admin: `admin@collectiq.com` / `password123`

## Dashboard

After login, you'll see:
- **Total Cases** - Active collection cases
- **Amount Due** - Total outstanding across all cases
- **Today's Follow-ups** - Cases needing attention today
- **Recent Activity** - Latest communications and updates

## Managing Cases

### View Cases
- Click **Cases** in sidebar
- Use search to find by name, phone, or case number
- Filter by status: Open, In Progress, Promise to Pay, Resolved

### Case Details
Click any case to see:
- Borrower info and contact details
- Loan details (amount, EMI, DPD)
- Communication history
- Payment promises and follow-ups

### Update Case Status
1. Open case details
2. Click status dropdown
3. Select new status
4. Add notes if needed

## Making Calls

### Manual Call (Click-to-Call)
1. Open a case
2. Click the phone icon next to borrower's number
3. Your phone will ring first, then connects to borrower

### AI Voice Call
1. Go to **AI Calls** page
2. Select a case or enter phone number
3. Review borrower context
4. Click **Make AI Call**
5. AI agent handles the conversation automatically

## Sending Messages

### SMS
1. Open case details
2. Click **Send SMS**
3. Select template or type custom message
4. Click Send

### WhatsApp
1. Open case details
2. Click **Send WhatsApp**
3. Select approved template
4. Click Send

## Running Campaigns

### Create Campaign
1. Go to **Campaigns**
2. Click **New Campaign**
3. Configure:
   - Name and type (AI Voice, SMS, WhatsApp)
   - Target cases (filter by DPD, amount, etc.)
   - Schedule and retry settings
4. Click Create

### Monitor Campaign
- View live progress on campaign detail page
- See calls in progress, success rates, outcomes
- Pause/resume as needed

## Data Import (Admin Only)

Admins can bulk import data via **Settings > Data Import**:

| Import Type | Purpose |
|-------------|---------|
| Import Cases | New borrowers + loans + cases |
| Import Borrowers | Add customer contacts |
| Update Loans | Daily portfolio updates (amounts, DPD) |

1. Download CSV template
2. Fill in data
3. Upload and review results

## Key Shortcuts

| Action | How |
|--------|-----|
| Search | `Ctrl/Cmd + K` |
| New Case | Cases page → Create Case |
| Quick Call | Click phone icon on any case |

## Tips

- **Follow-ups**: Set follow-up dates to track promises
- **Notes**: Add notes after every call for history
- **Tags**: Use tags to categorize borrowers
- **Filters**: Save common filters for quick access

## Need Help?

- Check case history for past communications
- Review AI call transcripts for conversation details
- Contact your admin for access issues
