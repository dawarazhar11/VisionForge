# Database Schema Design

**Database:** PostgreSQL 15
**ORM:** SQLAlchemy 2.0
**Migration Tool:** Alembic

---

## Entity Relationship Diagram

```
┌──────────────┐       ┌────────────────────┐       ┌──────────────────┐
│    Users     │       │ AssemblyProjects   │       │  TrainingJobs    │
├──────────────┤       ├────────────────────┤       ├──────────────────┤
│ id (PK)      │◄──────│ id (PK)            │◄──────│ id (PK)          │
│ email        │ 1   N │ user_id (FK)       │ 1   N │ project_id (FK)  │
│ password_hash│       │ name               │       │ status           │
│ full_name    │       │ description        │       │ progress         │
│ is_active    │       │ file_path          │       │ config_json      │
│ is_superuser │       │ file_size_mb       │       │ dataset_path     │
│ storage_quota│       │ file_type          │       │ metrics_json     │
│ created_at   │       │ status             │       │ error_message    │
│ updated_at   │       │ metadata_json      │       │ created_at       │
└──────────────┘       │ created_at         │       │ started_at       │
                       │ updated_at         │       │ completed_at     │
                       └────────────────────┘       └──────────────────┘
                                                              │ 1
                                                              │
                                                              │ N
                                                     ┌──────────────────┐
                                                     │     Models       │
                                                     ├──────────────────┤
                                                     │ id (PK)          │
                                                     │ job_id (FK)      │
                                                     │ name             │
                                                     │ format           │
                                                     │ file_path        │
                                                     │ file_size_mb     │
                                                     │ accuracy_metrics │
                                                     │ is_active        │
                                                     │ created_at       │
                                                     └──────────────────┘
```

---

## Table Definitions

### 1. `users`
Stores user authentication and profile information.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    storage_quota_mb INTEGER DEFAULT 5000,  -- 5GB default
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
```

**Fields:**
- `id` - UUID primary key
- `email` - Unique email address for login
- `password_hash` - Bcrypt hashed password
- `full_name` - Display name (optional)
- `is_active` - Account status (for soft delete/suspension)
- `is_superuser` - Admin privileges flag
- `storage_quota_mb` - Maximum storage allowed in MB
- `created_at` - Account creation timestamp
- `updated_at` - Last modification timestamp

---

### 2. `assembly_projects`
Stores uploaded 3D assembly files and metadata.

```sql
CREATE TABLE assembly_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    file_size_mb DECIMAL(10, 2) NOT NULL,
    file_type VARCHAR(50) NOT NULL,  -- blend, obj, stl, fbx
    status VARCHAR(50) DEFAULT 'uploaded',  -- uploaded, processing, ready, error
    metadata_json JSONB,  -- Store flexible metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_projects_user_id ON assembly_projects(user_id);
CREATE INDEX idx_projects_status ON assembly_projects(status);
CREATE INDEX idx_projects_created_at ON assembly_projects(created_at DESC);
```

**Fields:**
- `id` - UUID primary key
- `user_id` - Foreign key to `users` table
- `name` - Project name (user-defined)
- `description` - Optional project description
- `file_path` - Storage path to 3D file
- `file_size_mb` - File size in megabytes
- `file_type` - File extension (blend, obj, stl, fbx)
- `status` - Processing status
- `metadata_json` - Flexible JSONB for storing:
  - Number of objects in scene
  - Bounding box dimensions
  - Class mappings
  - Render settings
  - Custom tags
- `created_at` - Upload timestamp
- `updated_at` - Last modification timestamp

**Status Values:**
- `uploaded` - File successfully uploaded
- `processing` - Being validated/processed
- `ready` - Ready for rendering
- `error` - Upload/processing failed

---

### 3. `training_jobs`
Tracks synthetic data generation and model training jobs.

```sql
CREATE TABLE training_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES assembly_projects(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,  -- 0-100%
    stage VARCHAR(100),  -- rendering, training, converting, etc.
    config_json JSONB NOT NULL,  -- Render & training config
    dataset_path VARCHAR(500),
    metrics_json JSONB,  -- Training metrics (mAP, loss, etc.)
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_jobs_project_id ON training_jobs(project_id);
CREATE INDEX idx_jobs_status ON training_jobs(status);
CREATE INDEX idx_jobs_created_at ON training_jobs(created_at DESC);
```

**Fields:**
- `id` - UUID primary key
- `project_id` - Foreign key to `assembly_projects`
- `status` - Job status (pending, running, success, failed, cancelled)
- `progress` - Percentage completion (0-100)
- `stage` - Current processing stage
- `config_json` - JSONB containing:
  ```json
  {
    "render": {
      "num_images": 500,
      "resolution": [640, 640],
      "eevee_samples": 64,
      "train_val_split": 0.8
    },
    "training": {
      "model": "yolov8n",
      "epochs": 100,
      "batch_size": 16,
      "imgsz": 640
    }
  }
  ```
- `dataset_path` - Path to generated dataset
- `metrics_json` - Training results:
  ```json
  {
    "final_map50": 0.85,
    "final_map50_95": 0.72,
    "epochs_trained": 87,
    "training_time_seconds": 1245
  }
  ```
- `error_message` - Error details if failed
- `created_at` - Job creation time
- `started_at` - Execution start time
- `completed_at` - Completion/failure time

**Status Values:**
- `pending` - Queued, waiting for worker
- `running` - Currently processing
- `success` - Completed successfully
- `failed` - Failed with error
- `cancelled` - User cancelled

**Stage Values:**
- `queued`
- `rendering`
- `validating_dataset`
- `training`
- `converting`
- `uploading_model`
- `completed`

---

### 4. `models`
Stores trained model files and metadata.

```sql
CREATE TABLE models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES training_jobs(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    format VARCHAR(50) NOT NULL,  -- tflite, coreml, pt
    file_path VARCHAR(500) NOT NULL,
    file_size_mb DECIMAL(10, 2) NOT NULL,
    accuracy_metrics JSONB,  -- Detailed accuracy metrics
    is_active BOOLEAN DEFAULT TRUE,  -- For model versioning
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_models_job_id ON models(job_id);
CREATE INDEX idx_models_format ON models(format);
CREATE INDEX idx_models_active ON models(is_active);
CREATE INDEX idx_models_created_at ON models(created_at DESC);
```

**Fields:**
- `id` - UUID primary key
- `job_id` - Foreign key to `training_jobs`
- `name` - Model name (e.g., "mechanical_components_v1_tflite")
- `format` - Model format (tflite, coreml, pt)
- `file_path` - Storage path to model file
- `file_size_mb` - Model file size
- `accuracy_metrics` - Detailed metrics:
  ```json
  {
    "map50": 0.85,
    "map50_95": 0.72,
    "precision": 0.88,
    "recall": 0.82,
    "per_class": {
      "small_screw": {"map50": 0.89, "recall": 0.85},
      "large_screw": {"map50": 0.81, "recall": 0.79}
    }
  }
  ```
- `is_active` - Active model flag (for switching)
- `created_at` - Model creation time

---

## SQLAlchemy Models

### models/user.py
```python
from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True, index=True)
    is_superuser = Column(Boolean, default=False)
    storage_quota_mb = Column(Integer, default=5000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projects = relationship("AssemblyProject", back_populates="user", cascade="all, delete-orphan")
```

### models/assembly_project.py
```python
from sqlalchemy import Column, String, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime

from app.database import Base


class AssemblyProject(Base):
    __tablename__ = "assembly_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String)
    file_path = Column(String(500), nullable=False)
    file_size_mb = Column(DECIMAL(10, 2), nullable=False)
    file_type = Column(String(50), nullable=False)
    status = Column(String(50), default="uploaded", index=True)
    metadata_json = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="projects")
    jobs = relationship("TrainingJob", back_populates="project", cascade="all, delete-orphan")
```

### models/training_job.py
```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime

from app.database import Base


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("assembly_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="pending", index=True)
    progress = Column(Integer, default=0)
    stage = Column(String(100))
    config_json = Column(JSONB, nullable=False)
    dataset_path = Column(String(500))
    metrics_json = Column(JSONB)
    error_message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    project = relationship("AssemblyProject", back_populates="jobs")
    models = relationship("Model", back_populates="job", cascade="all, delete-orphan")
```

### models/model.py
```python
from sqlalchemy import Column, String, Boolean, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime

from app.database import Base


class Model(Base):
    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("training_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    format = Column(String(50), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_size_mb = Column(DECIMAL(10, 2), nullable=False)
    accuracy_metrics = Column(JSONB)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    job = relationship("TrainingJob", back_populates="models")
```

---

## Sample Queries

### Get user's projects with job counts
```sql
SELECT
    p.id,
    p.name,
    p.status,
    COUNT(j.id) as job_count,
    MAX(j.created_at) as last_job_at
FROM assembly_projects p
LEFT JOIN training_jobs j ON j.project_id = p.id
WHERE p.user_id = :user_id
GROUP BY p.id, p.name, p.status
ORDER BY p.created_at DESC;
```

### Get job with latest models
```sql
SELECT
    j.id as job_id,
    j.status,
    j.progress,
    j.metrics_json,
    m.id as model_id,
    m.format,
    m.file_size_mb,
    m.accuracy_metrics
FROM training_jobs j
LEFT JOIN models m ON m.job_id = j.id
WHERE j.id = :job_id;
```

### Check user storage usage
```sql
SELECT
    u.id,
    u.email,
    u.storage_quota_mb,
    COALESCE(SUM(p.file_size_mb), 0) as used_storage_mb,
    u.storage_quota_mb - COALESCE(SUM(p.file_size_mb), 0) as remaining_mb
FROM users u
LEFT JOIN assembly_projects p ON p.user_id = u.id
WHERE u.id = :user_id
GROUP BY u.id, u.email, u.storage_quota_mb;
```

---

## Migration Strategy

### Initial Migration (Alembic)
```bash
# Initialize Alembic
cd backend
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Create initial tables"

# Apply migration
alembic upgrade head
```

### Future Migrations
- Use Alembic's `revision --autogenerate` for schema changes
- Always test migrations on dev database first
- Keep migration files in version control
- Document breaking changes in migration docstrings

---

## Next Steps
1. Create SQLAlchemy models in `backend/app/models/`
2. Set up Alembic and create initial migration
3. Implement Pydantic schemas for API validation
4. Build CRUD operations in `backend/app/services/`
