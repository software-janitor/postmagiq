"""SQLModel table definitions.

This module exports all SQLModel table classes and their Create/Read variants.
All primary keys use UUID for security and scalability.

Model Categories:
- Core: User, Platform, Goal, Chapter, Post
- Voice: WritingSample, VoiceProfile
- Image: ImagePrompt, ImageConfigSet, ImageScene, ImagePose, ImageOutfit, ImageProp
- Character: CharacterTemplate, OutfitPart, Outfit, Character
- Workflow: WorkflowRun, WorkflowOutput, WorkflowSession, WorkflowStateMetric, WorkflowPersona
- Analytics: AnalyticsImport, PostMetric, DailyMetric, FollowerMetric
"""

# Base class
from runner.db.models.base import UUIDModel, TimestampMixin

# Multi-tenancy models
from runner.db.models.workspace import Workspace, WorkspaceCreate, WorkspaceRead
from runner.db.models.membership import (
    WorkspaceMembership, WorkspaceMembershipCreate, WorkspaceMembershipRead,
    WorkspaceRole, InviteStatus,
)

# Core models
from runner.db.models.user import User, UserCreate, UserRead, UserRole, PasswordResetToken
from runner.db.models.session import ActiveSession, ActiveSessionCreate, ActiveSessionRead
from runner.db.models.platform import Platform, PlatformCreate, PlatformRead
from runner.db.models.content import (
    Goal, GoalCreate, GoalRead,
    Chapter, ChapterCreate, ChapterRead,
    Post, PostCreate, PostRead,
)

# Voice models
from runner.db.models.voice import (
    WritingSample, WritingSampleCreate, WritingSampleRead,
    VoiceProfile, VoiceProfileCreate, VoiceProfileRead,
)

# Workflow models
from runner.db.models.workflow import (
    WorkflowRun, WorkflowRunCreate, WorkflowRunRead,
    WorkflowOutput, WorkflowOutputCreate,
    WorkflowSession, WorkflowSessionCreate,
    WorkflowStateMetric, WorkflowStateMetricCreate,
    WorkflowPersona, WorkflowPersonaCreate, WorkflowPersonaRead,
)

# Image models
from runner.db.models.image import (
    ImagePrompt, ImagePromptCreate, ImagePromptRead,
    ImageConfigSet, ImageConfigSetCreate,
    ImageScene, ImageSceneCreate,
    ImagePose, ImagePoseCreate,
    ImageOutfit, ImageOutfitCreate,
    ImageProp, ImagePropCreate,
    ImageCharacter, ImageCharacterCreate,
)

# Character models
from runner.db.models.character import (
    CharacterTemplate, CharacterTemplateCreate,
    OutfitPart, OutfitPartCreate,
    Outfit, OutfitCreate,
    OutfitItem, OutfitItemCreate,
    Character, CharacterCreate,
    CharacterOutfit, CharacterOutfitCreate,
    Sentiment, SentimentCreate,
    SceneCharacter, SceneCharacterCreate,
    PropCategory, PropCategoryCreate,
    ScenePropRule, ScenePropRuleCreate,
    ContextPropRule, ContextPropRuleCreate,
)

# Analytics models
from runner.db.models.analytics import (
    AnalyticsImport, AnalyticsImportCreate,
    PostMetric, PostMetricCreate,
    DailyMetric, DailyMetricCreate,
    FollowerMetric, FollowerMetricCreate,
    AudienceDemographic, AudienceDemographicCreate,
    PostDemographic, PostDemographicCreate,
)

# History models
from runner.db.models.history import (
    RunRecord, RunRecordCreate, RunRecordRead,
    InvocationRecord, InvocationRecordCreate,
    AuditScoreRecord, AuditScoreRecordCreate,
    PostIterationRecord, PostIterationRecordCreate,
)

# Subscription models
from runner.db.models.subscription import (
    BillingPeriod, SubscriptionStatus, ReservationStatus,
    SubscriptionTier, SubscriptionTierRead,
    AccountSubscription, AccountSubscriptionRead,
    UsageTracking, UsageTrackingRead,
    CreditReservation, CreditReservationRead,
    TierFeature, TierFeatureRead,
)

# Billing models
from runner.db.models.billing import (
    BillingEventType, InvoiceStatus, PaymentMethodType,
    BillingEvent, BillingEventRead,
    Invoice, InvoiceRead, InvoiceCreate,
    PaymentMethod, PaymentMethodRead,
)

# Approval models (Phase 6)
from runner.db.models.approval import (
    PostPriority, ApprovalStatus, AssignmentAction,
    PostAssignmentHistory, PostAssignmentHistoryBase,
    ApprovalStage, ApprovalStageBase, ApprovalStageCreate,
    ApprovalRequest, ApprovalRequestBase, ApprovalRequestCreate,
    ApprovalComment, ApprovalCommentBase, ApprovalCommentCreate,
)

# Notification models (Phase 7)
from runner.db.models.notification import (
    NotificationChannelType, NotificationType, NotificationPriority,
    NotificationChannel, NotificationChannelCreate, NotificationChannelRead,
    NotificationPreference, NotificationPreferenceCreate, NotificationPreferenceRead,
    Notification, NotificationCreate, NotificationRead,
)

# API Key and Webhook models (Phase 8)
from runner.db.models.api_key import (
    APIKeyStatus, WebhookStatus, DeliveryStatus, WebhookEventType,
    APIKey, APIKeyCreate, APIKeyRead,
    Webhook, WebhookCreate, WebhookRead,
    WebhookDelivery, WebhookDeliveryCreate, WebhookDeliveryRead,
)

# Whitelabel models (Phase 10)
from runner.db.models.whitelabel import (
    AssetType, DomainVerificationStatus,
    WhitelabelConfig, WhitelabelConfigCreate, WhitelabelConfigRead,
    WhitelabelAsset, WhitelabelAssetCreate, WhitelabelAssetRead,
)

# Audit models (Phase 10)
from runner.db.models.audit import (
    AuditAction,
    AuditLog, AuditLogCreate, AuditLogRead,
)

# Workflow Config models (Phase 11)
from runner.db.models.workflow_config import (
    WorkflowEnvironment,
    WorkflowConfig, WorkflowConfigCreate, WorkflowConfigRead, WorkflowConfigUpdate,
)

# Market Intelligence models (Phase 13)
from runner.db.models.market_intelligence import (
    EmbeddingSourceType, ResearchSourceType, ContentStatus, ModerationStatus, ModerationType,
    Embedding, EmbeddingCreate,
    AudienceSegment, AudienceSegmentCreate, AudienceSegmentRead,
    CalibratedVoice, CalibratedVoiceCreate, CalibratedVoiceRead,
    NicheVocabulary, NicheVocabularyCreate, NicheVocabularyRead,
    ResearchSource, ResearchSourceCreate, ResearchSourceRead,
    GeneratedContent, GeneratedContentCreate, GeneratedContentRead,
    ContentModeration, ContentModerationCreate, ContentModerationRead,
)

__all__ = [
    # Base
    "UUIDModel",
    "TimestampMixin",
    # Multi-tenancy
    "Workspace", "WorkspaceCreate", "WorkspaceRead",
    "WorkspaceMembership", "WorkspaceMembershipCreate", "WorkspaceMembershipRead",
    "WorkspaceRole", "InviteStatus",
    # User
    "User", "UserCreate", "UserRead", "UserRole", "PasswordResetToken",
    # Session
    "ActiveSession", "ActiveSessionCreate", "ActiveSessionRead",
    # Platform
    "Platform", "PlatformCreate", "PlatformRead",
    # Content
    "Goal", "GoalCreate", "GoalRead",
    "Chapter", "ChapterCreate", "ChapterRead",
    "Post", "PostCreate", "PostRead",
    # Voice
    "WritingSample", "WritingSampleCreate", "WritingSampleRead",
    "VoiceProfile", "VoiceProfileCreate", "VoiceProfileRead",
    # Workflow
    "WorkflowRun", "WorkflowRunCreate", "WorkflowRunRead",
    "WorkflowOutput", "WorkflowOutputCreate",
    "WorkflowSession", "WorkflowSessionCreate",
    "WorkflowStateMetric", "WorkflowStateMetricCreate",
    "WorkflowPersona", "WorkflowPersonaCreate", "WorkflowPersonaRead",
    # Image
    "ImagePrompt", "ImagePromptCreate", "ImagePromptRead",
    "ImageConfigSet", "ImageConfigSetCreate",
    "ImageScene", "ImageSceneCreate",
    "ImagePose", "ImagePoseCreate",
    "ImageOutfit", "ImageOutfitCreate",
    "ImageProp", "ImagePropCreate",
    "ImageCharacter", "ImageCharacterCreate",
    # Character
    "CharacterTemplate", "CharacterTemplateCreate",
    "OutfitPart", "OutfitPartCreate",
    "Outfit", "OutfitCreate",
    "OutfitItem", "OutfitItemCreate",
    "Character", "CharacterCreate",
    "CharacterOutfit", "CharacterOutfitCreate",
    "Sentiment", "SentimentCreate",
    "SceneCharacter", "SceneCharacterCreate",
    "PropCategory", "PropCategoryCreate",
    "ScenePropRule", "ScenePropRuleCreate",
    "ContextPropRule", "ContextPropRuleCreate",
    # Analytics
    "AnalyticsImport", "AnalyticsImportCreate",
    "PostMetric", "PostMetricCreate",
    "DailyMetric", "DailyMetricCreate",
    "FollowerMetric", "FollowerMetricCreate",
    "AudienceDemographic", "AudienceDemographicCreate",
    "PostDemographic", "PostDemographicCreate",
    # History
    "RunRecord", "RunRecordCreate", "RunRecordRead",
    "InvocationRecord", "InvocationRecordCreate",
    "AuditScoreRecord", "AuditScoreRecordCreate",
    "PostIterationRecord", "PostIterationRecordCreate",
    # Subscription
    "BillingPeriod", "SubscriptionStatus", "ReservationStatus",
    "SubscriptionTier", "SubscriptionTierRead",
    "AccountSubscription", "AccountSubscriptionRead",
    "UsageTracking", "UsageTrackingRead",
    "CreditReservation", "CreditReservationRead",
    "TierFeature", "TierFeatureRead",
    # Billing
    "BillingEventType", "InvoiceStatus", "PaymentMethodType",
    "BillingEvent", "BillingEventRead",
    "Invoice", "InvoiceRead", "InvoiceCreate",
    "PaymentMethod", "PaymentMethodRead",
    # Approval (Phase 6)
    "PostPriority", "ApprovalStatus", "AssignmentAction",
    "PostAssignmentHistory", "PostAssignmentHistoryBase",
    "ApprovalStage", "ApprovalStageBase", "ApprovalStageCreate",
    "ApprovalRequest", "ApprovalRequestBase", "ApprovalRequestCreate",
    "ApprovalComment", "ApprovalCommentBase", "ApprovalCommentCreate",
    # Notification (Phase 7)
    "NotificationChannelType", "NotificationType", "NotificationPriority",
    "NotificationChannel", "NotificationChannelCreate", "NotificationChannelRead",
    "NotificationPreference", "NotificationPreferenceCreate", "NotificationPreferenceRead",
    "Notification", "NotificationCreate", "NotificationRead",
    # API Key & Webhook (Phase 8)
    "APIKeyStatus", "WebhookStatus", "DeliveryStatus", "WebhookEventType",
    "APIKey", "APIKeyCreate", "APIKeyRead",
    "Webhook", "WebhookCreate", "WebhookRead",
    "WebhookDelivery", "WebhookDeliveryCreate", "WebhookDeliveryRead",
    # Whitelabel (Phase 10)
    "AssetType", "DomainVerificationStatus",
    "WhitelabelConfig", "WhitelabelConfigCreate", "WhitelabelConfigRead",
    "WhitelabelAsset", "WhitelabelAssetCreate", "WhitelabelAssetRead",
    # Audit (Phase 10)
    "AuditAction",
    "AuditLog", "AuditLogCreate", "AuditLogRead",
    # Workflow Config (Phase 11)
    "WorkflowEnvironment",
    "WorkflowConfig", "WorkflowConfigCreate", "WorkflowConfigRead", "WorkflowConfigUpdate",
    # Market Intelligence (Phase 13)
    "EmbeddingSourceType", "ResearchSourceType", "ContentStatus", "ModerationStatus", "ModerationType",
    "Embedding", "EmbeddingCreate",
    "AudienceSegment", "AudienceSegmentCreate", "AudienceSegmentRead",
    "CalibratedVoice", "CalibratedVoiceCreate", "CalibratedVoiceRead",
    "NicheVocabulary", "NicheVocabularyCreate", "NicheVocabularyRead",
    "ResearchSource", "ResearchSourceCreate", "ResearchSourceRead",
    "GeneratedContent", "GeneratedContentCreate", "GeneratedContentRead",
    "ContentModeration", "ContentModerationCreate", "ContentModerationRead",
]
