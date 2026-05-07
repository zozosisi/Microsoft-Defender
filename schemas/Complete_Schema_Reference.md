# Microsoft Defender XDR - Complete Schema Reference (From Tenant)

> **Tenant:** Crystal Group | **Updated:** 2026-05-07 | **Source:** Advanced Hunting CSV Exports
> **Tables:** 35 exported | **Missing CSV:** CloudProcessEvents (to be exported)

---

## Summary

| Category | Tables | Total Columns |
|----------|--------|---------------|
| Alerts & Behaviors | 4 | 104 |
| Apps & Identities | 10 | 329 |
| Email & Collaboration | 8 | 151 |
| Vulnerability Management | 8 | 76 |
| Cloud Infrastructure | 3 | 73 |
| Exposure Management | 2 | 17 |

---

## JOIN Relationships

```
AlertInfo.AlertId <-> AlertEvidence.AlertId
EmailEvents.NetworkMessageId <-> EmailUrlInfo.NetworkMessageId
EmailEvents.NetworkMessageId <-> EmailAttachmentInfo.NetworkMessageId
EntraIdSignInEvents.AccountObjectId <-> IdentityInfo.AccountObjectId
EntraIdSignInEvents.AccountUpn <-> IdentityLogonEvents.AccountUpn
AlertEvidence.AccountObjectId <-> IdentityInfo.AccountObjectId
EmailEvents.RecipientEmailAddress <-> IdentityInfo.EmailAddress
CloudAppEvents.AccountObjectId <-> IdentityInfo.AccountObjectId
IdentityAccountInfo.AccountUpn <-> IdentityInfo.AccountUpn
```

---

## Missing Tables (Need Export)

| # | Table | KQL Query |
|---|-------|-----------|
| 1 | `CloudProcessEvents` | `CloudProcessEvents \| getschema \| extend TableName = "CloudProcessEvents" \| project TableName, ColumnName, ColumnType, DataType` |

---

## Alerts & Behaviors

### AlertEvidence (43 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `AlertId` | string |
| `Title` | string |
| `Categories` | string |
| `AttackTechniques` | string |
| `ServiceSource` | string |
| `DetectionSource` | string |
| `EntityType` | string |
| `EvidenceRole` | string |
| `EvidenceDirection` | string |
| `FileName` | string |
| `FolderPath` | string |
| `SHA1` | string |
| `SHA256` | string |
| `FileSize` | long |
| `ThreatFamily` | string |
| `RemoteIP` | string |
| `RemoteUrl` | string |
| `AccountName` | string |
| `AccountDomain` | string |
| `AccountSid` | string |
| `AccountObjectId` | string |
| `AccountUpn` | string |
| `DeviceId` | string |
| `DeviceName` | string |
| `LocalIP` | string |
| `NetworkMessageId` | string |
| `EmailSubject` | string |
| `Application` | string |
| `ApplicationId` | int |
| `OAuthApplicationId` | string |
| `ProcessCommandLine` | string |
| `RegistryKey` | string |
| `RegistryValueName` | string |
| `RegistryValueData` | string |
| `AdditionalFields` | string |
| `Severity` | string |
| `CloudResource` | string |
| `CloudPlatform` | string |
| `ResourceType` | string |
| `ResourceID` | string |
| `SubscriptionId` | string |
| `SentinelWorkspaceIds` | string |

### AlertInfo (9 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `AlertId` | string |
| `Title` | string |
| `Category` | string |
| `Severity` | string |
| `ServiceSource` | string |
| `DetectionSource` | string |
| `AttackTechniques` | string |
| `SentinelWorkspaceIds` | string |

### BehaviorEntities (37 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `BehaviorId` | string |
| `ActionType` | string |
| `Categories` | string |
| `ServiceSource` | string |
| `DetectionSource` | string |
| `DataSources` | string |
| `EntityType` | string |
| `EntityRole` | string |
| `DetailedEntityRole` | string |
| `FileName` | string |
| `FolderPath` | string |
| `SHA1` | string |
| `SHA256` | string |
| `FileSize` | long |
| `ThreatFamily` | string |
| `RemoteIP` | string |
| `RemoteUrl` | string |
| `AccountName` | string |
| `AccountDomain` | string |
| `AccountSid` | string |
| `AccountObjectId` | string |
| `AccountUpn` | string |
| `DeviceId` | string |
| `DeviceName` | string |
| `LocalIP` | string |
| `NetworkMessageId` | string |
| `EmailSubject` | string |
| `EmailClusterId` | string |
| `Application` | string |
| `ApplicationId` | int |
| `OAuthApplicationId` | string |
| `ProcessCommandLine` | string |
| `RegistryKey` | string |
| `RegistryValueName` | string |
| `RegistryValueData` | string |
| `AdditionalFields` | string |

### BehaviorInfo (15 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `BehaviorId` | string |
| `ActionType` | string |
| `Description` | string |
| `Categories` | string |
| `AttackTechniques` | string |
| `ServiceSource` | string |
| `DetectionSource` | string |
| `DataSources` | string |
| `DeviceId` | string |
| `AccountUpn` | string |
| `AccountObjectId` | string |
| `StartTime` | datetime |
| `EndTime` | datetime |
| `AdditionalFields` | string |

---

## Apps & Identities

### AADSignInEventsBeta (46 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `Application` | string |
| `ApplicationId` | string |
| `LogonType` | string |
| `EndpointCall` | string |
| `ErrorCode` | int |
| `CorrelationId` | string |
| `SessionId` | string |
| `AccountDisplayName` | string |
| `AccountObjectId` | string |
| `AccountUpn` | string |
| `IsExternalUser` | int |
| `IsGuestUser` | bool |
| `AlternateSignInName` | string |
| `LastPasswordChangeTimestamp` | datetime |
| `ResourceDisplayName` | string |
| `ResourceId` | string |
| `ResourceTenantId` | string |
| `DeviceName` | string |
| `AadDeviceId` | string |
| `OSPlatform` | string |
| `DeviceTrustType` | string |
| `IsManaged` | int |
| `IsCompliant` | int |
| `AuthenticationProcessingDetails` | string |
| `AuthenticationRequirement` | string |
| `TokenIssuerType` | string |
| `RiskLevelAggregated` | int |
| `RiskLevelDuringSignIn` | int |
| `RiskEventTypes` | string |
| `RiskState` | int |
| `UserAgent` | string |
| `ClientAppUsed` | string |
| `Browser` | string |
| `ConditionalAccessPolicies` | string |
| `ConditionalAccessStatus` | int |
| `IPAddress` | string |
| `Country` | string |
| `State` | string |
| `City` | string |
| `Latitude` | string |
| `Longitude` | string |
| `NetworkLocationDetails` | string |
| `RequestId` | string |
| `ReportId` | string |
| `EntraIdDeviceId` | string |

### AADSpnSignInEventsBeta (20 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `Application` | string |
| `ApplicationId` | string |
| `IsManagedIdentity` | bool |
| `ErrorCode` | int |
| `CorrelationId` | string |
| `ServicePrincipalName` | string |
| `ServicePrincipalId` | string |
| `ResourceDisplayName` | string |
| `ResourceId` | string |
| `ResourceTenantId` | string |
| `IPAddress` | string |
| `Country` | string |
| `State` | string |
| `City` | string |
| `Latitude` | string |
| `Longitude` | string |
| `RequestId` | string |
| `ReportId` | string |
| `IsConfidentialClient` | bool |

### CloudAppEvents (36 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `ActionType` | string |
| `Application` | string |
| `ApplicationId` | int |
| `AppInstanceId` | int |
| `AccountObjectId` | string |
| `AccountId` | string |
| `AccountDisplayName` | string |
| `IsAdminOperation` | bool |
| `DeviceType` | string |
| `OSPlatform` | string |
| `IPAddress` | string |
| `IsAnonymousProxy` | bool |
| `CountryCode` | string |
| `City` | string |
| `ISP` | string |
| `UserAgent` | string |
| `ActivityType` | string |
| `ActivityObjects` | dynamic |
| `ObjectName` | string |
| `ObjectType` | string |
| `ObjectId` | string |
| `ReportId` | string |
| `AccountType` | string |
| `IsExternalUser` | bool |
| `IsImpersonated` | bool |
| `IPTags` | dynamic |
| `IPCategory` | string |
| `UserAgentTags` | dynamic |
| `RawEventData` | dynamic |
| `AdditionalFields` | dynamic |
| `SessionData` | dynamic |
| `AuditSource` | string |
| `OAuthAppId` | string |
| `UncommonForUser` | dynamic |
| `LastSeenForUser` | dynamic |

### EntraIdSignInEvents (48 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `Application` | string |
| `ApplicationId` | string |
| `LogonType` | string |
| `EndpointCall` | string |
| `ErrorCode` | int |
| `CorrelationId` | string |
| `SessionId` | string |
| `AccountDisplayName` | string |
| `AccountObjectId` | string |
| `AccountUpn` | string |
| `IsExternalUser` | int |
| `IsGuestUser` | bool |
| `AlternateSignInName` | string |
| `LastPasswordChangeTimestamp` | datetime |
| `ResourceDisplayName` | string |
| `ResourceId` | string |
| `ResourceTenantId` | string |
| `DeviceName` | string |
| `OSPlatform` | string |
| `DeviceTrustType` | string |
| `IsManaged` | int |
| `IsCompliant` | int |
| `AuthenticationProcessingDetails` | string |
| `AuthenticationRequirement` | string |
| `TokenIssuerType` | string |
| `RiskLevelAggregated` | int |
| `RiskLevelDuringSignIn` | int |
| `RiskEventTypes` | string |
| `RiskState` | int |
| `UserAgent` | string |
| `ClientAppUsed` | string |
| `Browser` | string |
| `ConditionalAccessPolicies` | string |
| `ConditionalAccessStatus` | int |
| `IPAddress` | string |
| `Country` | string |
| `State` | string |
| `City` | string |
| `Latitude` | string |
| `Longitude` | string |
| `NetworkLocationDetails` | string |
| `RequestId` | string |
| `ReportId` | string |
| `EntraIdDeviceId` | string |
| `GatewayJA4` | string |
| `UniqueTokenId` | string |
| `IsSignInThroughGlobalSecureAccess` | bool |

### EntraIdSpnSignInEvents (24 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `Application` | string |
| `ApplicationId` | string |
| `IsManagedIdentity` | bool |
| `ErrorCode` | int |
| `CorrelationId` | string |
| `ServicePrincipalName` | string |
| `ServicePrincipalId` | string |
| `ResourceDisplayName` | string |
| `ResourceId` | string |
| `ResourceTenantId` | string |
| `IPAddress` | string |
| `Country` | string |
| `State` | string |
| `City` | string |
| `Latitude` | string |
| `Longitude` | string |
| `RequestId` | string |
| `ReportId` | string |
| `IsConfidentialClient` | bool |
| `GatewayJA4` | string |
| `SessionId` | string |
| `UserAgent` | string |
| `UniqueTokenId` | string |

### GraphAPIAuditEvents (21 columns)

| Column | Type |
|--------|------|
| `IdentityProvider` | string |
| `ApiVersion` | string |
| `ApplicationId` | string |
| `ClientRequestId` | string |
| `OperationId` | string |
| `AccountObjectId` | string |
| `Location` | string |
| `RequestDuration` | string |
| `RequestMethod` | string |
| `Timestamp` | datetime |
| `ResponseStatusCode` | string |
| `Scopes` | string |
| `EntityType` | string |
| `ReportId` | string |
| `RequestUri` | string |
| `UniqueTokenIdentifier` | string |
| `RequestId` | string |
| `IpAddress` | string |
| `ServicePrincipalId` | string |
| `TargetWorkload` | string |
| `ResponseSize` | long |

### IdentityAccountInfo (44 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `ReportId` | string |
| `SourceProviderAccountId` | string |
| `AccountId` | string |
| `IdentityId` | string |
| `IsPrimary` | bool |
| `IdentityLinkType` | string |
| `IdentityLinkReason` | string |
| `IdentityLinkTime` | datetime |
| `IdentityLinkBy` | string |
| `DisplayName` | string |
| `AccountUpn` | string |
| `EmailAddress` | string |
| `CriticalityLevel` | int |
| `Type` | string |
| `GivenName` | string |
| `Surname` | string |
| `EmployeeId` | string |
| `Department` | string |
| `JobTitle` | string |
| `Address` | string |
| `City` | string |
| `Country` | string |
| `Phone` | string |
| `Manager` | string |
| `Sid` | string |
| `AccountStatus` | string |
| `SourceProvider` | string |
| `SourceProviderInstanceId` | string |
| `SourceProviderInstanceDisplayName` | string |
| `AuthenticationMethod` | string |
| `AuthenticationSourceAccountId` | string |
| `EnrolledMfas` | dynamic |
| `LastPasswordChangeTime` | datetime |
| `GroupMembership` | dynamic |
| `AssignedRoles` | dynamic |
| `EligibleRoles` | dynamic |
| `TenantMembershipType` | string |
| `CreatedDateTime` | datetime |
| `DeletedDateTime` | datetime |
| `Tags` | dynamic |
| `SourceProviderRiskLevel` | string |
| `SourceProviderRiskLevelDetails` | string |
| `AdditionalFields` | dynamic |

### IdentityInfo (46 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `ReportId` | string |
| `IdentityId` | string |
| `AccountObjectId` | string |
| `AccountUpn` | string |
| `OnPremSid` | string |
| `OnPremObjectId` | string |
| `AccountDisplayName` | string |
| `AccountName` | string |
| `AccountDomain` | string |
| `CriticalityLevel` | int |
| `Type` | string |
| `DistinguishedName` | string |
| `CloudSid` | string |
| `GivenName` | string |
| `Surname` | string |
| `Department` | string |
| `JobTitle` | string |
| `EmailAddress` | string |
| `SipProxyAddress` | string |
| `Address` | string |
| `City` | string |
| `Country` | string |
| `IsAccountEnabled` | bool |
| `Manager` | string |
| `Phone` | string |
| `CreatedDateTime` | datetime |
| `SourceProvider` | string |
| `ChangeSource` | string |
| `BlastRadius` | string |
| `CompanyName` | string |
| `DeletedDateTime` | datetime |
| `EmployeeId` | string |
| `OtherMailAddresses` | dynamic |
| `RiskLevel` | string |
| `RiskLevelDetails` | string |
| `State` | string |
| `Tags` | dynamic |
| `UserAccountControl` | dynamic |
| `SourceProviders` | dynamic |
| `IdentityEnvironment` | string |
| `PrivilegedEntraPimRoles` | dynamic |
| `AssignedRoles` | dynamic |
| `GroupMembership` | dynamic |
| `RiskScore` | int |
| `RiskScoreUpdateTime` | datetime |

### IdentityLogonEvents (28 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `ActionType` | string |
| `Application` | string |
| `LogonType` | string |
| `Protocol` | string |
| `FailureReason` | string |
| `AccountName` | string |
| `AccountDomain` | string |
| `AccountUpn` | string |
| `AccountSid` | string |
| `AccountObjectId` | string |
| `AccountDisplayName` | string |
| `DeviceName` | string |
| `DeviceType` | string |
| `OSPlatform` | string |
| `IPAddress` | string |
| `Port` | int |
| `DestinationDeviceName` | string |
| `DestinationIPAddress` | string |
| `DestinationPort` | int |
| `TargetDeviceName` | string |
| `TargetAccountDisplayName` | string |
| `Location` | string |
| `ISP` | string |
| `ReportId` | string |
| `AdditionalFields` | dynamic |
| `UncommonForUser` | dynamic |
| `LastSeenForUser` | dynamic |

### OAuthAppInfo (16 columns)

| Column | Type |
|--------|------|
| `ReportId` | string |
| `Timestamp` | datetime |
| `OAuthAppId` | string |
| `ServicePrincipalId` | string |
| `AppName` | string |
| `AddedOnTime` | datetime |
| `LastModifiedTime` | datetime |
| `AppStatus` | string |
| `VerifiedPublisher` | dynamic |
| `PrivilegeLevel` | string |
| `Permissions` | dynamic |
| `IsAdminConsented` | bool |
| `ConsentedUsersCount` | int |
| `AppOrigin` | string |
| `AppOwnerTenantId` | string |
| `LastUsedTime` | datetime |

---

## Email & Collaboration

### EmailAttachmentInfo (16 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `NetworkMessageId` | string |
| `SenderFromAddress` | string |
| `SenderDisplayName` | string |
| `SenderObjectId` | string |
| `RecipientEmailAddress` | string |
| `RecipientObjectId` | string |
| `FileName` | string |
| `FileType` | string |
| `SHA256` | string |
| `FileSize` | long |
| `ThreatTypes` | string |
| `ThreatNames` | string |
| `DetectionMethods` | string |
| `ReportId` | string |
| `FileExtension` | string |

### EmailEvents (49 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `NetworkMessageId` | string |
| `InternetMessageId` | string |
| `SenderMailFromAddress` | string |
| `SenderFromAddress` | string |
| `SenderDisplayName` | string |
| `SenderObjectId` | string |
| `SenderMailFromDomain` | string |
| `SenderFromDomain` | string |
| `SenderIPv4` | string |
| `SenderIPv6` | string |
| `RecipientEmailAddress` | string |
| `RecipientObjectId` | string |
| `Subject` | string |
| `EmailClusterId` | long |
| `EmailDirection` | string |
| `DeliveryAction` | string |
| `DeliveryLocation` | string |
| `ThreatTypes` | string |
| `ThreatNames` | string |
| `DetectionMethods` | string |
| `ConfidenceLevel` | string |
| `BulkComplaintLevel` | int |
| `EmailAction` | string |
| `EmailActionPolicy` | string |
| `EmailActionPolicyGuid` | string |
| `AuthenticationDetails` | string |
| `AttachmentCount` | int |
| `UrlCount` | int |
| `EmailLanguage` | string |
| `Connectors` | string |
| `OrgLevelAction` | string |
| `OrgLevelPolicy` | string |
| `UserLevelAction` | string |
| `UserLevelPolicy` | string |
| `ReportId` | string |
| `AdditionalFields` | string |
| `ExchangeTransportRule` | string |
| `DistributionList` | string |
| `ForwardingInformation` | string |
| `Context` | string |
| `To` | dynamic |
| `Cc` | dynamic |
| `ThreatClassification` | string |
| `RecipientDomain` | string |
| `EmailSize` | long |
| `IsFirstContact` | bool |
| `LatestDeliveryLocation` | string |
| `LatestDeliveryAction` | string |

### EmailPostDeliveryEvents (14 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `NetworkMessageId` | string |
| `InternetMessageId` | string |
| `Action` | string |
| `ActionType` | string |
| `ActionTrigger` | string |
| `ActionResult` | string |
| `RecipientEmailAddress` | string |
| `DeliveryLocation` | string |
| `ThreatTypes` | string |
| `DetectionMethods` | string |
| `ReportId` | string |
| `SenderFromAddress` | string |
| `EmailDirection` | string |

### EmailUrlInfo (8 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `NetworkMessageId` | string |
| `Url` | string |
| `UrlDomain` | string |
| `UrlLocation` | string |
| `ReportId` | string |
| `UrlChainId` | string |
| `UrlChainPosition` | int |

### MessageEvents (29 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `LastEditedTime` | datetime |
| `TeamsMessageId` | string |
| `SenderEmailAddress` | string |
| `SenderDisplayName` | string |
| `SenderObjectId` | string |
| `SenderType` | string |
| `RecipientDetails` | dynamic |
| `IsOwnedThread` | bool |
| `MessageId` | string |
| `ParentMessageId` | string |
| `GroupId` | string |
| `GroupName` | string |
| `ThreadId` | string |
| `ThreadName` | string |
| `ThreadType` | string |
| `ThreadSubType` | string |
| `IsExternalThread` | bool |
| `MessageType` | string |
| `MessageSubtype` | string |
| `MessageVersion` | string |
| `Subject` | string |
| `ThreatTypes` | string |
| `DetectionMethods` | dynamic |
| `ConfidenceLevel` | dynamic |
| `DeliveryAction` | string |
| `DeliveryLocation` | string |
| `ReportId` | string |
| `SafetyTip` | string |

### MessagePostDeliveryEvents (15 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `TeamsMessageId` | string |
| `Action` | string |
| `ActionType` | string |
| `ActionTrigger` | string |
| `ActionResult` | string |
| `SenderEmailAddress` | string |
| `RecipientDetails` | dynamic |
| `IsExternalThread` | bool |
| `ThreatTypes` | string |
| `ConfidenceLevel` | dynamic |
| `DetectionMethods` | dynamic |
| `LatestDeliveryLocation` | string |
| `ReportId` | string |
| `SafetyTip` | string |

### MessageUrlInfo (5 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `TeamsMessageId` | string |
| `Url` | string |
| `UrlDomain` | string |
| `ReportId` | string |

### UrlClickEvents (15 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `Url` | string |
| `ActionType` | string |
| `AccountUpn` | string |
| `Workload` | string |
| `NetworkMessageId` | string |
| `ThreatTypes` | string |
| `DetectionMethods` | string |
| `IPAddress` | string |
| `IsClickedThrough` | bool |
| `UrlChain` | string |
| `ReportId` | string |
| `AppName` | string |
| `AppVersion` | string |
| `SourceId` | string |

---

## Vulnerability Management

### DeviceTvmInfoGathering (6 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `LastSeenTime` | datetime |
| `DeviceId` | string |
| `DeviceName` | string |
| `OSPlatform` | string |
| `AdditionalFields` | dynamic |

### DeviceTvmInfoGatheringKB (5 columns)

| Column | Type |
|--------|------|
| `IgId` | string |
| `FieldName` | string |
| `Description` | string |
| `Categories` | dynamic |
| `DataStructure` | string |

### DeviceTvmSecureConfigurationAssessment (12 columns)

| Column | Type |
|--------|------|
| `DeviceId` | string |
| `DeviceName` | string |
| `OSPlatform` | string |
| `Timestamp` | datetime |
| `ConfigurationId` | string |
| `ConfigurationCategory` | string |
| `ConfigurationSubcategory` | string |
| `ConfigurationImpact` | real |
| `IsCompliant` | bool |
| `IsApplicable` | bool |
| `Context` | dynamic |
| `IsExpectedUserImpact` | bool |

### DeviceTvmSecureConfigurationAssessmentKB (10 columns)

| Column | Type |
|--------|------|
| `ConfigurationId` | string |
| `ConfigurationImpact` | real |
| `ConfigurationName` | string |
| `ConfigurationDescription` | string |
| `RiskDescription` | string |
| `ConfigurationCategory` | string |
| `ConfigurationSubcategory` | string |
| `ConfigurationBenchmarks` | dynamic |
| `Tags` | dynamic |
| `RemediationOptions` | string |

### DeviceTvmSoftwareEvidenceBeta (7 columns)

| Column | Type |
|--------|------|
| `DeviceId` | string |
| `SoftwareVendor` | string |
| `SoftwareName` | string |
| `SoftwareVersion` | string |
| `RegistryPaths` | dynamic |
| `DiskPaths` | dynamic |
| `LastSeenTime` | string |

### DeviceTvmSoftwareInventory (11 columns)

| Column | Type |
|--------|------|
| `DeviceId` | string |
| `DeviceName` | string |
| `OSPlatform` | string |
| `OSVersion` | string |
| `OSArchitecture` | string |
| `SoftwareVendor` | string |
| `SoftwareName` | string |
| `SoftwareVersion` | string |
| `EndOfSupportStatus` | string |
| `EndOfSupportDate` | datetime |
| `ProductCodeCpe` | string |

### DeviceTvmSoftwareVulnerabilities (15 columns)

| Column | Type |
|--------|------|
| `DeviceId` | string |
| `DeviceName` | string |
| `OSPlatform` | string |
| `OSVersion` | string |
| `OSArchitecture` | string |
| `SoftwareVendor` | string |
| `SoftwareName` | string |
| `SoftwareVersion` | string |
| `CveId` | string |
| `VulnerabilitySeverityLevel` | string |
| `RecommendedSecurityUpdate` | string |
| `RecommendedSecurityUpdateId` | string |
| `CveTags` | dynamic |
| `CveMitigationStatus` | string |
| `AadDeviceId` | string |

### DeviceTvmSoftwareVulnerabilitiesKB (10 columns)

| Column | Type |
|--------|------|
| `CveId` | string |
| `CvssScore` | real |
| `CvssVector` | string |
| `CveSupportability` | string |
| `IsExploitAvailable` | bool |
| `VulnerabilitySeverityLevel` | string |
| `LastModifiedTime` | datetime |
| `PublishedDate` | datetime |
| `VulnerabilityDescription` | string |
| `AffectedSoftware` | dynamic |

---

## Cloud Infrastructure

### CloudAuditEvents (18 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `AuditSource` | string |
| `DataSource` | string |
| `ActionType` | string |
| `OperationName` | string |
| `AzureResourceId` | string |
| `AwsResourceName` | string |
| `GcpFullResourceName` | string |
| `Account` | string |
| `IPAddress` | string |
| `IsAnonymousProxy` | bool |
| `CountryCode` | string |
| `City` | string |
| `ISP` | string |
| `UserAgent` | string |
| `RawEventData` | dynamic |
| `AdditionalFields` | dynamic |
| `ReportId` | string |

### CloudDnsEvents (22 columns)

| Column | Type |
|--------|------|
| `Timestamp` | datetime |
| `ReportId` | string |
| `ActionType` | string |
| `AdditionalFields` | dynamic |
| `AzureResourceId` | string |
| `AwsResourceName` | string |
| `GcpFullResourceName` | string |
| `KubernetesResource` | string |
| `KubernetesNamespace` | string |
| `KubernetesPodName` | string |
| `ContainerName` | string |
| `ContainerId` | string |
| `ImageName` | string |
| `ProcessName` | string |
| `ProcessId` | string |
| `EventType` | string |
| `EventSubType` | string |
| `DnsQuery` | string |
| `DnsQueryTypeName` | string |
| `DnsResponseCodeName` | string |
| `DnsNetworkDuration` | long |
| `TransactionIdHex` | string |

### CloudStorageAggregatedEvents (33 columns)

| Column | Type |
|--------|------|
| `DataAggregationStartTime` | datetime |
| `DataAggregationEndTime` | datetime |
| `DataSource` | string |
| `SubscriptionId` | string |
| `ResourceGroup` | string |
| `StorageAccount` | string |
| `StorageContainer` | string |
| `StorageFileShare` | string |
| `ServiceType` | string |
| `IPAddress` | string |
| `UserAgentHeader` | string |
| `OperationNamesList` | dynamic |
| `AuthenticationType` | string |
| `AccountObjectId` | string |
| `AccountTenantId` | string |
| `AccountApplicationId` | string |
| `AccountUpn` | string |
| `AccountType` | string |
| `OperationsCount` | long |
| `SuccessfulOperationsCount` | long |
| `FailedOperationsCount` | long |
| `TotalResponseLength` | long |
| `SuccessfulReadOperations` | long |
| `DistinctGetOperations` | long |
| `AnonymousSuccessfulOperations` | long |
| `HasAnonymousResourceNotFoundFailures` | bool |
| `Md5Hashes` | dynamic |
| `AzureResourceId` | string |
| `Location` | string |
| `Timestamp` | datetime |
| `ReportId` | string |
| `ActionType` | string |
| `AdditionalFields` | dynamic |

---

## Exposure Management

### ExposureGraphEdges (11 columns)

| Column | Type |
|--------|------|
| `EdgeId` | string |
| `EdgeLabel` | string |
| `SourceNodeId` | string |
| `SourceNodeName` | string |
| `SourceNodeLabel` | string |
| `SourceNodeCategories` | dynamic |
| `TargetNodeId` | string |
| `TargetNodeName` | string |
| `TargetNodeLabel` | string |
| `TargetNodeCategories` | dynamic |
| `EdgeProperties` | dynamic |

### ExposureGraphNodes (6 columns)

| Column | Type |
|--------|------|
| `NodeId` | string |
| `NodeLabel` | string |
| `NodeName` | string |
| `Categories` | dynamic |
| `NodeProperties` | dynamic |
| `EntityIds` | dynamic |

---


