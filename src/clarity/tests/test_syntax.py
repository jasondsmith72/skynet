import unittest
from ..compiler.parser import parse
from ..compiler.ast import (
    Program,
    FunctionDeclaration,
    # TryCatchStatement,
    # BlockStatement,
    # IfStatement,
    # ThrowStatement,
    # ReturnStatement,
    # CallExpression,
    # BinaryExpression,
    # IdentifierExpression,
    # AIExpression,
    # AgentDeclaration,
    # ServiceDeclaration,
    # Expression,
)


class TestSyntax(unittest.TestCase):
    """Tests for advanced syntax constructs in the Clarity language."""

    def parse(self, source: str) -> Program:
        """Helper method to parse source code into an AST."""
        return parse(source)

    def assertNodeType(self, node, expected_type):
        """Assert that a node is of a specific type."""
        self.assertIsInstance(node, expected_type)

    # def test_error_handling_and_guards(self):
    #     """Test parsing of try-catch, throw, and guard statements."""
    #     source = """
    #     function processFile(path) throws FileNotFoundError, JsonParseError {
    #         try {
    #             let file = open(path)
    #             let data = JSON.parse(file)
    #             return data
    #         } catch FileNotFoundError {
    #             log.error("File not found: " + path)
    #         } catch JsonParseError as message {
    #             log.error("Failed to parse JSON: " + message)
    #         }
    #     }

    #     function divide(a, b) throws DivisionByZeroError {
    #         if b == 0 {
    #             throw DivisionByZeroError("Cannot divide by zero")
    #         }
    #         return a / b
    #     }

    #     function processPayment(amount) throws {
    #         guard amount > 0 else {
    #             throw InvalidArgumentError("Amount must be positive")
    #         }

    #         guard amount < 10000 else {
    #             throw PaymentError("Amount is too high")
    #         }

    #         // It's not ideal to have a guard clause for a valid case,
    #         // but the parser should still handle it.
    #         guard amount > 50 else {
    #             log.info("Amount is low")
    #         }

    #         // This guard is strange because it has no throw/return
    #         guard amount != 100 else {
    #             log.warning("Amount is exactly 100")
    #         }

    #         // A guard with multiple conditions
    #         guard user.isVerified && !user.isFlagged else {
    #             throw SecurityError("User cannot make payment")
    #         }

    #         // A guard with a return statement
    #         guard amount > 10 else {
    #             return Error("Amount is too low")
    #         }

    #         // Process payment...
    #         return receipt
    #     }
    #     """
    #     program = self.parse(source)

    #     # Get the outer function body
    #     func_decl = program.declarations[0]
    #     statements = func_decl.body.statements

    #     # Check try-catch statement
    #     try_catch = statements[0]
    #     self.assertNodeType(try_catch, TryCatchStatement)
    #     self.assertNodeType(try_catch.try_block, BlockStatement)
    #     self.assertEqual(len(try_catch.try_block.statements), 3)
    #     self.assertEqual(len(try_catch.catch_clauses), 2)

    #     # Check first catch clause
    #     catch1 = try_catch.catch_clauses[0]
    #     self.assertEqual(catch1.error_type, "FileNotFoundError")
    #     self.assertIsNone(catch1.binding)

    #     # Check second catch clause with binding
    #     catch2 = try_catch.catch_clauses[1]
    #     self.assertEqual(catch2.error_type, "JsonParseError")
    #     self.assertEqual(catch2.binding, "message")

    #     # Check nested function with throws
    #     func_divide = statements[1]
    #     self.assertNodeType(func_divide, FunctionDeclaration)
    #     self.assertEqual(func_divide.name, "divide")
    #     self.assertTrue(func_divide.throws)
    #     self.assertEqual(func_divide.throws_types, ["DivisionByZeroError"])

    #     # Check throw statement inside nested function
    #     throw_stmt = func_divide.body.statements[0].consequent.statements[0]
    #     self.assertNodeType(throw_stmt, ThrowStatement)
    #     self.assertNodeType(throw_stmt.error, CallExpression)
    #     self.assertEqual(throw_stmt.error.callee.name, "DivisionByZeroError")

    #     # Check nested function with guard clauses
    #     func_payment = statements[2]
    #     self.assertNodeType(func_payment, FunctionDeclaration)
    #     self.assertEqual(func_payment.name, "processPayment")
    #     self.assertTrue(func_payment.throws)
    #     self.assertEqual(len(func_payment.throws_types), 0)  # Generic throws

    #     # Check guard clause
    #     guard_stmt = func_payment.body.statements[0]
    #     self.assertNodeType(guard_stmt, IfStatement)
    #     self.assertTrue(guard_stmt.is_guard)
    #     self.assertNodeType(guard_stmt.test, BinaryExpression)
    #     self.assertEqual(guard_stmt.test.operator, ">")

    # def test_ai_integration(self):
    #     """Test parsing of AI integration constructs."""
    #     source = """
    #     // Text generation with AI
    #     function generateEmailResponse(customerInquiry: String) -> String {
    #         return using ai {
    #             task: "Generate a professional customer service response"
    #             input: customerInquiry
    #             parameters: {
    #                 tone: "helpful and professional",
    #                 maxLength: 200 words,
    #                 includeGreeting: true,
    #                 includeClosure: true
    #             }
    #         }
    #     }

    #     // Structured data extraction
    #     function extractInvoiceData(document: Document) -> InvoiceData {
    #         return using ai {
    #             task: "Extract invoice information"
    #             input: document.text
    #             outputSchema: InvoiceData  // Type checking for AI output
    #             confidence: 0.8 minimum    // Only accept high-confidence extractions
    #         }
    #     }

    #     // Define an AI agent with specific capabilities
    #     agent CustomerSupportAssistant {
    #         // Define what the agent can access
    #         permissions {
    #             canRead: [CustomerDatabase, KnowledgeBase, SupportHistory]
    #             canWrite: [TicketSystem]
    #             canCall: [EmailService, NotificationService]
    #         }

    #         // Define the agent's capabilities
    #         capabilities {
    #             findSimilarIssues(description: String) -> List<SupportTicket>
    #             suggestSolution(problem: String) -> List<Solution>
    #             craftResponse(context: TicketContext) -> EmailTemplate
    #             escalateToHuman(reason: String)
    #         }

    #         // Define constraints on the agent's behavior
    #         constraints {
    #             maxResponseTime: 30 seconds
    #             mustEscalateWhen: [
    #                 "customer appears upset",
    #                 "legal issues mentioned",
    #                 "refund requested over $50"
    #             ]
    #             responseStyle: from file "support-guidelines.txt"
    #         }
    #     }

    #     // Using intents for self-healing
    #     intent "Calculate average sales per day for each month"
    #     function calculateAverageDailySales(monthlySales) {
    #         let result = {}

    #         for (let month in monthlySales) {
    #             let daysInMonth = getDaysInMonth(month)
    #             result[month] = monthlySales[month] / daysInMonth
    #         }

    #         return result
    #     }
    #     """
    #     program = self.parse(source)

    #     # Check declarations
    #     self.assertEqual(len(program.declarations), 4)

    #     # Check AI text generation function
    #     func1 = program.declarations[0]
    #     self.assertNodeType(func1, FunctionDeclaration)
    #     self.assertEqual(func1.name, "generateEmailResponse")
    #     return_expr = func1.body.statements[0]
    #     self.assertNodeType(return_expr, ReturnStatement)
    #     self.assertNodeType(return_expr.expression, AIExpression)
    #     self.assertEqual(return_expr.expression.kind, "using ai")

    #     # Check AI properties
    #     ai_expr = return_expr.expression
    #     self.assertEqual(ai_expr.properties["task"], "Generate a professional customer service response")
    #     self.assertNodeType(ai_expr.properties["input"], IdentifierExpression)
    #     self.assertEqual(ai_expr.properties["input"].name, "customerInquiry")
    #     self.assertNodeType(ai_expr.properties["parameters"], Expression)

    #     # Check structured data extraction function
    #     func2 = program.declarations[1]
    #     self.assertNodeType(func2, FunctionDeclaration)
    #     self.assertEqual(func2.name, "extractInvoiceData")
    #     return_expr = func2.body.statements[0]
    #     self.assertNodeType(return_expr, ReturnStatement)
    #     self.assertNodeType(return_expr.expression, AIExpression)

    #     # Check AI properties
    #     ai_expr = return_expr.expression
    #     self.assertEqual(ai_expr.properties["task"], "Extract invoice information")
    #     self.assertNodeType(ai_expr.properties["outputSchema"], IdentifierExpression)
    #     self.assertEqual(ai_expr.properties["outputSchema"].name, "InvoiceData")
    #     self.assertNodeType(ai_expr.properties["confidence"], Expression)

    #     # Check agent declaration
    #     agent_decl = program.declarations[2]
    #     self.assertNodeType(agent_decl, AgentDeclaration)
    #     self.assertEqual(agent_decl.name, "CustomerSupportAssistant")

    #     # Check agent permissions
    #     self.assertIsNotNone(agent_decl.permissions)
    #     self.assertEqual(len(agent_decl.permissions.can_read), 3)
    #     self.assertEqual(agent_decl.permissions.can_read[0], "CustomerDatabase")
    #     self.assertEqual(agent_decl.permissions.can_read[1], "KnowledgeBase")
    #     self.assertEqual(agent_decl.permissions.can_read[2], "SupportHistory")
    #     self.assertEqual(len(agent_decl.permissions.can_write), 1)
    #     self.assertEqual(agent_decl.permissions.can_write[0], "TicketSystem")
    #     self.assertEqual(len(agent_decl.permissions.can_call), 2)
    #     self.assertEqual(agent_decl.permissions.can_call[0], "EmailService")
    #     self.assertEqual(agent_decl.permissions.can_call[1], "NotificationService")

    #     # Check agent capabilities
    #     self.assertIsNotNone(agent_decl.capabilities)
    #     self.assertEqual(len(agent_decl.capabilities), 4)
    #     self.assertEqual(agent_decl.capabilities[0].name, "findSimilarIssues")
    #     self.assertEqual(agent_decl.capabilities[0].return_type, "List<SupportTicket>")
    #     self.assertEqual(agent_decl.capabilities[1].name, "suggestSolution")
    #     self.assertEqual(agent_decl.capabilities[1].return_type, "List<Solution>")
    #     self.assertEqual(agent_decl.capabilities[2].name, "craftResponse")
    #     self.assertEqual(agent_decl.capabilities[2].return_type, "EmailTemplate")
    #     self.assertEqual(agent_decl.capabilities[3].name, "escalateToHuman")
    #     self.assertIsNone(agent_decl.capabilities[3].return_type)

    #     # Check agent constraints
    #     self.assertIsNotNone(agent_decl.constraints)
    #     self.assertEqual(agent_decl.constraints.max_response_time, "30 seconds")
    #     self.assertEqual(len(agent_decl.constraints.must_escalate_when), 3)
    #     self.assertEqual(agent_decl.constraints.must_escalate_when[0], "customer appears upset")
    #     self.assertEqual(agent_decl.constraints.must_escalate_when[1], "legal issues mentioned")
    #     self.assertEqual(agent_decl.constraints.must_escalate_when[2], "refund requested over $50")
    #     self.assertEqual(agent_decl.constraints.response_style_source, "support-guidelines.txt")

    #     # Check intent-based function
    #     func3 = program.declarations[3]
    #     self.assertNodeType(func3, FunctionDeclaration)
    #     self.assertEqual(func3.name, "calculateAverageDailySales")
    #     self.assertEqual(func3.intent, "Calculate average sales per day for each month")

    # def test_service_declarations(self):
    #     """Test parsing of service declarations."""
    #     source = """
    #     // Define a service
    #     service NetworkMonitor {
    #         // Configuration for monitoring
    #         config {
    #             scanInterval: Duration = 5 minutes,
    #             alertThreshold: Severity = Severity.Medium,
    #             autoHealEnabled: Boolean = true
    #         }

    #         // Initialize the monitoring system
    #         function initialize() {
    #             log.info("Initializing Network Monitoring System")

    #             // Setup monitoring schedule
    #             schedule(config.scanInterval) {
    #                 scanAllDevices(devices)
    #             }
    #         }

    #         // Recovery strategies
    #         recoveryStrategies {
    #             // Strategy for connectivity errors
    #             for ConnectivityError {
    #                 retry(maxAttempts: 3, backoff: exponential)
    #                 fallback(useCache: true, expiration: 5 minutes)
    #                 notify(level: warning)
    #             }
    #         }

    #         // Event handlers
    #         on event DeviceStatusChanged(device, status) {
    #             log.info("Device ${device.id} status changed to ${status}")

    #             if status == Status.Critical {
    #                 alertOperators(device, status)
    #             }
    #         }

    #         // Scheduled tasks
    #         schedule("0 0 * * *") {  // Daily at midnight
    #             generateDailyReport()
    #         }
    #     }
    #     """
    #     program = self.parse(source)

    #     # Check service declaration
    #     self.assertEqual(len(program.declarations), 1)
    #     service_decl = program.declarations[0]
    #     self.assertNodeType(service_decl, ServiceDeclaration)
    #     self.assertEqual(service_decl.name, "NetworkMonitor")

    #     # Check service config
    #     self.assertIsNotNone(service_decl.config)
    #     self.assertEqual(len(service_decl.config), 3)
    #     self.assertEqual(service_decl.config[0].name, "scanInterval")
    #     self.assertEqual(service_decl.config[0].type, "Duration")
    #     self.assertEqual(service_decl.config[0].default_value, "5 minutes")
    #     self.assertEqual(service_decl.config[1].name, "alertThreshold")
    #     self.assertEqual(service_decl.config[1].type, "Severity")
    #     self.assertEqual(service_decl.config[1].default_value, "Severity.Medium")
    #     self.assertEqual(service_decl.config[2].name, "autoHealEnabled")
    #     self.assertEqual(service_decl.config[2].type, "Boolean")
    #     self.assertEqual(service_decl.config[2].default_value, True)

    #     # Check functions
    #     self.assertEqual(len(service_decl.functions), 1)
    #     self.assertEqual(service_decl.functions[0].name, "initialize")

    #     # Check recovery strategies
    #     self.assertIsNotNone(service_decl.recovery_strategies)
    #     self.assertEqual(len(service_decl.recovery_strategies), 1)
    #     self.assertEqual(service_decl.recovery_strategies[0].error_type, "ConnectivityError")
    #     self.assertEqual(len(service_decl.recovery_strategies[0].strategies), 3)

    #     # Check event handlers
    #     self.assertEqual(len(service_decl.event_handlers), 1)
    #     self.assertEqual(service_decl.event_handlers[0].event_name, "DeviceStatusChanged")
    #     self.assertEqual(len(service_decl.event_handlers[0].parameters), 2)
    #     self.assertEqual(service_decl.event_handlers[0].parameters[0], "device")
    #     self.assertEqual(service_decl.event_handlers[0].parameters[1], "status")

    #     # Check scheduled tasks
    #     self.assertEqual(len(service_decl.scheduled_tasks), 1)
    #     self.assertEqual(service_decl.scheduled_tasks[0].schedule, "0 0 * * *")

if __name__ == "__main__":
    unittest.main()