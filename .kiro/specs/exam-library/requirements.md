# Requirements Document

## Introduction

This feature adds an S3-backed exam library to the Exam Mockup Agent, enabling users to browse and select from a catalog of pre-uploaded exam question files instead of (or in addition to) uploading their own XLSX files. Exams are stored as XLSX files in an S3 bucket, and a JSON manifest (`exams/index.json`) describes the available exams with metadata. The home page provides a "Browse Exams" option alongside the existing upload flow.

## Glossary

- **Exam_Library**: The S3-backed collection of pre-uploaded exam XLSX files available for users to select
- **Exam_Manifest**: A JSON file (`exams/index.json`) in the S3 bucket that lists all available exams with metadata
- **Exam_Entry**: A single entry in the Exam_Manifest containing metadata about one exam (id, name, provider, description, file path, question count)
- **S3_Bucket**: The AWS S3 bucket storing both the manifest file and the XLSX exam files
- **Exam_Agent**: The AI-powered agent system that manages exam sessions, presents questions, and provides answer explanations
- **Question_Bank**: The parsed and stored collection of questions extracted from an XLSX file

## Requirements

### Requirement 1

**User Story:** As a certification candidate, I want to browse a catalog of available exams, so that I can select a pre-loaded exam without uploading my own file.

#### Acceptance Criteria

1. WHEN a user visits the home page THEN the Exam_Agent SHALL display a "Browse Exams" option alongside the existing file upload option
2. WHEN a user clicks "Browse Exams" THEN the Exam_Agent SHALL fetch the Exam_Manifest from the S3_Bucket and display a list of available exams
3. WHEN displaying the exam list THEN the Exam_Agent SHALL show each exam's name, provider, description, and question count
4. WHEN a user selects an exam from the catalog THEN the Exam_Agent SHALL download the corresponding XLSX file from S3, parse it, and proceed to mode selection

### Requirement 2

**User Story:** As an administrator, I want to manage the exam catalog through a JSON manifest in S3, so that I can add or remove exams without code changes.

#### Acceptance Criteria

1. THE Exam_Agent SHALL read the exam catalog from an Exam_Manifest file located at `exams/index.json` in the configured S3_Bucket
2. WHEN the Exam_Manifest contains an entry THEN the Exam_Agent SHALL validate that the entry includes id, name, provider, description, file_path, and question_count fields
3. IF the Exam_Manifest is missing or inaccessible THEN the Exam_Agent SHALL display an informative error message and allow the user to fall back to file upload
4. IF an exam's XLSX file referenced in the manifest is missing from S3 THEN the Exam_Agent SHALL display an error for that specific exam and continue showing other available exams

### Requirement 3

**User Story:** As a developer, I want the S3 exam library to be configurable via environment variables, so that I can use different buckets for development and production.

#### Acceptance Criteria

1. THE Exam_Agent SHALL read the S3 bucket name from the `EXAM_LIBRARY_BUCKET` environment variable
2. THE Exam_Agent SHALL read an optional S3 key prefix from the `EXAM_LIBRARY_PREFIX` environment variable (defaulting to `exams/`)
3. IF the `EXAM_LIBRARY_BUCKET` environment variable is not set THEN the Exam_Agent SHALL hide the "Browse Exams" option and only show the file upload flow

### Requirement 4

**User Story:** As a developer, I want the exam manifest to follow a defined JSON schema, so that tooling can validate manifest files.

#### Acceptance Criteria

1. THE Exam_Manifest SHALL be a JSON object with a top-level `exams` array
2. WHEN the Exam_Agent parses the manifest THEN the Exam_Agent SHALL validate each entry contains the fields: id (string), name (string), provider (string), description (string), file_path (string), question_count (integer)
3. WHEN the Exam_Agent serializes an Exam_Entry to JSON and deserializes it back THEN the restored entry SHALL be equivalent to the original entry

### Requirement 5

**User Story:** As a developer, I want the infrastructure to include the S3 bucket for the exam library, so that the deployment is self-contained.

#### Acceptance Criteria

1. WHEN the Terraform infrastructure is applied THEN the deployment SHALL create an S3_Bucket for the Exam_Library with versioning enabled
2. WHEN the ECS task role is configured THEN the role SHALL include read permissions (s3:GetObject, s3:ListBucket) for the Exam_Library S3_Bucket
3. WHEN the ECS task definition is configured THEN the environment SHALL include the `EXAM_LIBRARY_BUCKET` variable pointing to the created S3 bucket

</content>
</invoke>