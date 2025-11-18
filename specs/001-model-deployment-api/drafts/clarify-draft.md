# Clarify Draft

## Resolved Issues

### Issue 1: Audio Processing Specifications (FR-002)

**Original (모호함)**: System MUST provide audio preprocessing pipeline supporting WAV, MP3, and M4A formats up to 30MB

**Resolution (명확함)**: System MUST provide audio preprocessing pipeline supporting WAV, MP3, and M4A formats up to 30MB with the following specific requirements:
- **Format Preservation**: Maintain original sample rate and channels where possible to preserve research accuracy
- **Maximum Duration**: Strict 10-second maximum limit with clear error messages for exceeded files
- **Validation**: Strict validation with detailed error codes for format corruption, sample rate issues, and integrity problems
- **File Size**: Hard limit of 30MB with immediate rejection and specific error message

**Rationale**: This approach balances research accuracy needs with practical system constraints while providing clear feedback for troubleshooting.

**Impact**: Changes FR-002 acceptance criteria to include specific validation rules and error handling requirements.

### Issue 2: WebSocket Streaming Clarification (FR-004)

**Original (모호함)**: System MUST support real-time audio streaming through WebSocket connections

**Resolution (명확함)**: System MUST support audio file transmission through WebSocket connections with the following clarification:
- **Chunk Size**: Use 1-second audio chunks for transmission
- **Prediction Timing**: Emotion predictions are returned only after the complete audio file has been received and sent to the model
- **Connection Management**: Stateless connections with immediate retry capability for network interruptions
- **No Session Persistence**: Each WebSocket connection is independent with no state maintenance between connections

**Rationale**: This clarifies that the WebSocket is used for efficient file transfer rather than true real-time streaming, which simplifies implementation while maintaining good user experience.

**Impact**: Updates FR-004 and WebSocket acceptance scenarios to reflect file-transfer-based approach.

### Issue 3: SageMaker Infrastructure Configuration (FR-001, FR-006)

**Original (모호함)**: System MUST deploy to AWS SageMaker; System MUST implement auto-scaling from 0 to 50 concurrent requests

**Resolution (명확함)**: System MUST deploy to AWS SageMaker Serverless Inference with the following configuration:
- **Deployment Model**: Use SageMaker Serverless for cost optimization in research workloads
- **Scaling**: Automatic scaling from 0 to maximum concurrent requests based on demand
- **Instance Type**: Configure appropriate memory and compute based on model requirements (ml.m5.large or similar)
- **Cold Start Tolerance**: Accept 30-second cold start time as acceptable for serverless deployment

**Rationale**: Serverless inference is ideal for research workloads with variable usage patterns, providing cost savings while maintaining required performance.

**Impact**: Updates FR-001 deployment strategy and FR-006 scaling requirements to specify serverless configuration.

## Affected Sections

### specification.md
- **FR-002**: Enhanced with specific audio processing requirements and validation rules
- **FR-004**: Clarified WebSocket behavior as file transfer with delayed prediction
- **FR-001**: Updated to specify SageMaker Serverless deployment
- **FR-006**: Modified to reflect serverless auto-scaling characteristics
- **Acceptance Scenarios**: Updated WebSocket scenarios to match clarified behavior

## New Acceptance Criteria

### Audio Processing Additions
- [ ] System validates audio file integrity and returns specific error codes (INVALID_FORMAT, CORRUPTED_FILE, EXCEEDS_DURATION, EXCEEDS_SIZE)
- [ ] System preserves original audio sample rate and channels when processing
- [ ] System rejects audio files longer than 30 seconds with clear duration limit message
- [ ] System processes audio files under 30MB within specified time constraints

### WebSocket Clarifications
- [ ] WebSocket connections transmit audio in 1-second chunks
- [ ] System returns emotion predictions only after complete audio file receipt
- [ ] WebSocket connections support immediate retry after connection failures
- [ ] System handles multiple concurrent WebSocket connections independently

### Infrastructure Specifics
- [ ] System deploys model using SageMaker Serverless Inference configuration
- [ ] System scales automatically from 0 to maximum capacity based on request demand
- [ ] System accepts 30-second cold start time for serverless endpoint initialization
- [ ] System maintains 99.9% uptime accounting for serverless scaling characteristics

## Technical Decisions

### Audio Processing
- **Sample Rate**: Preserve original rates (e.g., 44.1kHz, 48kHz) rather than standardizing to 16kHz
- **Channels**: Maintain stereo/mono configuration from input files
- **Validation**: Comprehensive validation using ffmpeg/librosa for format detection and integrity checking
- **Error Codes**: Implement specific error codes for different failure scenarios

### Streaming Architecture
- **Protocol**: WebSocket for efficient binary file transfer
- **Buffering**: Client-side buffering to ensure smooth transmission
- **Stateless Design**: No server-side session state to maintain simplicity
- **Connection Management**: Immediate retry pattern with exponential backoff

### Cost Optimization
- **Serverless First**: Prioritize SageMaker Serverless for research usage patterns
- **Automatic Scaling**: Leverage AWS auto-scaling for optimal cost-performance ratio
- **Cold Start Acceptance**: Accept longer startup times for cost savings
- **Monitoring**: Implement CloudWatch alerts for cost and performance optimization

## Open Questions to Remove
- What sample rate should audio be resampled to before sending to the model?
- What chunk size should be used for audio streaming?
- Should predictions be returned for every chunk or only when speech is detected?
- Which SageMaker instance types should be used?
- What triggers auto-scaling and what are the cooldown periods?

## Updated Requirements

### FR-002 (Enhanced): Audio Processing Pipeline
System MUST provide audio preprocessing pipeline supporting WAV, MP3, and M4A formats up to 30MB with original sample rate and channel preservation, strict 30-second duration limits, and comprehensive validation with detailed error reporting for corrupted files.

### FR-004 (Clarified): Audio File Transfer via WebSocket
System MUST support audio file transmission through WebSocket connections using 1-second chunks, with emotion predictions returned only after complete file receipt, supporting stateless connections with immediate retry capability.

### FR-001 (Updated): Serverless Model Deployment
System MUST deploy firdhokk/speech-emotion-recognition-with-openai-whisper-large-v3 model to AWS SageMaker Serverless Inference with automatic scaling and 30-second cold start tolerance.

### FR-006 (Updated): Serverless Auto-Scaling
System MUST implement serverless auto-scaling from 0 to maximum concurrent requests with AWS-managed scaling policies and cost-optimized resource utilization.