# Use Case Story #8: Multi-tenant Department Assistant

**Scenario**: A consulting firm with Legal, Finance, Business, and Academic research teams uses one centralized RAG platform to query domain-specific documents with role-based access control.

---

## Actors & Setup

### Users
1. **Alice** - Senior Legal Counsel
   - Email: `alice@firm.com`
   - Roles: `lawyer`, `admin`
   - Domains: Legal docs

2. **Bob** - Finance Analyst
   - Email: `bob@firm.com`
   - Roles: `analyst`
   - Domains: Finance docs

3. **Carol** - Business Manager
   - Email: `carol@firm.com`
   - Roles: `manager`
   - Domains: Business docs

4. **Dave** - System Admin
   - Email: `dave@firm.com`
   - Roles: `admin`
   - Can manage all domains

### Documents (pre-uploaded by admin)
- `contract_template.pdf` (Legal, uploaded by Alice)
- `Q3_financial_report.docx` (Finance, uploaded by Dave)
- `business_strategy_2026.pdf` (Business, uploaded by Carol)
- `meeting_recording.wav` (Business, transcribed, uploaded by Dave)

---

## Story: A Day in the Life

### **Morning - Alice (Legal) works on contracts**

**1. Alice logs in**
```
URL: http://localhost:5173/login
Input: alice@firm.com / password
Response: JWT token, roles=[lawyer, admin]
Redirect: http://localhost:5173/chats
```

**2. Alice creates a new chat**
```
POST /chats
Response: { "chat_id": "chat-001-alice-legal" }
URL changes to: http://localhost:5173/chats/chat-001-alice-legal/message
```

**3. Alice uploads a contract PDF**
```
POST /upload/file
- file: contract_template.pdf
- file_domain: "legal" (Alice is admin, can set domain)
Response: Uploaded successfully
URL: (stays on /chats/chat-001-alice-legal/message)
FileList updates to show contract_template.pdf
```

**4. Alice asks about the contract in legal mode**
```
POST /chats/chat-001-alice-legal/message
Payload:
{
  "message": "What are the key confidentiality clauses in this contract?",
  "mode": "legal",  ← Legal mode activates legal-specific retrieval
  "format": "markdown",
  "file_id": "file-001"  ← Restrict to uploaded contract
}

Backend flow:
- get_accessible_file_ids(alice@firm.com, roles=[lawyer,admin], domain=legal)
  → Returns [file-001] (her legal doc)
- generate_rag_answer(mode="legal", file_id="file-001", ...)
  → Groq LLM retrieves legal clauses from PDF chunks
  → Returns legal-focused response with citations

Response:
{
  "answer": "## Key Confidentiality Clauses\n\n1. **Section 3.1**: ...",
  "sources": [
    {
      "file_id": "file-001",
      "chunk_id": "chunk-42",
      "text": "Confidentiality: All information disclosed..."
    }
  ]
}

URL changes to: http://localhost:5173/chats/chat-001-alice-legal/message?mode=legal&format=markdown&file_id=file-001
Chat history stored in DB:
- chat_messages.user_messages: [{"content": "What are...", "timestamp": "2026-03-09T09:15:00"}]
- chat_messages.assistant_messages: [{"content": "## Key Confidentiality...", "timestamp": "2026-03-09T09:15:02"}]
```

**5. Alice continues conversation (chat compression happens at message 6)**
```
After 6 messages exchanged:
- compress_chat_history() triggers
- Oldest 4 messages are summarized into chat.summary
- Recent 2 messages stay in chat_messages JSONB arrays
- DB now has:
  - chat.summary: "Contract discussion covered confidentiality, non-compete, and liability clauses..."
  - chat_messages.user_messages: [last 2 user msgs]
  - chat_messages.assistant_messages: [last 2 assistant msgs]
```

---

### **Mid-Morning - Bob (Finance) queries reports**

**1. Bob logs in (separate session)**
```
URL: http://localhost:5173/login
Input: bob@firm.com / password
Response: JWT token, roles=[analyst]
Redirect: http://localhost:5173/chats
```

**2. Bob can see only his chats (Alice's chats are hidden)**
```
GET /chats
- auth: bob@firm.com
Response:
[
  { "chat_id": "chat-002-bob-finance", "title": "Q3 Budget Questions", "created_at": "..." }
]

Note: Alice's chat-001 is NOT returned (filtered by user_email in DB query)
```

**3. Bob creates a finance chat**
```
POST /chats
Response: { "chat_id": "chat-003-bob-finance-new" }
URL: http://localhost:5173/chats/chat-003-bob-finance-new/message
```

**4. Bob tries to access Alice's legal document (should be blocked)**
```
POST /chats/chat-003-bob-finance-new/message
Payload:
{
  "message": "Summarize the contract",
  "file_id": "file-001"  ← Alice's legal doc
}

Backend:
- get_file_by_file_id(db, "file-001")
  → file_record = {domain: "legal", uploaded_by: "alice@firm.com"}
- Check: has_admin_role(bob's roles=[analyst]) → False
- Check: file_record.uploaded_by (alice) == bob -> False
- REJECT: 403 Forbidden "You are not allowed to access this file"

Response: HTTPException 403 - Access Denied
```

**5. Bob queries the finance report (his accessible document)**
```
POST /chats/chat-003-bob-finance-new/message
Payload:
{
  "message": "What was our revenue growth in Q3?",
  "mode": "finance",  ← Finance mode
  "format": "table",
  "file_id": "file-002"  ← Finance report Bob has access to
}

Backend:
- get_accessible_file_ids(bob@firm.com, roles=[analyst], domain=finance)
  → Returns [file-002] (finance domain, anyone can query it)
- generate_rag_answer(mode="finance", file_id="file-002", ...)
  → Retrieves revenue metrics from Q3 report
  → Format="table" → Returns markdown table

Response:
{
  "answer": "| Quarter | Revenue | Growth % |\n|---------|---------|----------|\n| Q2 | $5M | - |\n| Q3 | $6.2M | 24% |",
  "sources": [...]
}

URL: http://localhost:5173/chats/chat-003-bob-finance-new/message?mode=finance&format=table&file_id=file-002
```

---

### **Afternoon - Carol (Business) uploads and queries multimedia**

**1. Carol logs in**
```
URL: http://localhost:5173/login
Input: carol@firm.com / password
Response: JWT token, roles=[manager]
Redirect: http://localhost:5173/chats
```

**2. Carol uploads a business strategy document**
```
POST /upload/file
- file: business_strategy_2026.pdf
- file_domain: "business"
Response: Success
```

**3. Carol creates a business chat**
```
POST /chats
Response: { "chat_id": "chat-004-carol-business" }
URL: http://localhost:5173/chats/chat-004-carol-business/message
```

**4. Carol queries the strategy doc**
```
POST /chats/chat-004-carol-business/message
Payload:
{
  "message": "What are the 3 main strategic pillars for 2026?",
  "mode": "business",
  "format": "markdown"
}

Response:
{
  "answer": "# Strategic Pillars 2026\n\n1. **Digital Transformation**\n   - Cloud migration\n   - AI integration\n\n2. **Market Expansion**\n   - APAC region focus\n   - Partnership strategy\n\n3. **Customer Excellence**\n   - NPS improvement\n   - Support automation",
  "sources": [...]
}
```

---

### **Late Afternoon - Dave (Admin) manages everything**

**1. Dave logs in**
```
Response: JWT token, roles=[admin]
Redirect: http://localhost:5173/chats
```

**2. Dave uploads a meeting recording (transcribed by backend)**
```
POST /upload/file
- file: strategy_meeting_2026.wav
- file_domain: "business"

Backend:
- Transcription service processes audio
- OCR service (if embedded in audio metadata)
- File metadata stored in file table
Response: Success
```

**3. Dave views admin panel (custom admin features)**
```
GET /admin/users
Response: List of all users and their roles
```

**4. Dave queries ANY document across all domains (admin privilege)**
```
POST /chats/{dave's-chat-id}/message
Payload:
{
  "message": "Compare revenue growth (finance) vs strategic goals (business)",
  "mode": "general"  ← No domain restriction for admin
}

Backend:
- get_accessible_file_ids(dave@firm.com, roles=[admin], domain=None)
  → Returns ALL files [file-001 (legal), file-002 (finance), file-003 (business), file-004 (transcribed)]
- generate_rag_answer(mode="general", allowed_file_ids=ALL, ...)
  → Can cross-reference legal, finance, and business docs

Response: Cross-domain insights
```

---

### **Data Isolation & Security Checks**

| User | Sees Chats | Can Query Docs | Mode Restriction |
|------|-----------|----------------|-----------------|
| Alice (lawyer, admin) | Only her chats | Legal + all (admin) | legal, general |
| Bob (analyst) | Only his chats | Finance only | general, finance |
| Carol (manager) | Only her chats | Business + own files | business, general |
| Dave (admin) | All chats (audit) | All docs (all domains) | all modes |

---

### **Database State After Day**

**chats table**
```
id                | user_email     | title                      | summary           | created_at
chat-001-alice    | alice@firm.com | Contract Confidentiality   | "Discussion of..." | 2026-03-09 09:00
chat-002-bob      | bob@firm.com   | Q3 Budget Questions        | NULL              | 2026-03-09 10:00
chat-004-carol    | carol@firm.com | 2026 Strategy Questions    | NULL              | 2026-03-09 14:00
```

**chat_messages table** (one row per chat)
```
id | chat_id        | user_email     | user_messages | assistant_messages | created_at
1  | chat-001-alice | alice@firm.com | [{content: "What are...", timestamp: "..."}, ...] | [{content: "## Key...", timestamp: "..."}, ...] | 2026-03-09 09:00
2  | chat-002-bob   | bob@firm.com   | [{...}] | [{...}] | 2026-03-09 10:00
3  | chat-004-carol | carol@firm.com | [{...}] | [{...}] | 2026-03-09 14:00
```

**files table**
```
file_id | filename                   | domain      | uploaded_by    | created_at
file-001| contract_template.pdf      | legal       | alice@firm.com | 2026-03-09 09:10
file-002| Q3_financial_report.docx   | finance     | dave@firm.com  | 2026-03-09 10:00
file-003| business_strategy_2026.pdf | business    | carol@firm.com | 2026-03-09 14:15
file-004| strategy_meeting_2026.wav  | business    | dave@firm.com  | 2026-03-09 15:30
```

---

## Key Features Demonstrated

✅ **RBAC**: Different users see different docs based on roles + domain  
✅ **Domain Modes**: Legal mode for legal retrieval, Finance mode for finance, etc.  
✅ **Multi-tenant Isolation**: Alice can't see Bob's chats or files  
✅ **Admin Privileges**: Dave can access everything for auditing  
✅ **Chat Persistence**: URL-based navigation, refresh-safe state  
✅ **Chat Compression**: Long conversations summarized to preserve context  
✅ **JSONB Efficiency**: 1 row per chat, not 1 row per message  
✅ **Source Attribution**: Answers linked to exact doc chunks  
✅ **Multimedia Support**: Transcription + OCR integrated  

---

## Testing Workflow

1. Start backend: `.venv/bin/python -m uvicorn app.main:app --reload`
2. Start frontend: `npm run dev`
3. Open 3 browser tabs:
   - Tab 1: Alice at `http://localhost:5173/login`
   - Tab 2: Bob at `http://localhost:5173/login`
   - Tab 3: Dave at `http://localhost:5173/login`
4. Each user uploads docs → queries in their domain → verify isolation
5. Bob tries to access Alice's doc → should be blocked with 403
6. Dave queries cross-domain → should succeed
