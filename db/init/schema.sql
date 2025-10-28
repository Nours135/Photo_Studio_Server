DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS processing_tasks CASCADE;

-- Create ENUM types
CREATE TYPE subscription_tier_type AS ENUM ('FREE', 'PRO');
CREATE TYPE task_status_type AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');

-- 1. User table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100),
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    subscription_tier subscription_tier_type DEFAULT 'FREE' -- FREE/PRO
);

-- 2. processing_tasks
CREATE TABLE processing_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    task_type VARCHAR(50) NOT NULL, -- 'background_removal', 'style_transfer', etc.
    status task_status_type NOT NULL, 
    
    -- input and output
    input_image_s3_key TEXT NOT NULL,
    output_image_s3_key TEXT,
    preview_local_path TEXT,
    
    -- parameters
    parameters JSONB, -- store all processing parameters for reproducibility
    
    -- performance metrics
    processing_time_ms INT, -- processing time
    model_version VARCHAR(50), -- model version for A/B testing
        
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- indices
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_tasks_user_status ON processing_tasks(user_id, status);
CREATE INDEX idx_tasks_created ON processing_tasks(created_at DESC);
CREATE INDEX idx_tasks_type ON processing_tasks(task_type);

