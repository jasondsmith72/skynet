# Single Input Model: Natural Language to System Action

## Overview

A core design goal of Clarity and ClarityOS is to provide a natural, unified interface where users can express their needs in plain language, and the system intelligently translates these requests into actions. This document demonstrates this "Single Input Model" with practical examples.

## Architecture

The Single Input Model follows this high-level flow:

1. **User Input**: Natural language request from the user
2. **Intent Recognition**: AI parses the request to identify intent
3. **Context Analysis**: System evaluates relevant context
4. **Capability Matching**: Request is matched to available system capabilities
5. **Parameter Resolution**: Required parameters are identified or requested
6. **Execution**: The appropriate actions are executed
7. **Feedback**: Results are presented to the user

## Implementation

The core implementation relies on Clarity's AI-native capabilities:

```clarity
// Core intent processor
service IntentProcessor {
    // Process natural language input
    function process(input: String, context: UserContext) -> ActionResult {
        // Parse input to understand intent
        let intent = ai.understand(input, {
            context: context,
            history: ConversationHistory.recent(10),
            confidenceThreshold: 0.7
        })
        
        // Find capabilities that can fulfill this intent
        let capabilities = CapabilityRegistry.matchIntent(intent)
        
        // If no capabilities found
        if capabilities.isEmpty {
            return ActionResult.notSupported(
                "I don't know how to ${intent.description}",
                suggestedAlternatives: CapabilityRegistry.getSimilar(intent)
            )
        }
        
        // Select best capability
        let selectedCapability = ai.selectBest(capabilities, {
            criteria: [
                "intent match precision",
                "required permissions available",
                "context appropriateness",
                "user preference"
            ]
        })
        
        // Check if we have all required parameters
        let missingParams = selectedCapability.checkRequiredParameters(intent.parameters)
        if !missingParams.isEmpty {
            return ActionResult.needsMoreInfo(
                "I need more information to ${intent.description}",
                missingParameters: missingParams
            )
        }
        
        // Execute the capability
        return selectedCapability.execute(intent.parameters, context)
    }
}
```

## Example Scenarios

### Scenario 1: Document Management

**User Input**: "Find all the client proposals from last quarter and create a summary spreadsheet"

```clarity
// Intent handling for document management
capability DocumentManagement {
    // Find documents capability
    @intentPattern("find ${documentType} from ${timeframe}")
    function findDocuments(params: IntentParameters) -> ActionResult {
        // Extract parameters
        let documentType = params.get("documentType")
        let timeframe = params.get("timeframe")
        
        // Convert natural language timeframe to date range
        let dateRange = TimeframeParser.parse(timeframe)
        
        // Search for documents
        let documents = DocumentStore.search({
            type: ai.mapToDocumentType(documentType),
            created: dateRange,
            orderBy: "created desc"
        })
        
        // Return results
        return ActionResult.success(
            "Found ${documents.count} ${documentType}",
            data: documents
        )
    }
    
    // Create spreadsheet capability
    @intentPattern("create a ${spreadsheetType} spreadsheet [from ${data}]")
    function createSpreadsheet(params: IntentParameters) -> ActionResult {
        // Extract parameters
        let spreadsheetType = params.get("spreadsheetType")
        let data = params.get("data")
        
        // Generate spreadsheet based on intent
        let spreadsheet = ai.generate({
            type: "spreadsheet",
            content: spreadsheetType,
            data: data,
            format: "xlsx"
        })
        
        // Save to user's documents
        let savedPath = FileSystem.saveDocument(spreadsheet, {
            name: "${spreadsheetType} - ${now().format('yyyy-MM-dd')}",
            folder: "Documents/Generated Reports"
        })
        
        // Return results
        return ActionResult.success(
            "Created ${spreadsheetType} spreadsheet",
            data: {
                path: savedPath,
                preview: spreadsheet.preview()
            }
        )
    }
    
    // Combined operation - find and create
    @intentPattern("find ${documentType} from ${timeframe} and create a ${spreadsheetType} spreadsheet")
    function findAndCreateSummary(params: IntentParameters) -> ActionResult {
        // First find the documents
        let findResult = findDocuments(params)
        if !findResult.success {
            return findResult
        }
        
        // Then create a spreadsheet from them
        params.set("data", findResult.data)
        return createSpreadsheet(params)
    }
}
```

### Scenario 2: System Administration for MSPs

**User Input**: "Check if any client servers have less than 10% free disk space and generate a cleanup report"

```clarity
// Intent handling for system administration
capability SystemAdministration {
    // Check disk space capability
    @intentPattern("check [if] [any] ${target} [have|has] less than ${threshold} [free] disk space")
    function checkDiskSpace(params: IntentParameters) -> ActionResult {
        // Extract parameters
        let target = params.get("target") 
        let threshold = params.get("threshold")
        
        // Resolve target to actual systems
        let systems = SystemResolver.resolve(target, {
            currentContext: params.context
        })
        
        // Normalize threshold
        let thresholdValue = ThresholdParser.parse(threshold)
        
        // Check disk space on all systems
        let results = systems.map(system => {
            return {
                system: system.name,
                volumes: system.getVolumes().map(volume => {
                    return {
                        path: volume.path,
                        total: volume.totalSpace,
                        free: volume.freeSpace,
                        percentFree: (volume.freeSpace / volume.totalSpace) * 100,
                        belowThreshold: (volume.freeSpace / volume.totalSpace) * 100 < thresholdValue
                    }
                })
            }
        })
        
        // Filter to only systems with issues
        let issuesSystems = results.filter(result => 
            result.volumes.any(volume => volume.belowThreshold)
        )
        
        // Return results
        return ActionResult.success(
            "${issuesSystems.count} systems have volumes below the ${threshold} threshold",
            data: issuesSystems
        )
    }
    
    // Generate cleanup report capability
    @intentPattern("generate [a] cleanup report [for ${target}]")
    function generateCleanupReport(params: IntentParameters) -> ActionResult {
        // Extract parameters
        let target = params.get("target", params.context.lastResult?.data)
        
        // Generate cleanup recommendations
        let recommendations = ai.analyze({
            systems: target,
            task: "disk space cleanup",
            considerationFactors: [
                "large unnecessary files",
                "temporary files",
                "duplicate content",
                "old backups",
                "unused applications",
                "log rotation"
            ]
        })
        
        // Generate report
        let report = ReportGenerator.create({
            title: "Disk Space Cleanup Recommendations",
            sections: [
                {
                    title: "Executive Summary",
                    content: recommendations.summary
                },
                {
                    title: "System Analysis",
                    content: recommendations.systemAnalysis
                },
                {
                    title: "Recommendations",
                    content: recommendations.details
                },
                {
                    title: "Automation Options",
                    content: recommendations.automationPossibilities
                }
            ],
            format: "pdf"
        })
        
        // Save report
        let savedPath = FileSystem.saveDocument(report, {
            name: "Cleanup Recommendations - ${now().format('yyyy-MM-dd')}",
            folder: "Documents/System Reports"
        })
        
        // Return results
        return ActionResult.success(
            "Generated cleanup report with recommendations for ${target.length} systems",
            data: {
                path: savedPath,
                preview: report.preview()
            }
        )
    }
    
    // Combined operation
    @intentPattern("check [if] [any] ${target} [have|has] less than ${threshold} [free] disk space and generate a cleanup report")
    function checkAndGenerateReport(params: IntentParameters) -> ActionResult {
        // First check disk space
        let checkResult = checkDiskSpace(params)
        if !checkResult.success {
            return checkResult
        }
        
        // Only proceed if issues found
        if checkResult.data.isEmpty {
            return ActionResult.success(
                "No systems found with disk space below ${params.get('threshold')}. No cleanup report needed."
            )
        }
        
        // Generate cleanup report
        params.set("target", checkResult.data)
        return generateCleanupReport(params)
    }
}
```

### Scenario 3: Intelligent Technical Support

**User Input**: "My laptop keeps freezing when I open Photoshop, can you fix it?"

```clarity
// Intent handling for technical support
capability TechnicalSupport {
    // Diagnose issue capability
    @intentPattern("${device} keeps ${problem} when ${condition}")
    function diagnoseIssue(params: IntentParameters) -> ActionResult {
        // Extract parameters
        let device = params.get("device")
        let problem = params.get("problem")
        let condition = params.get("condition")
        
        // Identify the device
        let userDevices = DeviceRegistry.forUser(params.context.user)
        let targetDevice = ai.identifyDevice(device, userDevices)
        
        if !targetDevice {
            return ActionResult.needsMoreInfo(
                "I couldn't identify which ${device} you're referring to. Could you be more specific?",
                missingParameters: ["specificDevice"]
            )
        }
        
        // Gather diagnostic data
        let diagnosticData = DiagnosticSystem.collect(targetDevice, {
            relatedTo: [problem, condition],
            timeframe: TimeSpan.days(7),
            includeSystemLogs: true,
            includeApplicationLogs: true,
            includePerformanceData: true
        })
        
        // Analyze issue
        let analysis = ai.troubleshoot({
            device: targetDevice,
            symptoms: {
                problem: problem,
                trigger: condition
            },
            diagnosticData: diagnosticData,
            knowledgeBase: [
                KnowledgeBase.systemIssues,
                KnowledgeBase.applicationCompatibility,
                KnowledgeBase.recentPatterns
            ]
        })
        
        // Return results
        return ActionResult.success(
            "I've analyzed the issue with your ${targetDevice.name}",
            data: {
                device: targetDevice,
                analysis: analysis,
                potentialSolutions: analysis.recommendations
            }
        )
    }
    
    // Fix issue capability
    @intentPattern("fix ${issue}")
    function fixIssue(params: IntentParameters) -> ActionResult {
        // Extract parameters
        let issue = params.get("issue")
        let analysis = params.get("analysis")
        
        // Select best solution
        let solution = ai.selectBestSolution(analysis.potentialSolutions, {
            criteria: [
                "success probability",
                "implementation simplicity",
                "risk level",
                "user disruption"
            ]
        })
        
        // Check if we need permission
        if solution.requiresPermission {
            return ActionResult.needsPermission(
                "I can fix this by ${solution.description}. Would you like me to proceed?",
                permission: {
                    action: solution,
                    impact: solution.userImpact,
                    alternatives: analysis.alternatives
                }
            )
        }
        
        // Apply solution
        let result = solution.apply()
        
        if result.success {
            return ActionResult.success(
                "I've fixed the issue by ${solution.description}. Please try using ${analysis.trigger} again and let me know if the problem persists."
            )
        } else {
            return ActionResult.partialSuccess(
                "I tried fixing the issue but encountered some problems. ${result.error}",
                nextSteps: analysis.escalationOptions
            )
        }
    }
    
    // Combined operation
    @intentPattern("${device} keeps ${problem} when ${condition}, can you fix it?")
    function diagnoseAndFix(params: IntentParameters) -> ActionResult {
        // First diagnose
        let diagnoseResult = diagnoseIssue(params)
        if !diagnoseResult.success {
            return diagnoseResult
        }
        
        // Then attempt to fix
        params.set("analysis", diagnoseResult.data.analysis)
        return fixIssue(params)
    }
}
```

### Scenario 4: MSP Client Management

**User Input**: "Schedule quarterly security reviews for all enterprise clients and send prep emails one week before each meeting"

```clarity
// Intent handling for client management
capability ClientManagement {
    // Schedule meetings capability
    @intentPattern("schedule ${meetingType} for ${clients}")
    function scheduleMeetings(params: IntentParameters) -> ActionResult {
        // Extract parameters
        let meetingType = params.get("meetingType")
        let clientSelector = params.get("clients")
        
        // Resolve clients
        let clients = ClientRegistry.resolve(clientSelector, {
            currentUser: params.context.user
        })
        
        if clients.isEmpty {
            return ActionResult.failure(
                "No clients matched '${clientSelector}'"
            )
        }
        
        // Determine meeting parameters based on type
        let meetingParams = ai.determineMeetingParameters(meetingType, {
            knowledgeBase: BusinessProcesses.meetings
        })
        
        // Find suitable times for each client
        let scheduledMeetings = clients.map(client => {
            // Find attendees
            let attendees = [
                params.context.user,  // Current user
                client.accountManager,
                client.primaryContact
            ]
            
            // Find times that work for everyone
            let availableTimes = CalendarSystem.findMutualAvailability(
                attendees,
                {
                    timeframe: meetingParams.timeframe,
                    duration: meetingParams.duration,
                    frequency: meetingParams.frequency
                }
            )
            
            if availableTimes.isEmpty {
                return {
                    client: client,
                    scheduled: false,
                    reason: "No mutual availability found"
                }
            }
            
            // Schedule the best time
            let scheduledMeeting = CalendarSystem.createMeeting({
                title: "${meetingParams.title} - ${client.name}",
                time: availableTimes.optimal(),
                duration: meetingParams.duration,
                attendees: attendees,
                location: meetingParams.location,
                notes: meetingParams.description
            })
            
            return {
                client: client,
                scheduled: true,
                meeting: scheduledMeeting
            }
        })
        
        // Return results
        let successCount = scheduledMeetings.count(m => m.scheduled)
        return ActionResult.success(
            "Scheduled ${successCount} out of ${clients.count} ${meetingType} meetings",
            data: scheduledMeetings
        )
    }
    
    // Send emails capability
    @intentPattern("send ${emailType} [emails] to ${recipients} ${timing}")
    function sendEmails(params: IntentParameters) -> ActionResult {
        // Extract parameters
        let emailType = params.get("emailType")
        let recipients = params.get("recipients")
        let timing = params.get("timing")
        
        // Parse timing to determine when to send
        let schedule = TimingParser.parse(timing)
        
        // Generate email template based on type
        let emailTemplate = ai.generateEmailTemplate(emailType, {
            businessContext: params.context.organization,
            tone: "professional",
            length: "concise"
        })
        
        // Schedule emails
        let scheduledEmails = recipients.map(recipient => {
            // Determine the right send time
            let sendTime = schedule.calculateFor(recipient)
            
            // Personalize email for this recipient
            let personalizedEmail = emailTemplate.personalize({
                recipient: recipient,
                sender: params.context.user,
                customFields: recipient.relevantData
            })
            
            // Schedule the email
            let scheduled = EmailSystem.schedule({
                to: recipient.email,
                from: params.context.user.email,
                subject: personalizedEmail.subject,
                body: personalizedEmail.body,
                sendAt: sendTime
            })
            
            return {
                recipient: recipient,
                scheduled: scheduled.success,
                sendTime: sendTime,
                emailId: scheduled.id
            }
        })
        
        // Return results
        let successCount = scheduledEmails.count(e => e.scheduled)
        return ActionResult.success(
            "Scheduled ${successCount} ${emailType} emails to be sent ${timing}",
            data: scheduledEmails
        )
    }
    
    // Combined operation
    @intentPattern("schedule ${meetingType} for ${clients} and send ${emailType} emails ${timing}")
    function scheduleMeetingsWithEmails(params: IntentParameters) -> ActionResult {
        // First schedule meetings
        let meetingsResult = scheduleMeetings(params)
        if !meetingsResult.success {
            return meetingsResult
        }
        
        // Then schedule prep emails
        let scheduledMeetings = meetingsResult.data
        params.set("recipients", scheduledMeetings
            .filter(m => m.scheduled)
            .map(m => m.client.primaryContact))
        
        return sendEmails(params)
    }
}
```

## Extending the System

One of the most powerful aspects of the Single Input Model is its extensibility. New capabilities can be added to the system without changing the core interface:

```clarity
// Register a new capability
function registerNewCapability() {
    // Define a new capability
    capability NetworkDiagnostics {
        @intentPattern("check network connectivity between ${sourceDevice} and ${targetDevice}")
        function checkConnectivity(params: IntentParameters) -> ActionResult {
            // Implementation details...
        }
        
        @intentPattern("optimize network for ${application}")
        function optimizeForApplication(params: IntentParameters) -> ActionResult {
            // Implementation details...
        }
    }
    
    // Register with the system
    CapabilityRegistry.register(NetworkDiagnostics)
}
```

## Benefits for MSPs

The Single Input Model provides several key advantages for MSPs:

1. **Reduced Training Requirements**: Staff can interact with systems using natural language rather than learning specific commands or navigation paths
2. **Consistent Operations**: The AI ensures that actions follow best practices and company policies
3. **Faster Problem Resolution**: Complex multi-step processes can be executed with a single request
4. **Knowledge Capture**: The system embeds organizational knowledge and processes into capabilities
5. **Scalability**: Junior technicians can perform complex tasks guided by the AI
6. **Client Self-Service**: Appropriately permissioned capabilities can be exposed to clients for self-service
7. **Continuous Improvement**: The system learns from usage patterns to enhance its understanding and capabilities

## Implementation Considerations

When implementing the Single Input Model for MSPs:

1. **Permission Boundaries**: Carefully define permission boundaries for capabilities
2. **Verification Steps**: Include verification steps for high-impact operations
3. **Training Data**: Provide domain-specific training data for intent recognition
4. **Fallback Mechanisms**: Implement graceful fallbacks when intents cannot be processed
5. **Audit Logging**: Maintain comprehensive logs of all actions performed
6. **Human Supervision**: Enable easy transitions to human support when needed
7. **Multi-tenant Design**: Ensure strict separation between different client environments

## Conclusion

The Single Input Model represents a fundamental shift in how MSPs can interact with their systems. By providing a natural language interface backed by AI-powered intent recognition and execution, Clarity enables MSPs to streamline operations, reduce training costs, and improve service quality. The examples provided demonstrate how complex multi-step processes can be initiated with simple natural language requests, making advanced capabilities accessible to both technical and non-technical users.