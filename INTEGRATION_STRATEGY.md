# Plutus-Wealthify Integration Strategy

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Wealthify Repository                     │
├─────────────────────────────────────────────────────────────┤
│ Flutter App (Frontend)                                      │
│ ├── User Authentication & Account Management               │
│ ├── Financial Data Aggregation & Visualization            │
│ └── Chat Interface (Plutus Integration)                    │
├─────────────────────────────────────────────────────────────┤
│ Backend API (FastAPI)                                      │
│ ├── User Management Service                                │
│ ├── Account Aggregation Service                           │
│ ├── Database Management                                    │
│ └── Plutus Integration Layer                              │
├─────────────────────────────────────────────────────────────┤
│ services/plutus/ (Git Submodule)                          │
│ └── Plutus AI Brain (Independent Development)             │
└─────────────────────────────────────────────────────────────┘
```

## Recommended Integration: Git Submodules + FastAPI Sub-Application

### Phase 1: Development Integration (Current)
- Add Plutus as git submodule in Wealthify
- Mount Plutus as FastAPI sub-application
- Shared database and user context

### Phase 2: Production Scaling (Future)
- Deploy Plutus as independent service
- API communication between services
- Independent scaling and updates

## Implementation Steps

### Step 1: Setup Git Submodule in Wealthify

```bash
# In Wealthify repository
cd /path/to/wealthify
git submodule add https://github.com/koosha/plutus.git services/plutus
git submodule update --init --recursive

# Create integration layer
mkdir -p services/plutus_integration
```

### Step 2: Create Integration Layer

```python
# services/plutus_integration/plutus_app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

# Add Plutus to Python path
plutus_path = Path(__file__).parent.parent / "plutus" / "src"
sys.path.insert(0, str(plutus_path))

from plutus.agents.orchestrator import PlutusOrchestrator
from plutus.services.context_service import get_context_service

class WealthifyPlutusIntegration:
    def __init__(self, wealthify_db_session):
        self.orchestrator = PlutusOrchestrator()
        self.context_service = get_context_service()
        self.db_session = wealthify_db_session
    
    async def process_user_message(self, user_id: str, message: str, session_id: str = None):
        """Process user message with Wealthify context"""
        
        # Get fresh user data from Wealthify database
        user_context = await self._build_user_context_from_wealthify(user_id)
        
        # Process with Plutus
        response = await self.orchestrator.process_message(
            user_message=message,
            user_id=user_id,
            session_id=session_id,
            external_context=user_context
        )
        
        # Log conversation in Wealthify database
        await self._log_conversation(user_id, message, response)
        
        return response
    
    async def _build_user_context_from_wealthify(self, user_id: str):
        """Build rich user context from Wealthify database"""
        # Query Wealthify database for real-time user data
        # Convert to Plutus-compatible format
        pass
    
    async def _log_conversation(self, user_id: str, message: str, response: dict):
        """Log conversation in Wealthify conversation history"""
        pass

# FastAPI sub-application
def create_plutus_app(wealthify_app: FastAPI, db_session):
    plutus_integration = WealthifyPlutusIntegration(db_session)
    
    @wealthify_app.post("/api/v1/plutus/chat")
    async def chat_with_plutus(request: ChatRequest):
        return await plutus_integration.process_user_message(
            user_id=request.user_id,
            message=request.message,
            session_id=request.session_id
        )
    
    @wealthify_app.get("/api/v1/plutus/context/{user_id}")
    async def get_user_plutus_context(user_id: str):
        context = await plutus_integration.context_service.get_user_context(user_id)
        return context
    
    return wealthify_app
```

### Step 3: Wealthify Main App Integration

```python
# wealthify/main.py
from fastapi import FastAPI
from services.plutus_integration.plutus_app import create_plutus_app
from database import get_db_session

app = FastAPI(title="Wealthify API")

# Mount Plutus integration
app = create_plutus_app(app, get_db_session())

# Existing Wealthify routes
@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: str):
    # Existing user management
    pass

@app.get("/api/v1/accounts/{user_id}")
async def get_user_accounts(user_id: str):
    # Existing account management
    pass
```

## Version Management Strategy

### Plutus Versioning
```bash
# In Plutus repo - create releases
git tag v1.0.0
git push origin v1.0.0

# In Wealthify repo - update to specific version
cd services/plutus
git fetch
git checkout v1.0.0
cd ../..
git add services/plutus
git commit -m "Update Plutus to v1.0.0 - Added retirement planning agent"
```

### Release Workflow
1. **Plutus Development**: Independent feature development in Plutus repo
2. **Version Release**: Tag stable versions in Plutus
3. **Wealthify Integration**: Update submodule to specific Plutus version
4. **Testing**: Run integration tests in Wealthify
5. **Deployment**: Deploy Wealthify with pinned Plutus version

## Database Strategy

### Shared Database Approach (Recommended)
- Plutus uses Wealthify's existing database
- Real-time user context from Wealthify tables
- Plutus adds conversation/AI specific tables

```sql
-- Plutus-specific tables in Wealthify database
CREATE TABLE plutus_conversations (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    session_id VARCHAR(255),
    message TEXT,
    response JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE plutus_user_insights (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    wealth_health_score INTEGER,
    last_analysis JSONB,
    insights JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Deployment Options

### Development Deployment
```yaml
# docker-compose.yml
version: '3.8'
services:
  wealthify:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./services/plutus:/app/services/plutus
```

### Production Deployment Options

#### Option A: Single Service (Simple)
- Deploy Wealthify with Plutus submodule
- Single container/service
- Shared resources

#### Option B: Microservices (Scalable)
```yaml
# Production docker-compose.yml
version: '3.8'
services:
  wealthify-api:
    image: wealthify/api:latest
    ports:
      - "8000:8000"
    environment:
      - PLUTUS_SERVICE_URL=http://plutus-service:8001
  
  plutus-service:
    image: plutus/service:latest
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://...
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

## Migration Path

### Phase 1: Monolith Integration (Immediate)
1. Add Plutus as submodule
2. Direct Python imports
3. Shared database and context
4. Single deployment unit

### Phase 2: Service Separation (6-12 months)
1. Add API layer to Plutus
2. Gradual decoupling
3. Independent deployment pipelines
4. Microservices architecture

### Phase 3: Full Microservices (1+ years)
1. Independent scaling
2. Different tech stacks if needed
3. Advanced API management
4. Service mesh if required

## Benefits of This Approach

### Development Benefits
- ✅ **Independent Development**: Teams can work on Plutus and Wealthify separately
- ✅ **Version Control**: Pin to stable Plutus versions
- ✅ **Testing**: Easy to test Plutus changes in Wealthify context
- ✅ **Clean Separation**: Clear boundaries between financial data management and AI

### Production Benefits
- ✅ **Scalability**: Can scale Plutus independently based on AI workload
- ✅ **Fault Isolation**: Plutus issues don't crash financial data systems
- ✅ **Technology Freedom**: Can optimize Plutus with different tech stack
- ✅ **Team Organization**: Clear ownership and responsibility

### Business Benefits
- ✅ **Faster Innovation**: Rapid AI feature development without affecting core app
- ✅ **Risk Management**: AI experiments don't impact financial data integrity
- ✅ **Vendor Independence**: Could replace Plutus with different AI solution
- ✅ **Compliance**: Easier to audit AI decisions separately from financial data

## Trade-offs Comparison

| Aspect | Monorepo | Submodules | Microservices | Package |
|--------|----------|------------|---------------|---------|
| Development Speed | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ |
| Independent Scaling | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Version Management | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Deployment Complexity | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ |
| Team Independence | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Infrastructure Cost | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐ |

## Recommendation

**Start with Git Submodules** for development and **plan migration to Microservices** for production scale.

This approach provides:
1. **Immediate integration** with minimal complexity
2. **Clear migration path** to microservices
3. **Independent development** cycles
4. **Production flexibility** for future scaling