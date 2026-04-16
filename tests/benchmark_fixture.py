"""Labeled prompt benchmark for classification accuracy measurement.

Each entry: (prompt, expected_tier, category)
Categories help diagnose which domains need pattern improvement.
"""

BENCHMARK_PROMPTS: list[tuple[str, str, str]] = [
    # =========================================================================
    # HAIKU — simple lookups, quick commands, factual questions
    # =========================================================================
    # Git commands
    ("git status", "haiku", "git"),
    ("show me the git log", "haiku", "git"),
    ("git diff main", "haiku", "git"),
    ("git add .", "haiku", "git"),

    # Simple questions
    ("what is a closure?", "haiku", "factual"),
    ("what does async mean?", "haiku", "factual"),
    ("how to create a dictionary in Python?", "haiku", "factual"),
    ("what are protocols in Swift?", "haiku", "factual"),
    ("how does map work?", "haiku", "factual"),

    # File reading / listing
    ("show me the contents of main.py", "haiku", "file-ops"),
    ("list all swift files", "haiku", "file-ops"),
    ("read the README", "haiku", "file-ops"),
    ("get the package.json", "haiku", "file-ops"),

    # Formatting / simple ops
    ("format this json", "haiku", "formatting"),
    ("lint this file", "haiku", "formatting"),
    ("prettify the output", "haiku", "formatting"),
    ("find all usages of LoginView", "haiku", "search"),
    ("grep for TODO comments", "haiku", "search"),
    ("search for fetchUser in the codebase", "haiku", "search"),
    ("summarize this function", "haiku", "summary"),
    ("what's the syntax for guard statements?", "haiku", "factual"),

    # =========================================================================
    # SONNET — moderate complexity, implementation tasks
    # =========================================================================
    # Test writing
    ("write a test for the login flow", "sonnet", "testing"),
    ("add unit tests for UserService", "sonnet", "testing"),
    ("create a test spec for the API endpoint", "sonnet", "testing"),

    # Bug fixing
    ("fix the bug in the auth middleware", "sonnet", "bugfix"),
    ("debug this error in the payment handler", "sonnet", "bugfix"),
    ("fix the issue with the date picker not showing", "sonnet", "bugfix"),

    # Implementation
    ("build a settings screen with toggle switches", "sonnet", "implementation"),
    ("implement a loading spinner component", "sonnet", "implementation"),
    ("create a new endpoint for user profiles", "sonnet", "implementation"),
    ("add a search bar to the list view", "sonnet", "implementation"),

    # Refactoring (single scope)
    ("refactor the fetchData method to use async/await", "sonnet", "refactor"),
    ("refactor this view to extract the header", "sonnet", "refactor"),

    # Code review
    ("review this function for issues", "sonnet", "review"),
    ("check this PR for problems", "sonnet", "review"),

    # Documentation
    ("add docstrings to this module", "sonnet", "docs"),
    ("document the API endpoints", "sonnet", "docs"),

    # =========================================================================
    # OPUS — complex, multi-file, architectural
    # =========================================================================
    # Architecture
    ("design the architecture for a real-time chat system", "opus", "architecture"),
    ("architect a caching layer for the API", "opus", "architecture"),
    ("design pattern for handling offline sync", "opus", "architecture"),

    # Multi-file / cross-cutting
    ("refactor the entire auth module across all files", "opus", "multi-file"),
    ("update all components to use the new design system", "opus", "multi-file"),
    ("migrate all API calls across multiple modules to the new client", "opus", "multi-file"),

    # Trade-off analysis
    ("compare REST vs GraphQL for our mobile app", "opus", "analysis"),
    ("pros and cons of SwiftData vs Core Data for this project", "opus", "analysis"),
    ("evaluate the trade-offs between server-side and client-side rendering", "opus", "analysis"),

    # Performance optimization
    ("optimize the database query performance", "opus", "performance"),
    ("optimize memory usage in the image processing pipeline", "opus", "performance"),

    # Planning / roadmap
    ("plan the migration from UIKit to SwiftUI", "opus", "planning"),
    ("create a roadmap for implementing the payment system", "opus", "planning"),
    ("plan the phased rollout of the new authentication system", "opus", "planning"),

    # Security
    ("security review of the authentication flow", "opus", "security"),
    ("audit the API for vulnerabilities", "opus", "security"),

    # Complex debugging
    ("diagnose the memory leak in the background sync process", "opus", "complex-debug"),
    ("debug the race condition in the WebSocket handler", "opus", "complex-debug"),
    ("diagnose the deadlock between the cache and network layers", "opus", "complex-debug"),

    # =========================================================================
    # TRICKY / EDGE CASES — common misclassifications
    # =========================================================================
    # Short but complex (should NOT be haiku)
    ("redesign the navigation", "opus", "edge-short-complex"),
    ("analyze our error handling strategy", "opus", "edge-short-complex"),

    # Long but simple (should NOT be opus just because of length)
    ("what is the difference between let and var in Swift? I know var is mutable but I want to understand when to use each one and if there are performance implications", "haiku", "edge-long-simple"),
    # Very long but clearly sonnet-tier (implementation, not architecture)
    ("fix the bug in the login screen where the password field doesn't clear after a failed attempt. The user taps login, gets an error, but the password stays filled in. I've tried setting the text to empty in the error handler but it doesn't seem to work. The field is a SecureField in SwiftUI and the binding is to a published property on the view model. It works fine for the username field. " + "Here is the relevant code from LoginView. " * 10, "sonnet", "edge-long-sonnet"),

    # Ambiguous — could go either way, test current default behavior
    ("update the login screen", "sonnet", "edge-ambiguous"),
    ("fix the tests", "sonnet", "edge-ambiguous"),
    ("make the app faster", "sonnet", "edge-ambiguous"),
    ("clean up this code", "sonnet", "edge-ambiguous"),

    # Follow-up style (short, conversational)
    ("yes", "haiku", "edge-followup"),
    ("ok do it", "haiku", "edge-followup"),
    ("no that's wrong", "haiku", "edge-followup"),

    # iOS-specific patterns (domain the user cares about)
    ("add a SwiftUI view for the profile screen", "sonnet", "ios"),
    ("implement Core Location permissions", "sonnet", "ios"),
    ("set up push notifications", "sonnet", "ios"),
    ("design the SwiftData model layer with relationships and migrations", "opus", "ios"),
    ("architect the offline-first sync strategy using CloudKit", "opus", "ios"),

    # =========================================================================
    # STRESS TEST — adversarial edge cases for overfitting detection
    # =========================================================================
    # Haiku that contain opus-sounding words in non-opus contexts
    ("what is a design pattern?", "haiku", "stress-false-opus"),
    ("show me the security settings", "haiku", "stress-false-opus"),
    ("what does optimize mean?", "haiku", "stress-false-opus"),

    # Sonnet that look like haiku (short but require implementation)
    ("add a button", "sonnet", "stress-short-sonnet"),
    ("create a modal", "sonnet", "stress-short-sonnet"),
    ("fix the crash", "sonnet", "stress-short-sonnet"),
    ("write the migration", "sonnet", "stress-short-sonnet"),

    # Sonnet that look like opus (complex words but single-scope)
    ("refactor the login view to use MVVM", "sonnet", "stress-false-opus-sonnet"),
    ("add error handling to the API call", "sonnet", "stress-false-opus-sonnet"),

    # Opus that look like sonnet (no explicit opus keywords)
    ("how should we structure the entire app to support offline mode?", "opus", "stress-hidden-opus"),
    ("what's the best way to handle data across all our screens?", "opus", "stress-hidden-opus"),

    # Extremely short valid prompts
    ("thanks", "haiku", "stress-ultra-short"),
    ("?", "haiku", "stress-ultra-short"),
    ("hmm", "haiku", "stress-ultra-short"),

    # Multi-intent prompts (contain signals from multiple tiers)
    ("fix the login bug and redesign the auth architecture", "opus", "stress-multi-intent"),
    ("write tests for the API and review the error handling across all modules", "opus", "stress-multi-intent"),

    # Questions about complex topics — these are analytical, not simple lookups
    ("what are trade-offs of microservices?", "opus", "stress-question-complex"),
    ("how does the security audit work?", "haiku", "stress-question-complex"),

    # =========================================================================
    # NATURAL LANGUAGE — real-world phrasing
    # =========================================================================
    # Haiku — conversational questions
    ("can you show me the config file?", "haiku", "natural-haiku"),
    ("where did we put the auth module?", "haiku", "natural-haiku"),
    ("is this the right file?", "haiku", "natural-haiku"),
    ("where is the main entry point defined?", "haiku", "natural-haiku"),
    ("what does this error mean?", "haiku", "natural-haiku"),
    ("explain this function", "haiku", "natural-haiku"),

    # Sonnet — natural implementation requests
    ("can you fix this crash?", "sonnet", "natural-sonnet"),
    ("could you add a loading spinner to this view?", "sonnet", "natural-sonnet"),
    ("help me implement the search feature", "sonnet", "natural-sonnet"),
    ("I need to add a new API endpoint", "sonnet", "natural-sonnet"),
    ("let's update the settings screen", "sonnet", "natural-sonnet"),
    ("please fix the failing test", "sonnet", "natural-sonnet"),
    ("change the background color of the header", "sonnet", "natural-sonnet"),

    # Opus — natural complex requests
    ("how should we structure the database for offline support?", "opus", "natural-opus"),
    ("what's the best approach for handling auth across all our services?", "opus", "natural-opus"),
    ("we need a strategy for migrating the entire backend", "opus", "natural-opus"),
]
